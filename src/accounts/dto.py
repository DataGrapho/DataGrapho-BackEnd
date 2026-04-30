from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Empresa, Filial, Perfil, Setor, UsuarioAcesso


User = get_user_model()


class EmpresaDto(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ("id_empresa", "nome", "cnpj")


class FilialDto(serializers.ModelSerializer):
    class Meta:
        model = Filial
        fields = ("id_filial", "nome")


class SetorDto(serializers.ModelSerializer):
    class Meta:
        model = Setor
        fields = ("id_setor", "nome")


class PerfilDto(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ("id_perfil", "nome")


class UsuarioAcessoDto(serializers.ModelSerializer):
    empresa = EmpresaDto()
    filial = FilialDto(allow_null=True)
    setor = SetorDto(allow_null=True)
    perfil = PerfilDto()

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


class UsuarioMeDto(serializers.ModelSerializer):
    id_usuario = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = ("id_usuario", "cpf", "email", "nome", "is_active", "data_criacao", "last_login")


class LoginTokenDto(TokenObtainPairSerializer):
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
        data["usuario"] = UsuarioMeDto(user).data
        data["acessos"] = UsuarioAcessoDto(acessos, many=True).data
        return data


class UsuarioAcessoCreateDto(serializers.Serializer):
    id_empresa = serializers.IntegerField()
    id_filial = serializers.IntegerField(required=False, allow_null=True)
    id_setor = serializers.IntegerField(required=False, allow_null=True)
    id_perfil = serializers.IntegerField()
    ativo = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        id_filial = attrs.get("id_filial")
        id_setor = attrs.get("id_setor")
        if id_setor is not None and id_filial is None:
            raise serializers.ValidationError("Se id_setor for informado, id_filial também deve ser informado.")
        return attrs


class RegisterDto(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    cpf = serializers.CharField(max_length=14)
    nome = serializers.CharField(max_length=200)
    password = serializers.CharField(min_length=6, write_only=True)
    is_active = serializers.BooleanField(required=False, default=True)
    acessos = UsuarioAcessoCreateDto(many=True, required=False)

    def validate_email(self, value: str):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email já cadastrado.")
        return value

    def validate_cpf(self, value: str):
        if User.objects.filter(cpf=value).exists():
            raise serializers.ValidationError("CPF já cadastrado.")
        return value

    def create(self, validated_data):
        acessos_data = validated_data.pop("acessos", [])
        password = validated_data.pop("password")
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save(update_fields=["password"])

        created_acessos = []
        for acesso in acessos_data:
            empresa = Empresa.objects.get(id_empresa=acesso["id_empresa"])
            filial = None
            if acesso.get("id_filial") is not None:
                filial = Filial.objects.get(id_filial=acesso["id_filial"], empresa=empresa)
            setor = None
            if acesso.get("id_setor") is not None:
                if filial is None:
                    raise serializers.ValidationError("Se id_setor for informado, id_filial também deve ser informado.")
                setor = Setor.objects.get(id_setor=acesso["id_setor"], filial=filial)
            perfil = Perfil.objects.get(id_perfil=acesso["id_perfil"])

            created_acessos.append(
                UsuarioAcesso.objects.create(
                    usuario=user,
                    empresa=empresa,
                    filial=filial,
                    setor=setor,
                    perfil=perfil,
                    ativo=acesso.get("ativo", True),
                )
            )

        return user, created_acessos
