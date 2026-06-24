from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()


class RegisterApiPermissionTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.payload = {
            "email": "novo@datagrapho.local",
            "cpf": "12345678901",
            "nome": "Novo Usuario",
            "password": "SenhaSegura123",
        }

    def test_register_requires_authentication_even_when_debug_is_enabled(self):
        response = self.client.post("/api/auth/register/", self.payload, format="json")

        self.assertEqual(response.status_code, 401)
        self.assertFalse(User.objects.filter(email=self.payload["email"]).exists())

    def test_register_rejects_authenticated_non_admin_user(self):
        user = User.objects.create_user(
            email="comum@datagrapho.local",
            cpf="11111111111",
            nome="Usuario Comum",
            password="SenhaSegura123",
        )
        self.client.force_authenticate(user=user)

        response = self.client.post("/api/auth/register/", self.payload, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(email=self.payload["email"]).exists())

    def test_register_allows_authenticated_staff_user(self):
        admin = User.objects.create_user(
            email="admin@datagrapho.local",
            cpf="22222222222",
            nome="Administrador",
            password="SenhaSegura123",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin)

        response = self.client.post("/api/auth/register/", self.payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email=self.payload["email"]).exists())
