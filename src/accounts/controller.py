from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .dto import ForgotPasswordDto, LoginTokenDto, RegisterDto, ResetPasswordDto, UsuarioAcessoDto, UsuarioMeDto
from .models import PasswordResetToken


User = get_user_model()


class LoginView(TokenObtainPairView):
    """Login endpoint - obtain JWT access and refresh tokens."""
    serializer_class = LoginTokenDto


class MeView(APIView):
    """Get current authenticated user information."""
    serializer_class = UsuarioMeDto # garente que use o DTO certo *Rafa passou aqui
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve current user profile and access information."""
        return Response(UsuarioMeDto(request.user).data)


class RegisterView(APIView):
    """Create a new user account."""
    serializer_class = RegisterDto # garente que use o DTO certo *Rafa passou aqui

    def get_permissions(self):
        if getattr(settings, "DEBUG", False):
            return [AllowAny()]
        return [IsAdminUser()]

    def post(self, request):
        """Register a new user with optional access records."""
        serializer = RegisterDto(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, acessos = serializer.save()

        response = {
            "usuario": UsuarioMeDto(user).data,
            "acessos": UsuarioAcessoDto(acessos, many=True).data,
        }
        return Response(response, status=201)


class ForgotPasswordView(APIView):
    """Start password recovery flow with generic response for security."""

    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordDto

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email=email, is_active=True).first()

        if user is not None:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            expires_minutes = int(getattr(settings, "PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES", 30))
            expires_at = timezone.now() + timedelta(minutes=expires_minutes)

            PasswordResetToken.objects.create(
                usuario=user,
                token_hash=token_hash,
                expires_at=expires_at,
            )

            reset_link = self._build_reset_link(token)
            send_mail(
                subject="Recuperacao de senha",
                message=(
                    "Recebemos uma solicitacao para redefinir sua senha.\n"
                    f"Use o link abaixo para continuar:\n{reset_link}\n\n"
                    "Se voce nao solicitou, ignore este e-mail."
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@datagrapho.local"),
                recipient_list=[email],
                fail_silently=True,
            )

        return Response({"detail": "Se o e-mail estiver cadastrado, enviaremos as instrucoes de recuperacao."}, status=200)

    @staticmethod
    def _build_reset_link(token: str) -> str:
        base_url = getattr(
            settings,
            "FRONTEND_PASSWORD_RESET_URL",
            "http://localhost:3000/reset-password?token={token}",
        )
        if "{token}" in base_url:
            return base_url.format(token=token)
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}token={token}"


class ResetPasswordView(APIView):
    """Finish password reset flow using one-time token."""

    permission_classes = [AllowAny]
    serializer_class = ResetPasswordDto

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["password"]
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        with transaction.atomic():
            reset_token = (
                PasswordResetToken.objects.select_related("usuario")
                .filter(token_hash=token_hash, usado_em__isnull=True)
                .order_by("-criado_em")
                .first()
            )

            if reset_token is None or reset_token.is_expired():
                return Response({"detail": "Token invalido ou expirado."}, status=400)

            user = reset_token.usuario
            user.set_password(new_password)
            user.save(update_fields=["password"])

            reset_token.usado_em = timezone.now()
            reset_token.save(update_fields=["usado_em"])

        return Response({"detail": "Senha redefinida com sucesso."}, status=200)
