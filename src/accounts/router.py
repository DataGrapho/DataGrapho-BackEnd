from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .controller import ForgotPasswordView, LoginView, MeView, RegisterView, ResetPasswordView

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("password/forgot/", ForgotPasswordView.as_view(), name="auth-password-forgot"),
    path("password/reset/", ResetPasswordView.as_view(), name="auth-password-reset"),
]
