from django.core.management import call_command
from django.test import TestCase

from catalogo_depara.models import CatalogoDePara
from depara.models import DePara
from depara.seed import seed_demo_depara


class SeedDeParaTest(TestCase):
    def test_cria_tres_catalogos_com_seus_mapeamentos(self):
        seed_demo_depara()

        self.assertEqual(CatalogoDePara.objects.count(), 3)
        self.assertEqual(DePara.objects.count(), 14)
        self.assertTrue(
            DePara.objects.filter(
                id_catalogo__tabela_origem="produtos.unidade", codigo_origem="CX", codigo_destino="CAIXA"
            ).exists()
        )

    def test_mapeamento_filho_aponta_para_o_pai(self):
        seed_demo_depara()

        filho = DePara.objects.get(codigo_origem="EXA-LAB")
        self.assertIsNotNone(filho.id_depara_pai)
        self.assertEqual(filho.id_depara_pai.codigo_origem, "EXA")

    def test_nao_altera_dados_existentes_ao_executar_de_novo(self):
        seed_demo_depara()
        antes = (CatalogoDePara.objects.count(), DePara.objects.count())

        self.assertFalse(seed_demo_depara())

        self.assertEqual(antes, (CatalogoDePara.objects.count(), DePara.objects.count()))

    def test_comando_de_seed_inclui_o_de_para(self):
        call_command("seed_demo_domains")

        self.assertEqual(CatalogoDePara.objects.count(), 3)
