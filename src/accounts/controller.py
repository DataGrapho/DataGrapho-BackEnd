from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .dto import (
    EmpresaDto,
    EmpresaListDto,
    FilialDto,
    FilialListDto,
    ForgotPasswordDto,
    LoginTokenDto,
    PerfilDto,
    PerfilListDto,
    RegisterDto,
    ResetPasswordDto,
    SetorDto,
    SetorListDto,
    UsuarioAcessoDto,
    UsuarioMeDto,
)
from .models import Empresa, Filial, PasswordResetToken, Perfil, Setor


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
    """Create a user account as an authenticated administrator only."""
    serializer_class = RegisterDto # garente que use o DTO certo *Rafa passou aqui
    # A rota nunca deve se tornar p├║blica por causa de uma configura├º├úo de
    # ambiente.  O JWT deve pertencer a um usu├írio com ``is_staff=True``.
    permission_classes = [IsAdminUser]

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

            print("RESET TOKEN:", token)
            print("RESET LINK:", reset_link)

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


class EmpresaViewSet(viewsets.ModelViewSet):
    """ViewSet to manage Empresa CRUD operations."""

    queryset = Empresa.objects.all()
    serializer_class = EmpresaDto
    permission_classes = [IsAdminUser]
    lookup_field = "id_empresa"

    def get_serializer_class(self):
        if self.action == "list":
            return EmpresaListDto
        return EmpresaDto

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "count": len(queryset),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "success": True,
                "message": "Empresa criada com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                "success": True,
                "message": "Empresa atualizada com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "success": True,
                "message": "Empresa removida com sucesso",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, id_empresa=None):
        instance = self.get_object()
        instance.ativo = True
        instance.save(update_fields=["ativo"])
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Empresa ativada com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def deactivate(self, request, id_empresa=None):
        instance = self.get_object()
        instance.ativo = False
        instance.save(update_fields=["ativo"])
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Empresa desativada com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class FilialViewSet(viewsets.ModelViewSet):
    """ViewSet to manage Filial CRUD operations."""

    queryset = Filial.objects.all()
    serializer_class = FilialDto
    permission_classes = [IsAdminUser]
    lookup_field = "id_filial"

    def get_serializer_class(self):
        if self.action == "list":
            return FilialListDto
        return FilialDto

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "count": len(queryset),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "success": True,
                "message": "Filial criada com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                "success": True,
                "message": "Filial atualizada com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "success": True,
                "message": "Filial removida com sucesso",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, id_filial=None):
        instance = self.get_object()
        instance.ativo = True
        instance.save(update_fields=["ativo"])
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Filial ativada com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def deactivate(self, request, id_filial=None):
        instance = self.get_object()
        instance.ativo = False
        instance.save(update_fields=["ativo"])
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Filial desativada com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class SetorViewSet(viewsets.ModelViewSet):
    """ViewSet to manage Setor CRUD operations."""

    queryset = Setor.objects.all()
    serializer_class = SetorDto
    permission_classes = [IsAdminUser]
    lookup_field = "id_setor"

    def get_serializer_class(self):
        if self.action == "list":
            return SetorListDto
        return SetorDto

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "count": len(queryset),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "success": True,
                "message": "Setor criado com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                "success": True,
                "message": "Setor atualizado com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "success": True,
                "message": "Setor removido com sucesso",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, id_setor=None):
        instance = self.get_object()
        instance.ativo = True
        instance.save(update_fields=["ativo"])
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Setor ativado com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def deactivate(self, request, id_setor=None):
        instance = self.get_object()
        instance.ativo = False
        instance.save(update_fields=["ativo"])
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Setor desativado com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class PerfilViewSet(viewsets.ModelViewSet):
    """ViewSet to manage Perfil CRUD operations."""

    queryset = Perfil.objects.all()
    serializer_class = PerfilDto
    permission_classes = [IsAdminUser]
    lookup_field = "id_perfil"

    def get_serializer_class(self):
        if self.action == "list":
            return PerfilListDto
        return PerfilDto

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "count": len(queryset),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "success": True,
                "message": "Perfil criado com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(
            {
                "success": True,
                "message": "Perfil atualizado com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {
                "success": True,
                "message": "Perfil removido com sucesso",
            },
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, id_perfil=None):
        instance = self.get_object()
        instance.ativo = True
        instance.save(update_fields=["ativo"])
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Perfil ativado com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def deactivate(self, request, id_perfil=None):
        instance = self.get_object()
        instance.ativo = False
        instance.save(update_fields=["ativo"])
        serializer = self.get_serializer(instance)
        return Response(
            {
                "success": True,
                "message": "Perfil desativado com sucesso",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
