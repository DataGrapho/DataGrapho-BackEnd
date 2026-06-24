from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Empresa, Filial, Perfil, Setor, UsuarioAcesso


User = get_user_model()


def get_admin_company_ids(user) -> set[int]:
    if user.is_superuser:
        return set()
    return set(
        UsuarioAcesso.objects.filter(usuario=user, ativo=True)
        .values_list("empresa_id", flat=True)
        .distinct()
    )


def validate_accesses_company_scope(user, acessos_data: list[dict] | None) -> None:
    if not acessos_data or user.is_superuser:
        return

    allowed_company_ids = get_admin_company_ids(user)
    if not allowed_company_ids:
        raise serializers.ValidationError(
            {"acessos": "Permissao insuficiente para gerenciar usuarios com os acessos informados."}
        )

    for access in acessos_data:
        empresa_id = access.get("id_empresa")
        if empresa_id not in allowed_company_ids:
            raise serializers.ValidationError(
                {"acessos": "Permissao insuficiente para atribuir acesso a esta empresa."}
            )


def validate_admin_role_promotion(user, attrs: dict, *, action: str) -> None:
    if user.is_superuser:
        return
    if attrs.get("is_staff") or attrs.get("is_superuser"):
        message = (
            "Apenas superusuarios podem criar administradores ou superusuarios."
            if action == "create"
            else "Apenas superusuarios podem promover administradores ou superusuarios."
        )
        raise serializers.ValidationError(message)


def create_user_accesses(user, acessos_data: list[dict]) -> list[UsuarioAcesso]:
    created_acessos = []
    for acesso in acessos_data:
        empresa = Empresa.objects.get(id_empresa=acesso["id_empresa"])
        filial = None
        if acesso.get("id_filial") is not None:
            filial = Filial.objects.get(id_filial=acesso["id_filial"], empresa=empresa)
        setor = None
        if acesso.get("id_setor") is not None:
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
    return created_acessos


class EmpresaDto(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ["id_empresa", "nome", "cnpj", "endereco", "ativo", "criado_em"]
        read_only_fields = ["id_empresa", "criado_em"]


class EmpresaListDto(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ["id_empresa", "nome", "cnpj", "ativo"]


class FilialDto(serializers.ModelSerializer):
    class Meta:
        model = Filial
        fields = ["id_filial", "empresa", "nome", "endereco", "ativo", "criado_em"]
        read_only_fields = ["id_filial", "criado_em"]


class FilialListDto(serializers.ModelSerializer):
    class Meta:
        model = Filial
        fields = ["id_filial", "empresa", "nome", "ativo"]


class SetorDto(serializers.ModelSerializer):
    class Meta:
        model = Setor
        fields = ["id_setor", "filial", "nome", "descricao", "ativo"]
        read_only_fields = ["id_setor"]


class SetorListDto(serializers.ModelSerializer):
    class Meta:
        model = Setor
        fields = ["id_setor", "filial", "nome", "ativo"]


class PerfilDto(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ["id_perfil", "nome", "descricao", "ativo"]
        read_only_fields = ["id_perfil"]


class PerfilListDto(serializers.ModelSerializer):
    class Meta:
        model = Perfil
        fields = ["id_perfil", "nome", "ativo"]


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
        fields = (
            "id_usuario",
            "cpf",
            "email",
            "nome",
            "is_active",
            "is_staff",
            "is_superuser",
            "data_criacao",
            "last_login",
        )


class UsuarioListDto(serializers.ModelSerializer):
    id_usuario = serializers.IntegerField(read_only=True)
    acessos = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id_usuario", "cpf", "email", "nome", "is_active", "is_staff", "is_superuser", "data_criacao", "acessos")

    def get_acessos(self, user):
        acessos = (
            UsuarioAcesso.objects.select_related("empresa", "filial", "setor", "perfil")
            .filter(usuario=user)
            .order_by("id")
        )
        return UsuarioAcessoDto(acessos, many=True).data


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
            raise serializers.ValidationError("Se id_setor for informado, id_filial tamb├®m deve ser informado.")
        return attrs


class UsuarioUpdateDto(serializers.ModelSerializer):
    password = serializers.CharField(min_length=6, write_only=True, required=False)
    acessos = UsuarioAcessoCreateDto(many=True, required=False)

    class Meta:
        model = User
        fields = ("email", "cpf", "nome", "password", "is_active", "is_staff", "is_superuser", "acessos")

    def validate_email(self, value: str):
        user = self.instance
        if user and User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("Email j├í cadastrado.")
        return value

    def validate_cpf(self, value: str):
        user = self.instance
        if user and User.objects.filter(cpf=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("CPF j├í cadastrado.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        if request is not None:
            validate_admin_role_promotion(request.user, attrs, action="update")
            if not request.user.is_superuser and "acessos" in attrs:
                validate_accesses_company_scope(request.user, attrs.get("acessos"))
        return attrs

    def update(self, instance, validated_data):
        acessos_data = validated_data.pop("acessos", None)
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if acessos_data is not None:
            instance.acessos.all().delete()
            create_user_accesses(instance, acessos_data)

        return instance


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


class RegisterDto(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    cpf = serializers.CharField(max_length=14)
    nome = serializers.CharField(max_length=200)
    password = serializers.CharField(min_length=6, write_only=True)
    is_active = serializers.BooleanField(required=False, default=True)
    is_staff = serializers.BooleanField(required=False, default=False)
    is_superuser = serializers.BooleanField(required=False, default=False)
    acessos = UsuarioAcessoCreateDto(many=True, required=False)

    def validate(self, attrs):
        request = self.context.get("request")
        if request is not None:
            validate_admin_role_promotion(request.user, attrs, action="create")
            if not request.user.is_superuser:
                validate_accesses_company_scope(request.user, attrs.get("acessos"))
        return attrs

    def validate_email(self, value: str):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email j├í cadastrado.")
        return value

    def validate_cpf(self, value: str):
        if User.objects.filter(cpf=value).exists():
            raise serializers.ValidationError("CPF j├í cadastrado.")
        return value

    def create(self, validated_data):
        acessos_data = validated_data.pop("acessos", [])
        password = validated_data.pop("password")
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save(update_fields=["password"])

        created_acessos = create_user_accesses(user, acessos_data)

        return user, created_acessos


class ForgotPasswordDto(serializers.Serializer):
    email = serializers.EmailField(max_length=255)


class ResetPasswordDto(serializers.Serializer):
    password = serializers.CharField(min_length=6, write_only=True)
    confirmPassword = serializers.CharField(min_length=6, write_only=True)
    token = serializers.CharField(max_length=255)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirmPassword"]:
            raise serializers.ValidationError({"confirmPassword": ["As senhas n├úo conferem."]})
        return attrs
