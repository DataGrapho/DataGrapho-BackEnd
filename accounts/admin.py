from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Empresa, Filial, Perfil, Setor, Usuario, UsuarioAcesso


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario

    ordering = ("email",)
    list_display = ("id_usuario", "email", "cpf", "nome", "is_active", "is_staff")
    search_fields = ("email", "cpf", "nome")
    list_filter = ("is_active", "is_staff", "is_superuser")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados", {"fields": ("cpf", "nome")}),
        ("Status", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Permissões", {"fields": ("groups", "user_permissions")}),
        ("Datas", {"fields": ("data_criacao", "last_login")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "cpf", "nome", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )

    readonly_fields = ("data_criacao", "last_login")


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("id_empresa", "nome", "cnpj", "ativo", "criado_em")
    search_fields = ("nome", "cnpj")
    list_filter = ("ativo",)


@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    list_display = ("id_filial", "nome", "empresa", "ativo", "criado_em")
    search_fields = ("nome",)
    list_filter = ("ativo", "empresa")


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ("id_setor", "nome", "filial", "ativo")
    search_fields = ("nome",)
    list_filter = ("ativo", "filial")


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("id_perfil", "nome", "ativo")
    search_fields = ("nome",)
    list_filter = ("ativo",)


@admin.register(UsuarioAcesso)
class UsuarioAcessoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "empresa", "filial", "setor", "perfil", "ativo", "criado_em")
    list_filter = ("ativo", "empresa", "perfil")
    search_fields = ("usuario__email", "usuario__cpf")
