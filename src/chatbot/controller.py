import logging
import html
import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework import status

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
