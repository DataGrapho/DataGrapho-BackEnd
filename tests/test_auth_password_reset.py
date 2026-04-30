from __future__ import annotations

import hashlib
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import PasswordResetToken


User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@datagrapho.local",
            cpf="12345678901",
            nome="Usuario Teste",
            password="SenhaAntiga123",
        )

    def test_forgot_password_existing_email_returns_generic_and_sends_email(self):
        response = self.client.post(
            "/api/auth/password/forgot/",
            {"email": self.user.email},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PasswordResetToken.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

        email_body = mail.outbox[0].body
        token_match = re.search(r"token=([A-Za-z0-9_\-]+)", email_body)
        self.assertIsNotNone(token_match)

        raw_token = token_match.group(1)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        self.assertTrue(PasswordResetToken.objects.filter(token_hash=token_hash).exists())

    def test_forgot_password_unknown_email_returns_generic_without_side_effects(self):
        response = self.client.post(
            "/api/auth/password/forgot/",
            {"email": "naoexiste@datagrapho.local"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PasswordResetToken.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_forgot_password_invalid_email_returns_400(self):
        response = self.client.post(
            "/api/auth/password/forgot/",
            {"email": "email-invalido"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_reset_password_success_marks_token_as_used(self):
        raw_token = "token-reset-valido"
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        reset_token = PasswordResetToken.objects.create(
            usuario=self.user,
            token_hash=token_hash,
            expires_at=timezone.now() + timedelta(minutes=30),
        )

        response = self.client.post(
            "/api/auth/password/reset/",
            {
                "password": "NovaSenha123",
                "confirmPassword": "NovaSenha123",
                "token": raw_token,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NovaSenha123"))

        reset_token.refresh_from_db()
        self.assertIsNotNone(reset_token.usado_em)

    def test_reset_password_invalid_token_returns_400(self):
        response = self.client.post(
            "/api/auth/password/reset/",
            {
                "password": "NovaSenha123",
                "confirmPassword": "NovaSenha123",
                "token": "token-inexistente",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_reset_password_expired_token_returns_400(self):
        raw_token = "token-expirado"
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        PasswordResetToken.objects.create(
            usuario=self.user,
            token_hash=token_hash,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.post(
            "/api/auth/password/reset/",
            {
                "password": "NovaSenha123",
                "confirmPassword": "NovaSenha123",
                "token": raw_token,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_reset_password_rejects_reused_token(self):
        raw_token = "token-uso-unico"
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        PasswordResetToken.objects.create(
            usuario=self.user,
            token_hash=token_hash,
            expires_at=timezone.now() + timedelta(minutes=30),
        )

        first = self.client.post(
            "/api/auth/password/reset/",
            {
                "password": "NovaSenha123",
                "confirmPassword": "NovaSenha123",
                "token": raw_token,
            },
            format="json",
        )
        second = self.client.post(
            "/api/auth/password/reset/",
            {
                "password": "OutraSenha123",
                "confirmPassword": "OutraSenha123",
                "token": raw_token,
            },
            format="json",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)

    def test_reset_password_requires_matching_passwords(self):
        response = self.client.post(
            "/api/auth/password/reset/",
            {
                "password": "NovaSenha123",
                "confirmPassword": "OutraSenha123",
                "token": "qualquer-token",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
