import json
from typing import Any, Dict, List

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.dominios import dominios_do_usuario
from accounts.models import DominioAcesso, Empresa, Filial, Perfil, Setor, Usuario, UsuarioAcesso
from chatbot.core.ai_providers import AIResponse
from chatbot.core.engine import FunctionCallingEngine
from chatbot.core.tool_registry import ToolRegistry, get_tool_registry
from chatbot.domains.convenio.repository import ConvenioRepository
from chatbot.domains.convenio.tools import register_convenio_tools
from chatbot.domains.vendas.repository import VendasRepository
from chatbot.domains.vendas.tools import register_vendas_tools


DOMINIOS_TESTE = {**settings.CHATBOT_CONFIG, "ACTIVE_DOMAINS": ["convenio", "vendas"]}


class FakeProvider:
    """Provedor falso: registra as ferramentas recebidas e responde sem chamar nada."""

    def __init__(self):
        self.tools_received: List[List[str]] = []

    def chat_completion(self, messages, tools=None, temperature=0.0):
        self.tools_received.append([t["function"]["name"] for t in (tools or [])])
        return AIResponse(content="resposta de teste", tool_calls=None)


def criar_estrutura():
    """Duas empresas: A (filiais F1 com setor S1, e F2) e B (filial F3)."""
    perfil = Perfil.objects.create(nome="Analista")
    empresa_a = Empresa.objects.create(nome="Empresa A", cnpj="00.000.000/0001-01")
    empresa_b = Empresa.objects.create(nome="Empresa B", cnpj="00.000.000/0002-02")
    filial_1 = Filial.objects.create(empresa=empresa_a, nome="Filial 1")
    filial_2 = Filial.objects.create(empresa=empresa_a, nome="Filial 2")
    filial_3 = Filial.objects.create(empresa=empresa_b, nome="Filial 3")
    setor_1 = Setor.objects.create(filial=filial_1, nome="Setor 1")
    return {
        "perfil": perfil,
        "empresa_a": empresa_a,
        "empresa_b": empresa_b,
        "filial_1": filial_1,
        "filial_2": filial_2,
        "filial_3": filial_3,
        "setor_1": setor_1,
    }


def criar_usuario(email: str, cpf: str, **acesso) -> Usuario:
    usuario = Usuario.objects.create_user(email=email, password="senha-123", cpf=cpf, nome=email)
    if acesso:
        UsuarioAcesso.objects.create(usuario=usuario, **acesso)
    return usuario


@override_settings(CHATBOT_CONFIG=DOMINIOS_TESTE)
class DominiosDoUsuarioTest(TestCase):
    def setUp(self):
        e = criar_estrutura()
        self.e = e
        self.user_f1 = criar_usuario(
            "f1@teste.com", "111.111.111-11",
            empresa=e["empresa_a"], filial=e["filial_1"], setor=e["setor_1"], perfil=e["perfil"],
        )
        self.user_f2 = criar_usuario(
            "f2@teste.com", "222.222.222-22",
            empresa=e["empresa_a"], filial=e["filial_2"], perfil=e["perfil"],
        )
        self.user_b = criar_usuario(
            "b@teste.com", "333.333.333-33", empresa=e["empresa_b"], perfil=e["perfil"],
        )

    def test_usuario_sem_concessao_nao_ve_nenhum_dominio(self):
        self.assertEqual(dominios_do_usuario(self.user_f1), set())

    def test_superusuario_ve_todos_os_dominios_ativos(self):
        admin = Usuario.objects.create_superuser(email="root@teste.com", password="x", cpf="999.999.999-99", nome="Root")
        self.assertEqual(dominios_do_usuario(admin), {"convenio", "vendas"})

    def test_concessao_de_empresa_alcanca_filiais_setores_e_usuarios(self):
        DominioAcesso.objects.create(dominio="convenio", empresa=self.e["empresa_a"])

        self.assertEqual(dominios_do_usuario(self.user_f1), {"convenio"})
        self.assertEqual(dominios_do_usuario(self.user_f2), {"convenio"})
        self.assertEqual(dominios_do_usuario(self.user_b), set())

    def test_concessao_de_filial_nao_alcanca_outras_filiais_da_mesma_empresa(self):
        DominioAcesso.objects.create(dominio="vendas", filial=self.e["filial_2"])

        self.assertEqual(dominios_do_usuario(self.user_f2), {"vendas"})
        self.assertEqual(dominios_do_usuario(self.user_f1), set())

    def test_concessao_de_setor_alcanca_apenas_quem_esta_no_setor(self):
        DominioAcesso.objects.create(dominio="convenio", setor=self.e["setor_1"])

        self.assertEqual(dominios_do_usuario(self.user_f1), {"convenio"})
        self.assertEqual(dominios_do_usuario(self.user_f2), set())

    def test_concessao_de_usuario_vale_apenas_para_ele(self):
        DominioAcesso.objects.create(dominio="vendas", usuario=self.user_f2)

        self.assertEqual(dominios_do_usuario(self.user_f2), {"vendas"})
        self.assertEqual(dominios_do_usuario(self.user_f1), set())

    def test_dominio_inativo_nao_e_liberado(self):
        DominioAcesso.objects.create(dominio="wine", empresa=self.e["empresa_a"])
        self.assertEqual(dominios_do_usuario(self.user_f1), set())

    def test_usuario_com_acessos_em_duas_empresas_recebe_a_uniao(self):
        UsuarioAcesso.objects.create(
            usuario=self.user_f2, empresa=self.e["empresa_b"], perfil=self.e["perfil"],
        )
        DominioAcesso.objects.create(dominio="convenio", empresa=self.e["empresa_a"])
        DominioAcesso.objects.create(dominio="vendas", empresa=self.e["empresa_b"])

        self.assertEqual(dominios_do_usuario(self.user_f2), {"convenio", "vendas"})


@override_settings(CHATBOT_CONFIG=DOMINIOS_TESTE)
class EngineRestricaoDominioTest(TestCase):
    def setUp(self):
        self.registry = ToolRegistry()
        register_convenio_tools(self.registry)
        register_vendas_tools(self.registry)
        self.provider = FakeProvider()
        self.engine = FunctionCallingEngine(
            ai_provider=self.provider,
            tool_registry=self.registry,
            repositories={"convenio": ConvenioRepository(), "vendas": VendasRepository()},
        )

    def test_ia_recebe_apenas_ferramentas_dos_dominios_liberados(self):
        self.engine.execute_query("oi", allowed_domains={"convenio"})

        recebidas = self.provider.tools_received[-1]
        self.assertTrue(recebidas)
        self.assertTrue(all(nome.startswith("get_convenio") for nome in recebidas))

    def test_sem_dominios_liberados_a_ia_nao_e_chamada(self):
        result = self.engine.execute_query("quanto vendemos?", allowed_domains=set())

        self.assertEqual(self.provider.tools_received, [])
        self.assertIn("não tem acesso", result.response)

    def test_execucao_de_ferramenta_fora_do_dominio_e_bloqueada(self):
        with self.assertRaises(ValueError):
            self.engine._execute_tool(
                "get_vendas_periodo",
                json.dumps({"data_inicio": "2026-01-01", "data_fim": "2026-12-31"}),
                allowed_domains={"convenio"},
            )

    def test_sem_restricao_explicita_todas_as_ferramentas_sao_enviadas(self):
        self.engine.execute_query("oi")

        recebidas = self.provider.tools_received[-1]
        self.assertTrue(any(n.startswith("get_vendas") for n in recebidas))
        self.assertTrue(any(n.startswith("get_convenio") for n in recebidas))


@override_settings(CHATBOT_CONFIG=DOMINIOS_TESTE)
class DominioAcessoApiTest(TestCase):
    def setUp(self):
        e = criar_estrutura()
        self.e = e
        self.url = reverse("accounts:auth-dominio-acessos")
        self.admin_a = criar_usuario(
            "admin-a@teste.com", "444.444.444-44",
            empresa=e["empresa_a"], perfil=e["perfil"],
        )
        self.admin_a.is_staff = True
        self.admin_a.save(update_fields=["is_staff"])
        self.superuser = Usuario.objects.create_superuser(
            email="root@teste.com", password="x", cpf="555.555.555-55", nome="Root"
        )
        self.client = APIClient()

    def _post(self, user, payload):
        self.client.force_authenticate(user=user)
        return self.client.post(self.url, payload, format="json")

    def test_admin_de_empresa_concede_a_filial_de_sua_empresa(self):
        response = self._post(self.admin_a, {"dominio": "convenio", "nivel": "filial", "alvo": self.e["filial_1"].pk})

        self.assertEqual(response.status_code, 201)
        self.assertTrue(DominioAcesso.objects.filter(dominio="convenio", filial=self.e["filial_1"]).exists())

    def test_admin_nao_concede_a_empresa_de_outro_escopo(self):
        response = self._post(self.admin_a, {"dominio": "convenio", "nivel": "empresa", "alvo": self.e["empresa_b"].pk})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(DominioAcesso.objects.exists())

    def test_admin_nao_concede_a_filial_de_outro_escopo(self):
        response = self._post(self.admin_a, {"dominio": "convenio", "nivel": "filial", "alvo": self.e["filial_3"].pk})

        self.assertEqual(response.status_code, 403)

    def test_superusuario_concede_em_qualquer_escopo(self):
        response = self._post(self.superuser, {"dominio": "vendas", "nivel": "empresa", "alvo": self.e["empresa_b"].pk})

        self.assertEqual(response.status_code, 201)

    def test_dominio_invalido_e_recusado(self):
        response = self._post(self.superuser, {"dominio": "inexistente", "nivel": "empresa", "alvo": self.e["empresa_a"].pk})

        self.assertEqual(response.status_code, 400)

    def test_concessao_duplicada_retorna_conflito(self):
        self._post(self.superuser, {"dominio": "convenio", "nivel": "empresa", "alvo": self.e["empresa_a"].pk})
        response = self._post(self.superuser, {"dominio": "convenio", "nivel": "empresa", "alvo": self.e["empresa_a"].pk})

        self.assertEqual(response.status_code, 409)

    def test_listagem_mostra_concessoes_herdadas_de_niveis_acima(self):
        DominioAcesso.objects.create(dominio="convenio", empresa=self.e["empresa_a"])
        self.client.force_authenticate(user=self.admin_a)

        response = self.client.get(self.url, {"nivel": "filial", "alvo": self.e["filial_1"].pk})

        self.assertEqual(response.status_code, 200)
        dados = response.json()["data"]
        self.assertEqual(dados["diretos"], [])
        self.assertEqual(dados["herdados"][0]["dominio"], "convenio")
        self.assertEqual(dados["herdados"][0]["nivel"], "empresa")
        self.assertEqual(dados["herdados"][0]["origem"], "Empresa A")

    def test_admin_nao_remove_concessao_de_outro_escopo(self):
        concessao = DominioAcesso.objects.create(dominio="convenio", empresa=self.e["empresa_b"])
        self.client.force_authenticate(user=self.admin_a)

        response = self.client.delete(reverse("accounts:auth-dominio-acesso-detail", args=[concessao.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(DominioAcesso.objects.filter(pk=concessao.pk).exists())

    def test_admin_remove_concessao_do_proprio_escopo(self):
        concessao = DominioAcesso.objects.create(dominio="convenio", filial=self.e["filial_1"])
        self.client.force_authenticate(user=self.admin_a)

        response = self.client.delete(reverse("accounts:auth-dominio-acesso-detail", args=[concessao.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(DominioAcesso.objects.filter(pk=concessao.pk).exists())

    def test_usuario_comum_nao_acessa_a_administracao(self):
        comum = criar_usuario("comum@teste.com", "666.666.666-66", empresa=self.e["empresa_a"], perfil=self.e["perfil"])
        self.client.force_authenticate(user=comum)

        response = self.client.get(self.url, {"nivel": "empresa", "alvo": self.e["empresa_a"].pk})

        self.assertEqual(response.status_code, 403)

    def test_lista_de_dominios_disponiveis(self):
        self.client.force_authenticate(user=self.superuser)

        response = self.client.get(reverse("accounts:auth-dominios"))

        self.assertEqual(response.status_code, 200)
        chaves = [item["chave"] for item in response.json()["data"]]
        self.assertEqual(chaves, ["convenio", "vendas"])


class ChatRespeitaConcessoesTest(TestCase):
    """Garante que o endpoint de saúde do chat lista só as ferramentas liberadas."""

    @override_settings(CHATBOT_CONFIG=DOMINIOS_TESTE)
    def test_health_mostra_apenas_ferramentas_do_usuario(self):
        estrutura = criar_estrutura()
        usuario = criar_usuario(
            "chat@teste.com", "777.777.777-77", empresa=estrutura["empresa_a"], perfil=estrutura["perfil"],
        )
        DominioAcesso.objects.create(dominio="vendas", empresa=estrutura["empresa_a"])
        client = APIClient()
        client.force_authenticate(user=usuario)

        response = client.get(reverse("chatbot:health-check"))

        self.assertEqual(response.status_code, 200)
        dados: Dict[str, Any] = response.json()
        self.assertEqual(dados["domains"], ["vendas"])
        # O registro global é carregado na inicialização; comparamos com o que ele tem de vendas.
        esperadas = {t.name for t in get_tool_registry().get_tools_for_domains({"vendas"})}
        self.assertEqual(set(dados["tools"]), esperadas)
