from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Empresa, Filial, Perfil, Setor

User = get_user_model()


class AccountsCrudApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Regular user
        self.user = User.objects.create_user(
            email="user@datagrapho.local",
            cpf="11111111111",
            nome="User Comum",
            password="Password123",
        )

        # Staff user (admin)
        self.admin = User.objects.create_user(
            email="admin@datagrapho.local",
            cpf="22222222222",
            nome="Admin Staff",
            password="Password123",
            is_staff=True,
        )

        # Sample data
        self.empresa = Empresa.objects.create(
            nome="Empresa Teste",
            cnpj="12.345.678/0001-90",
            endereco="Rua Teste, 123",
            ativo=True,
        )

        self.filial = Filial.objects.create(
            empresa=self.empresa,
            nome="Filial Teste",
            endereco="Rua Filial, 456",
            ativo=True,
        )

        self.setor = Setor.objects.create(
            filial=self.filial,
            nome="Setor Teste",
            descricao="Descricao Setor",
            ativo=True,
        )

        self.perfil = Perfil.objects.create(
            nome="Perfil Teste",
            descricao="Descricao Perfil",
            ativo=True,
        )

    # --- PERMISSION TESTS ---

    def test_crud_requires_authentication(self):
        endpoints = [
            "/api/auth/empresas/",
            "/api/auth/filiais/",
            "/api/auth/setores/",
            "/api/auth/perfis/",
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 401, f"Failed for url {url}")

    def test_crud_rejects_non_staff_user(self):
        self.client.force_authenticate(user=self.user)
        endpoints = [
            "/api/auth/empresas/",
            "/api/auth/filiais/",
            "/api/auth/setores/",
            "/api/auth/perfis/",
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403, f"Failed for url {url}")

    def test_crud_allows_staff_user(self):
        self.client.force_authenticate(user=self.admin)
        endpoints = [
            ("/api/auth/empresas/", 1),
            ("/api/auth/filiais/", 1),
            ("/api/auth/setores/", 1),
            ("/api/auth/perfis/", 1),
        ]
        for url, expected_count in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"Failed for url {url}")
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["count"], expected_count)

    # --- EMPRESA CRUD TESTS ---

    def test_empresa_create(self):
        self.client.force_authenticate(user=self.admin)
        payload = {
            "nome": "Nova Empresa",
            "cnpj": "98.765.432/0001-10",
            "endereco": "Avenida Paulista, 1000",
            "ativo": True,
        }
        response = self.client.post("/api/auth/empresas/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["nome"], "Nova Empresa")
        self.assertTrue(Empresa.objects.filter(cnpj="98.765.432/0001-10").exists())

    def test_empresa_retrieve(self):
        self.client.force_authenticate(user=self.admin)
        url = f"/api/auth/empresas/{self.empresa.id_empresa}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["nome"], "Empresa Teste")

    def test_empresa_update(self):
        self.client.force_authenticate(user=self.admin)
        url = f"/api/auth/empresas/{self.empresa.id_empresa}/"
        payload = {
            "nome": "Empresa Alterada",
            "cnpj": "12.345.678/0001-90",
            "endereco": "Novo Endereco",
        }
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["nome"], "Empresa Alterada")
        self.empresa.refresh_from_db()
        self.assertEqual(self.empresa.nome, "Empresa Alterada")

    def test_empresa_delete(self):
        self.client.force_authenticate(user=self.admin)
        # Note: Empresa has FKs in Filial (PROTECT), so let's delete filial and sector first to allow deletion
        self.setor.delete()
        self.filial.delete()

        url = f"/api/auth/empresas/{self.empresa.id_empresa}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Empresa.objects.filter(id_empresa=self.empresa.id_empresa).exists())

    def test_empresa_activate_deactivate(self):
        self.client.force_authenticate(user=self.admin)
        url_deactivate = f"/api/auth/empresas/{self.empresa.id_empresa}/deactivate/"
        url_activate = f"/api/auth/empresas/{self.empresa.id_empresa}/activate/"

        # Deactivate
        response = self.client.post(url_deactivate)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["data"]["ativo"])
        self.empresa.refresh_from_db()
        self.assertFalse(self.empresa.ativo)

        # Activate
        response = self.client.post(url_activate)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["ativo"])
        self.empresa.refresh_from_db()
        self.assertTrue(self.empresa.ativo)

    # --- FILIAL CRUD TESTS ---

    def test_filial_create(self):
        self.client.force_authenticate(user=self.admin)
        payload = {
            "empresa": self.empresa.id_empresa,
            "nome": "Nova Filial",
            "endereco": "Outro Endereco, 99",
            "ativo": True,
        }
        response = self.client.post("/api/auth/filiais/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["nome"], "Nova Filial")
        self.assertTrue(Filial.objects.filter(nome="Nova Filial").exists())

    def test_filial_activate_deactivate(self):
        self.client.force_authenticate(user=self.admin)
        url_deactivate = f"/api/auth/filiais/{self.filial.id_filial}/deactivate/"
        url_activate = f"/api/auth/filiais/{self.filial.id_filial}/activate/"

        response = self.client.post(url_deactivate)
        self.assertEqual(response.status_code, 200)
        self.filial.refresh_from_db()
        self.assertFalse(self.filial.ativo)

        response = self.client.post(url_activate)
        self.assertEqual(response.status_code, 200)
        self.filial.refresh_from_db()
        self.assertTrue(self.filial.ativo)

    # --- SETOR CRUD TESTS ---

    def test_setor_create(self):
        self.client.force_authenticate(user=self.admin)
        payload = {
            "filial": self.filial.id_filial,
            "nome": "Novo Setor",
            "descricao": "Desc",
            "ativo": True,
        }
        response = self.client.post("/api/auth/setores/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["nome"], "Novo Setor")
        self.assertTrue(Setor.objects.filter(nome="Novo Setor").exists())

    def test_setor_activate_deactivate(self):
        self.client.force_authenticate(user=self.admin)
        url_deactivate = f"/api/auth/setores/{self.setor.id_setor}/deactivate/"
        url_activate = f"/api/auth/setores/{self.setor.id_setor}/activate/"

        response = self.client.post(url_deactivate)
        self.assertEqual(response.status_code, 200)
        self.setor.refresh_from_db()
        self.assertFalse(self.setor.ativo)

        response = self.client.post(url_activate)
        self.assertEqual(response.status_code, 200)
        self.setor.refresh_from_db()
        self.assertTrue(self.setor.ativo)

    # --- PERFIL CRUD TESTS ---

    def test_perfil_create(self):
        self.client.force_authenticate(user=self.admin)
        payload = {
            "nome": "Novo Perfil",
            "descricao": "Desc",
            "ativo": True,
        }
        response = self.client.post("/api/auth/perfis/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["nome"], "Novo Perfil")
        self.assertTrue(Perfil.objects.filter(nome="Novo Perfil").exists())

    def test_perfil_activate_deactivate(self):
        self.client.force_authenticate(user=self.admin)
        url_deactivate = f"/api/auth/perfis/{self.perfil.id_perfil}/deactivate/"
        url_activate = f"/api/auth/perfis/{self.perfil.id_perfil}/activate/"

        response = self.client.post(url_deactivate)
        self.assertEqual(response.status_code, 200)
        self.perfil.refresh_from_db()
        self.assertFalse(self.perfil.ativo)

        response = self.client.post(url_activate)
        self.assertEqual(response.status_code, 200)
        self.perfil.refresh_from_db()
        self.assertTrue(self.perfil.ativo)
