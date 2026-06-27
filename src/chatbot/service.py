import uuid
import logging
from typing import Dict, Any, Optional
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from chatbot.models import ChatSession, ChatMessage
from chatbot.core.engine import FunctionCallingEngine
from chatbot.core.ai_providers import AIMessage


logger = logging.getLogger(__name__)
User = get_user_model()


class ChatbotService:
    
    def __init__(self):
        self.engine = FunctionCallingEngine()
    
    def process_chat(
        self,
        user_id: int,
        message: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        logger.info(
            f"Processing chat: user_id={user_id}, "
            f"session_id={session_id}, "
            f"message='{message[:50]}...'"
        )
        
        session = self._get_or_create_session(user_id, session_id)
        
        self._store_message(
            session=session,
            role='user',
            content=message
        )
        
        conversation_history = self._get_conversation_history(session)
        
        try:
            result = self.engine.execute_query(
                user_message=message,
                conversation_history=conversation_history
            )
            
            self._store_message(
                session=session,
                role='assistant',
                content=result.response
            )
            
            if result.tools_used:
                for tool_name in result.tools_used:
                    self._store_message(
                        session=session,
                        role='tool',
                        content=f"Tool executed: {tool_name}",
                        tool_name=tool_name
                    )
            
            session.last_activity = timezone.now()
            session.save(update_fields=['last_activity'])
            
            logger.info(
                f"Chat processed successfully: session_id={session.session_id}, "
                f"tools_used={result.tools_used}, "
                f"tool_calls_count={result.tool_calls_count}"
            )
            
            return {
                'response': result.response,
                'session_id': str(session.session_id),
                'tools_used': result.tools_used,
                'tool_calls_count': result.tool_calls_count
            }
        
        except Exception as e:
            logger.error(f"Error processing chat: {e}", exc_info=True)
            
            error_message = f"Erro ao processar mensagem: {str(e)}"
            self._store_message(
                session=session,
                role='assistant',
                content=error_message
            )
            
            return {
                'response': error_message,
                'session_id': str(session.session_id),
                'tools_used': [],
                'tool_calls_count': 0,
                'error': str(e)
            }
    
    def _get_or_create_session(
        self,
        user_id: int,
        session_id: Optional[str] = None
    ) -> ChatSession:
        if session_id:
            try:
                session_uuid = uuid.UUID(session_id)
                session = ChatSession.objects.get(
                    session_id=session_uuid,
                    user_id=user_id
                )
                
                from django.conf import settings
                expiry_seconds = settings.CHATBOT_CONFIG.get('SESSION_EXPIRY', 3600)
                expiry_time = timezone.now() - timedelta(seconds=expiry_seconds)
                
                if session.last_activity < expiry_time:
                    logger.info(f"Session {session_id} expired, creating new session")
                    session = self._create_new_session(user_id)
                else:
                    logger.info(f"Using existing session: {session_id}")
                
                return session
                
            except (ValueError, ChatSession.DoesNotExist):
                logger.warning(f"Invalid or non-existent session_id: {session_id}, creating new session")
                return self._create_new_session(user_id)
        else:
            logger.info(f"No session_id provided, creating new session for user {user_id}")
            return self._create_new_session(user_id)
    
    def _create_new_session(self, user_id: int) -> ChatSession:
        user = User.objects.get(pk=user_id)
        session = ChatSession.objects.create(user=user)
        logger.info(f"Created new session: {session.session_id} for user {user_id}")
        return session
    
    def _store_message(
        self,
        session: ChatSession,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        tool_parameters: Optional[Dict] = None
    ) -> ChatMessage:
        message = ChatMessage.objects.create(
            session=session,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_parameters=tool_parameters
        )
        
        logger.debug(f"Stored message: role={role}, session={session.session_id}")
        return message
    
    def _get_conversation_history(
        self,
        session: ChatSession,
        limit: int = 10
    ) -> list:
        messages = ChatMessage.objects.filter(
            session=session
        ).order_by('-created_at')[:limit]
        
        messages = list(reversed(messages))
        
        ai_messages = []
        for msg in messages:
            if msg.role == 'tool':
                continue
            
            ai_messages.append(AIMessage(
                role=msg.role,
                content=msg.content
            ))
        
        logger.debug(f"Retrieved {len(ai_messages)} messages for session {session.session_id}")
        return ai_messages
    
    def get_session_messages(
        self,
        user_id: int,
        session_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            session_uuid = uuid.UUID(session_id)
            session = ChatSession.objects.get(
                session_id=session_uuid,
                user_id=user_id
            )
            
            messages_query = ChatMessage.objects.filter(
                session=session
            ).order_by('created_at')
            
            if limit:
                messages_query = messages_query[:limit]
            
            messages = list(messages_query.values(
                'id_message',
                'role',
                'content',
                'tool_name',
                'created_at'
            ))
            
            return {
                'session_id': str(session.session_id),
                'created_at': session.created_at.isoformat(),
                'last_activity': session.last_activity.isoformat(),
                'message_count': len(messages),
                'messages': messages
            }
            
        except (ValueError, ChatSession.DoesNotExist):
            logger.warning(f"Session not found: {session_id}")
            return {
                'error': 'Session not found',
                'session_id': session_id
            }
