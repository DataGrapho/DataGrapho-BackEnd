from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Empresa, Filial, Perfil, Setor, UsuarioAcesso


User = get_user_model()


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ("id_empresa", "nome", "cnpj")


class FilialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filial
        fields = ("id_filial", "nome")


class SetorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setor
        fields = ("id_setor", "nome")


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ("id_perfil", "nome")


class UsuarioAcessoSerializer(serializers.ModelSerializer):
    empresa = EmpresaSerializer()
    filial = FilialSerializer(allow_null=True)
    setor = SetorSerializer(allow_null=True)
    perfil = PerfilSerializer()

    class Meta:
        model = UsuarioAcesso
        fields = (
            "id",
            "empresa",
            "filial",
            "setor",
            "perfil",
            "ativo",
            "criado_em",
        )


class UsuarioMeSerializer(serializers.ModelSerializer):
    id_usuario = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = ("id_usuario", "cpf", "email", "nome", "is_active", "data_criacao", "last_login")


class LoginTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["id_usuario"] = user.id_usuario
        token["email"] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        acessos = (
            UsuarioAcesso.objects.select_related("empresa", "filial", "setor", "perfil")
            .filter(usuario=user, ativo=True)
            .order_by("id")
        )
        data["usuario"] = UsuarioMeSerializer(user).data
        data["acessos"] = UsuarioAcessoSerializer(acessos, many=True).data
        return data
