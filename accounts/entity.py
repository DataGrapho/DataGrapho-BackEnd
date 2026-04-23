from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("O email deve ser informado")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password is None:
            user.set_unusable_password()
        else:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email=email, password=password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email=email, password=password, **extra_fields)


class Empresa(models.Model):
    id_empresa = models.AutoField(primary_key=True, db_column="id_empresa")
    nome = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=18, unique=True)
    endereco = models.TextField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "empresa"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.nome} ({self.cnpj})"


class Filial(models.Model):
    id_filial = models.AutoField(primary_key=True, db_column="id_filial")
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, db_column="id_empresa", related_name="filiais")
    nome = models.CharField(max_length=200)
    endereco = models.TextField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "filial"

    def __str__(self) -> str:  # pragma: no cover
        return self.nome


class Setor(models.Model):
    id_setor = models.AutoField(primary_key=True, db_column="id_setor")
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, db_column="id_filial", related_name="setores")
    nome = models.CharField(max_length=200)
    descricao = models.TextField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = "setor"

    def __str__(self) -> str:  # pragma: no cover
        return self.nome


class Perfil(models.Model):
    id_perfil = models.AutoField(primary_key=True, db_column="id_perfil")
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = "perfil"

    def __str__(self) -> str:  # pragma: no cover
        return self.nome


class Usuario(AbstractBaseUser, PermissionsMixin):
    id_usuario = models.AutoField(primary_key=True, db_column="id_usuario")
    cpf = models.CharField(max_length=14, unique=True)
    email = models.EmailField(max_length=255, unique=True)
    # Keep Django's auth field name as `password`, but store it in `senha_hash` column.
    password = models.CharField(max_length=128, db_column="senha_hash")
    nome = models.CharField(max_length=200)

    is_active = models.BooleanField(default=True, db_column="ativo")
    data_criacao = models.DateTimeField(default=timezone.now, db_column="data_criacao")
    last_login = models.DateTimeField(null=True, blank=True, db_column="ultimo_acesso")

    # Required for admin.
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["cpf", "nome"]

    class Meta:
        db_table = "usuario"

    def __str__(self) -> str:  # pragma: no cover
        return self.email


class UsuarioAcesso(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, db_column="id_usuario", related_name="acessos")
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, db_column="id_empresa", related_name="acessos")
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        db_column="id_filial",
        related_name="acessos",
        null=True,
        blank=True,
    )
    setor = models.ForeignKey(
        Setor,
        on_delete=models.PROTECT,
        db_column="id_setor",
        related_name="acessos",
        null=True,
        blank=True,
    )
    perfil = models.ForeignKey(Perfil, on_delete=models.PROTECT, db_column="id_perfil", related_name="acessos")

    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "usuario_acesso"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "empresa", "filial", "setor"],
                name="uq_usuario_acesso",
            ),
            models.CheckConstraint(
                name="chk_hierarquia_acesso",
                condition=(
                    (Q(setor__isnull=True) | (Q(filial__isnull=False) & Q(empresa__isnull=False)))
                    & (Q(filial__isnull=True) | Q(empresa__isnull=False))
                ),
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.usuario.email} @ {self.empresa.nome}"
