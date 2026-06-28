import logging
import html
import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework import status, serializers, viewsets

from chatbot.dto import ChatRequestSerializer, ChatResponseSerializer
from chatbot.service import ChatbotService


logger = logging.getLogger(__name__)


def sanitize_input(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r'[^\w\s\-.,!?áàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


class ChatbotRateThrottle(UserRateThrottle):
    scope = 'chatbot'


class ChatController(APIView):
    
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatbotRateThrottle]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ChatbotService()
    
    def post(self, request):
        try:
            request_serializer = ChatRequestSerializer(data=request.data)
            if not request_serializer.is_valid():
                logger.warning(f"Invalid request: {request_serializer.errors}")
                return Response(
                    {
                        'success': False,
                        'error': 'Invalid request',
                        'details': request_serializer.errors
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            message = request_serializer.validated_data['message']
            session_id = request_serializer.validated_data.get('session_id')
            
            message = sanitize_input(message)
            
            if session_id:
                session_id = str(session_id)
            
            user_id = request.user.pk
            
            logger.info(
                f"Chat request: user_id={user_id}, "
                f"session_id={session_id}, "
                f"message='{message[:50]}...'"
            )
            
            logger.info(
                f"AUDIT: user_id={user_id}, "
                f"session_id={session_id}, "
                f"action=chat_request, "
                f"timestamp={request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))}"
            )
            
            result = self.service.process_chat(
                user_id=user_id,
                message=message,
                session_id=session_id
            )
            
            response_serializer = ChatResponseSerializer(data=result)
            if not response_serializer.is_valid():
                logger.error(f"Invalid response format: {response_serializer.errors}")
                return Response(
                    {
                        'success': False,
                        'error': 'Internal error: invalid response format'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response(
                {
                    'success': True,
                    'data': response_serializer.validated_data
                },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Unexpected error in ChatController: {e}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': 'Internal server error',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



from rest_framework import viewsets
from chatbot.models import ChatSession, ChatMessage


class SessionSerializer(serializers.Serializer):
    id = serializers.UUIDField(source='session_id')
    title = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at')
    updatedAt = serializers.DateTimeField(source='last_activity')
    lastMessagePreview = serializers.SerializerMethodField()
    totalMessages = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    def get_title(self, obj):
        # Pega a primeira mensagem como título ou retorna "Novo chat"
        first_message = obj.messages.filter(role='user').first()
        if first_message:
            return first_message.content[:50] + ('...' if len(first_message.content) > 50 else '')
        return 'Novo chat'
    
    def get_lastMessagePreview(self, obj):
        last_message = obj.messages.order_by('-created_at').first()
        if last_message:
            return last_message.content[:100] + ('...' if len(last_message.content) > 100 else '')
        return ''
    
    def get_totalMessages(self, obj):
        return obj.messages.count()
    
    def get_status(self, obj):
        return 'active'


class SessionMessagesSerializer(serializers.Serializer):
    response = serializers.SerializerMethodField()
    session_id = serializers.UUIDField()
    tools_used = serializers.SerializerMethodField()
    tool_calls_count = serializers.SerializerMethodField()
    
    def get_response(self, obj):
        # Retorna a última resposta do assistant
        last_assistant_msg = obj.messages.filter(role='assistant').order_by('-created_at').first()
        return last_assistant_msg.content if last_assistant_msg else ''
    
    def get_tools_used(self, obj):
        # Retorna as ferramentas usadas nas mensagens tool
        tool_messages = obj.messages.filter(role='tool')
        return list(set([msg.tool_name for msg in tool_messages if msg.tool_name]))
    
    def get_tool_calls_count(self, obj):
        return obj.messages.filter(role='tool').count()


class SessionsController(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Listar todas as sessões do usuário"""
        try:
            sessions = ChatSession.objects.filter(
                user=request.user
            ).prefetch_related('messages').order_by('-last_activity')
            
            serializer = SessionSerializer(sessions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to list sessions'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """Obter histórico de uma sessão específica"""
        try:
            session = ChatSession.objects.prefetch_related('messages').get(
                session_id=pk,
                user=request.user
            )
            
            serializer = SessionMessagesSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving session: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to retrieve session'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, pk=None):
        """Deletar uma sessão"""
        try:
            session = ChatSession.objects.get(
                session_id=pk,
                user=request.user
            )
            session.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting session: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to delete session'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
