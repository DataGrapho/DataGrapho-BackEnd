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
        try:
            self.service = ChatbotService()
        except Exception as e:
            logger.error(f"Failed to initialize ChatbotService: {e}", exc_info=True)
            self.service = None
    
    @staticmethod
    def health_check(request):
        """Endpoint de teste para verificar se o chatbot está funcionando"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from chatbot.core.tool_registry import get_tool_registry
            from chatbot.core.domain_loader import get_all_domain_repositories
            from chatbot.core.ai_providers import get_ai_provider
            from django.conf import settings
            
            registry = get_tool_registry()
            tools = registry.get_all_tools()
            repositories = get_all_domain_repositories()
            provider = get_ai_provider()
            
            return Response({
                'status': 'ok',
                'chatbot_config': {
                    'provider': settings.CHATBOT_CONFIG.get('AI_PROVIDER'),
                    'model': settings.CHATBOT_CONFIG.get('AI_MODEL'),
                    'active_domains': settings.CHATBOT_CONFIG.get('ACTIVE_DOMAINS'),
                    'api_key_set': bool(settings.CHATBOT_CONFIG.get('AI_API_KEY')),
                },
                'tools_loaded': len(tools),
                'tool_names': [t.name for t in tools],
                'repositories_loaded': list(repositories.keys()),
                'provider_class': provider.__class__.__name__,
            })
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return Response({
                'status': 'error',
                'error': str(e),
            }, status=500)
    
    def post(self, request):
        try:
            # Verificar se o serviço foi inicializado corretamente
            if self.service is None:
                logger.error("ChatbotService not initialized - AI_API_KEY may not be configured")
                return Response(
                    {
                        'success': False,
                        'error': 'Chatbot não está configurado corretamente. Verifique a configuração do AI_API_KEY.',
                        'data': None
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            logger.info("=== CHAT REQUEST START ===")
            logger.info(f"Request data: {request.data}")
            
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
            
            try:
                logger.info("Calling service.process_chat...")
                result = self.service.process_chat(
                    user_id=user_id,
                    message=message,
                    session_id=session_id
                )
                logger.info(f"Service returned: {result}")
            except Exception as service_error:
                logger.error(f"ERROR in service.process_chat: {service_error}", exc_info=True)
                raise
            
            response_serializer = ChatResponseSerializer(data=result)
            if not response_serializer.is_valid():
                logger.error(f"Invalid response format: {response_serializer.errors}")
                logger.error(f"Result was: {result}")
                return Response(
                    {
                        'success': False,
                        'error': 'Internal error: invalid response format',
                        'details': response_serializer.errors
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            logger.info("=== CHAT REQUEST SUCCESS ===")
            return Response(
                {
                    'success': True,
                    'data': response_serializer.validated_data
                },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"=== CHAT REQUEST FAILED ===")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception message: {str(e)}")
            logger.error(f"Full traceback:", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': str(e) or 'Internal server error',
                    'data': None
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
        # Retornar data + primeiros caracteres do session_id
        from django.utils import timezone
        created_date = timezone.localtime(obj.created_at)
        date_str = created_date.strftime('%d/%m')
        session_prefix = str(obj.session_id)[:8]
        return f"{date_str} - {session_prefix}"
    
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
    
    def create(self, request):
        """Criar uma nova sessão de chat"""
        try:
            session = ChatSession.objects.create(user=request.user)
            serializer = SessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Error creating session: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to create session'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def list(self, request):
        """Listar todas as sessões do usuário"""
        try:
            sessions = ChatSession.objects.filter(
                user=request.user
            ).prefetch_related('messages').order_by('-last_activity')
            
            logger.info(f"Found {sessions.count()} sessions for user {request.user.id}")
            
            serializer = SessionSerializer(sessions, many=True)
            logger.info(f"Serialized {len(serializer.data)} sessions")
            
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to list sessions', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def partial_update(self, request, pk=None):
        """Atualizar o título de uma sessão"""
        try:
            session = ChatSession.objects.get(
                session_id=pk,
                user=request.user
            )
            
            title = request.data.get('title', '')
            # Por enquanto só vamos logar, mas poderia adicionar campo title no modelo
            logger.info(f"User requested to rename session {pk} to '{title}'")
            
            serializer = SessionSerializer(session)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except ChatSession.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating session: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to update session'},
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
