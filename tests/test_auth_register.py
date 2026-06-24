from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Empresa, Perfil, UsuarioAcesso


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

    def test_register_rejects_staff_creating_admin_user(self):
        admin = User.objects.create_user(
            email="admin@datagrapho.local",
            cpf="22222222222",
            nome="Administrador",
            password="SenhaSegura123",
            is_staff=True,
        )
        self.client.force_authenticate(user=admin)

        response = self.client.post(
            "/api/auth/register/",
            {**self.payload, "email": "staff-created-admin@datagrapho.local", "is_staff": True},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="staff-created-admin@datagrapho.local").exists())

    def test_register_rejects_staff_assigning_out_of_scope_company(self):
        admin = User.objects.create_user(
            email="admin.datafit@datagrapho.local",
            cpf="33333333333",
            nome="Admin Datafit",
            password="SenhaSegura123",
            is_staff=True,
        )
        datafit = Empresa.objects.create(nome="Datafit", cnpj="11.111.111/0001-11", ativo=True)
        datagrapho = Empresa.objects.create(nome="Datagrapho", cnpj="22.222.222/0001-22", ativo=True)
        perfil = Perfil.objects.create(nome="Operacional", ativo=True)
        UsuarioAcesso.objects.create(usuario=admin, empresa=datafit, perfil=perfil, ativo=True)
        self.client.force_authenticate(user=admin)

        response = self.client.post(
            "/api/auth/register/",
            {
                **self.payload,
                "email": "fora.escopo@datagrapho.local",
                "acessos": [{"id_empresa": datagrapho.id_empresa, "id_perfil": perfil.id_perfil, "ativo": True}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="fora.escopo@datagrapho.local").exists())
