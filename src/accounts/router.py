from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .controller import (
    EmpresaViewSet,
    FilialViewSet,
    ForgotPasswordView,
    LoginView,
    MeView,
    PerfilViewSet,
    RegisterView,
    ResetPasswordView,
    SetorViewSet,
    UsuarioViewSet,
)

app_name = "accounts"

router = DefaultRouter()
router.register(r"usuarios", UsuarioViewSet, basename="usuario")
router.register(r"empresas", EmpresaViewSet, basename="empresa")
router.register(r"filiais", FilialViewSet, basename="filial")
router.register(r"setores", SetorViewSet, basename="setor")
router.register(r"perfis", PerfilViewSet, basename="perfil")

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("password/forgot/", ForgotPasswordView.as_view(), name="auth-password-forgot"),
    path("password/reset/", ResetPasswordView.as_view(), name="auth-password-reset"),
    path("", include(router.urls)),
]
