import logging
import re

from django.conf import settings
from django.db.models import Q
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from chatbot.core.domain_loader import get_all_domain_repositories
from chatbot.core.tool_registry import get_tool_registry
from chatbot.dto import ChatRequestSerializer, ChatResponseSerializer
from chatbot.models import ChatMessage, ChatSession
from chatbot.service import ChatbotService


logger = logging.getLogger(__name__)


def sanitize_input(text: str) -> str:
    """Normalize user text without destroying accents or useful punctuation."""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return re.sub(r"\s+", " ", text).strip()


class ChatbotRateThrottle(UserRateThrottle):
    scope = "chatbot"


class ChatbotHealthController(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        registry = get_tool_registry()
        repositories = get_all_domain_repositories()
        configured = bool(settings.CHATBOT_CONFIG.get("AI_API_KEY"))
        return Response(
            {
                "status": "ok" if configured else "configuration_required",
                "provider": settings.CHATBOT_CONFIG.get("AI_PROVIDER"),
                "model": settings.CHATBOT_CONFIG.get("AI_MODEL"),
                "domains": list(repositories.keys()),
                "tools": [tool.name for tool in registry.get_all_tools()],
                "ai_configured": configured,
            }
        )


class ChatController(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatbotRateThrottle]
    service_class = ChatbotService

    def post(self, request):
        request_serializer = ChatRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        message = sanitize_input(request_serializer.validated_data["message"])
        session_id = request_serializer.validated_data.get("session_id")

        try:
            result = self.service_class().process_chat(
                user_id=request.user.pk,
                message=message,
                session_id=str(session_id) if session_id else None,
            )
        except Exception:
            logger.exception("Chat request failed for user_id=%s", request.user.pk)
            return Response(
                {
                    "success": False,
                    "error": "Nao foi possivel processar a mensagem agora.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        response_serializer = ChatResponseSerializer(data=result)
        response_serializer.is_valid(raise_exception=True)
        return Response({"success": True, "data": response_serializer.validated_data})


class SessionSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(source="session_id")
    title = serializers.CharField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="last_activity")
    lastMessagePreview = serializers.SerializerMethodField()
    totalMessages = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_lastMessagePreview(self, obj):
        message = obj.messages.exclude(role="tool").order_by("-created_at").first()
        if not message:
            return ""
        return message.content[:100] + ("..." if len(message.content) > 100 else "")

    def get_totalMessages(self, obj):
        return obj.messages.exclude(role="tool").count()

    def get_status(self, obj):
        return "active"


class SessionMessageSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="id_message")
    role = serializers.CharField()
    content = serializers.CharField()
    createdAt = serializers.DateTimeField(source="created_at")


class SessionDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="session_id")
    title = serializers.CharField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="last_activity")
    messages = serializers.SerializerMethodField()

    def get_messages(self, obj):
        messages = obj.messages.filter(role__in=("user", "assistant")).order_by("created_at")
        return SessionMessageSerializer(messages, many=True).data


class SessionTitleSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, allow_blank=False, trim_whitespace=True)


class SessionsController(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        title_serializer = SessionTitleSerializer(
            data=request.data or {"title": "Novo chat"}
        )
        title_serializer.is_valid(raise_exception=True)
        session = ChatSession.objects.create(
            user=request.user,
            title=title_serializer.validated_data["title"],
        )
        return Response(
            SessionSummarySerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    def list(self, request):
        sessions = ChatSession.objects.filter(user=request.user)
        search = request.query_params.get("search", "").strip()
        if search:
            sessions = sessions.filter(
                Q(title__icontains=search) | Q(messages__content__icontains=search)
            ).distinct()
        sessions = sessions.prefetch_related("messages").order_by("-last_activity")
        return Response(SessionSummarySerializer(sessions, many=True).data)

    def partial_update(self, request, pk=None):
        session = self._get_session(request.user, pk)
        if session is None:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = SessionTitleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session.title = serializer.validated_data["title"]
        session.save(update_fields=["title", "last_activity"])
        return Response(SessionSummarySerializer(session).data)

    def retrieve(self, request, pk=None):
        session = self._get_session(request.user, pk, prefetch=True)
        if session is None:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(SessionDetailSerializer(session).data)

    def destroy(self, request, pk=None):
        session = self._get_session(request.user, pk)
        if session is None:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _get_session(user, session_id, prefetch=False):
        queryset = ChatSession.objects.filter(user=user)
        if prefetch:
            queryset = queryset.prefetch_related("messages")
        try:
            return queryset.get(session_id=session_id)
        except (ChatSession.DoesNotExist, ValueError):
            return None
