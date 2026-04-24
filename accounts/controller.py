from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .dto import LoginTokenDto, RegisterDto, UsuarioAcessoDto, UsuarioMeDto


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
