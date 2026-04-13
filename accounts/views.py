from __future__ import annotations

from django.conf import settings

from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import LoginTokenSerializer, RegisterSerializer, UsuarioAcessoSerializer, UsuarioMeSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginTokenSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UsuarioMeSerializer(request.user).data)


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
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, acessos = serializer.save()

        response = {
            "usuario": UsuarioMeSerializer(user).data,
            "acessos": UsuarioAcessoSerializer(acessos, many=True).data,
        }
        return Response(response, status=201)
