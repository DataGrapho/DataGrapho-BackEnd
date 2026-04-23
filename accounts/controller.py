from __future__ import annotations

from django.conf import settings

from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .dto import LoginTokenDto, RegisterDto, UsuarioAcessoDto, UsuarioMeDto


class LoginView(TokenObtainPairView):
    serializer_class = LoginTokenDto


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioMeDto(request.user).data)


class RegisterView(APIView):
    """Create a new Usuario and optionally UsuarioAcesso records.

    In development (DEBUG=True), this endpoint is open to bootstrap data.
    In non-debug environments, it requires an admin/staff user.
    """

    def get_permissions(self):
        if getattr(settings, "DEBUG", False):
            return [AllowAny()]
        return [IsAdminUser()]

    def post(self, request):
        serializer = RegisterDto(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, acessos = serializer.save()

        response = {
            "usuario": UsuarioMeDto(user).data,
            "acessos": UsuarioAcessoDto(acessos, many=True).data,
        }
        return Response(response, status=201)
