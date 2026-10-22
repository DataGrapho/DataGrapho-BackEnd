from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import Empresa, Filial, Perfil, Setor, Usuario, UsuarioAcesso
from accounts.seed import SENHA_DEMO_USUARIOS, seed_demo_organizacao, seed_demo_usuarios


class SeedOrganizacaoTest(TestCase):
    def test_cria_ao_menos_tres_empresas_com_um_hospital(self):
        seed_demo_organizacao()

        self.assertGreaterEqual(Empresa.objects.count(), 3)
        self.assertTrue(Empresa.objects.filter(nome__icontains="Hospital").exists())

    def test_cria_filiais_e_setores_para_cada_empresa(self):
        seed_demo_organizacao()

        for empresa in Empresa.objects.all():
            with self.subTest(empresa=empresa.nome):
                filiais = Filial.objects.filter(empresa=empresa)
                self.assertGreater(filiais.count(), 0)
                self.assertTrue(Setor.objects.filter(filial__in=filiais).exists())

    def test_cria_perfis_de_demonstracao(self):
        seed_demo_organizacao()

        self.assertTrue(Perfil.objects.filter(nome="Administrador").exists())
        self.assertTrue(Perfil.objects.filter(nome="Médico").exists())
        self.assertGreaterEqual(Perfil.objects.count(), 6)

    def test_nao_altera_dados_existentes_ao_executar_de_novo(self):
        seed_demo_organizacao()
        antes = (Empresa.objects.count(), Filial.objects.count(), Setor.objects.count(), Perfil.objects.count())

        self.assertFalse(seed_demo_organizacao())

        depois = (Empresa.objects.count(), Filial.objects.count(), Setor.objects.count(), Perfil.objects.count())
        self.assertEqual(antes, depois)

    def test_comando_de_seed_inclui_a_estrutura_organizacional(self):
        call_command("seed_demo_domains")

        self.assertGreaterEqual(Empresa.objects.count(), 3)
        self.assertTrue(Perfil.objects.filter(nome="Administrador").exists())


class SeedUsuariosTest(TestCase):
    def setUp(self):
        seed_demo_organizacao()

    def test_senha_none_nao_cria_usuarios(self):
        self.assertEqual(seed_demo_usuarios(None), 0)
        self.assertFalse(Usuario.objects.filter(email__endswith="@demo.datagrapho.test").exists())

    def test_cria_tres_usuarios_por_empresa(self):
        criados = seed_demo_usuarios(SENHA_DEMO_USUARIOS)

        self.assertEqual(criados, 3 * Empresa.objects.count())
        for empresa in Empresa.objects.all():
            with self.subTest(empresa=empresa.nome):
                self.assertEqual(UsuarioAcesso.objects.filter(empresa=empresa).count(), 3)

    def test_administrador_e_staff_com_acesso_no_nivel_da_empresa(self):
        seed_demo_usuarios(SENHA_DEMO_USUARIOS)

        admin = Usuario.objects.get(email__startswith="admin.hospital-santa-clara@")
        self.assertTrue(admin.is_staff)
        self.assertFalse(admin.is_superuser)
        acesso = UsuarioAcesso.objects.get(usuario=admin)
        self.assertEqual(acesso.perfil.nome, "Administrador")
        self.assertIsNone(acesso.filial)

    def test_senha_definida_e_valida(self):
        seed_demo_usuarios(SENHA_DEMO_USUARIOS)

        usuario = Usuario.objects.get(email__startswith="gestor.hospital-santa-clara@")
        self.assertTrue(usuario.check_password(SENHA_DEMO_USUARIOS))
        self.assertFalse(usuario.check_password("outra"))

    def test_nao_duplica_ao_executar_de_novo(self):
        seed_demo_usuarios(SENHA_DEMO_USUARIOS)
        total = Usuario.objects.count()

        self.assertEqual(seed_demo_usuarios(SENHA_DEMO_USUARIOS), 0)
        self.assertEqual(Usuario.objects.count(), total)

    @override_settings(DEBUG=True)
    def test_comando_cria_usuarios_somente_com_debug_ligado(self):
        call_command("seed_demo_domains")

        self.assertTrue(Usuario.objects.filter(email__endswith="@demo.datagrapho.test").exists())

    @override_settings(DEBUG=False)
    def test_comando_nao_cria_usuarios_em_producao(self):
        call_command("seed_demo_domains")

        self.assertFalse(Usuario.objects.filter(email__endswith="@demo.datagrapho.test").exists())
        self.assertEqual(Empresa.objects.count(), 4)
