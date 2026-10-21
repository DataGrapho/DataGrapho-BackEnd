import json
import random
from datetime import date, timedelta

from django.test import TestCase

from chatbot.core.engine import FunctionCallingEngine
from chatbot.core.tool_registry import ToolRegistry
from chatbot.domains.convenio.repository import ConvenioRepository
from chatbot.domains.convenio.seed import seed_demo_data as seed_convenio
from chatbot.domains.convenio.tools import register_convenio_tools
from chatbot.domains.estoque.repository import EstoqueRepository
from chatbot.domains.estoque.seed import seed_demo_data as seed_estoque
from chatbot.domains.estoque.tools import register_estoque_tools
from chatbot.domains.vendas.repository import VendasRepository
from chatbot.domains.vendas.seed import seed_demo_data as seed_vendas
from chatbot.domains.vendas.tools import register_vendas_tools


REGISTER_FUNCTIONS = {
    'convenio': register_convenio_tools,
    'vendas': register_vendas_tools,
    'estoque': register_estoque_tools,
}


class DemoDomainsRegistrationTest(TestCase):
    def test_tools_register_and_produce_valid_provider_definitions(self):
        registry = ToolRegistry()
        for register in REGISTER_FUNCTIONS.values():
            register(registry)

        tools = registry.get_all_tools()
        self.assertEqual(len(tools), 10)
        self.assertEqual({tool.domain for tool in tools}, set(REGISTER_FUNCTIONS))

        for provider in ('gemini', 'openai', 'anthropic'):
            definitions = registry.get_tool_definitions_for_ai(provider)
            self.assertEqual(len(definitions), 10)

    def test_duplicate_registration_is_rejected(self):
        registry = ToolRegistry()
        register_estoque_tools(registry)
        with self.assertRaises(ValueError):
            register_estoque_tools(registry)


class DemoDomainsDataTest(TestCase):
    def setUp(self):
        self.today = date.today()
        rng = random.Random(42)
        seed_convenio(rng, self.today)
        seed_vendas(random.Random(42), self.today)
        seed_estoque(random.Random(42), self.today)

    def test_seed_is_idempotent(self):
        self.assertFalse(seed_convenio(random.Random(1), self.today))
        self.assertFalse(seed_vendas(random.Random(1), self.today))
        self.assertFalse(seed_estoque(random.Random(1), self.today))

    def test_convenio_queries(self):
        repository = ConvenioRepository()

        beneficiario = repository.get_beneficiario_by_name('Mariana')
        self.assertEqual(beneficiario['count'], 1)
        self.assertIn('plano', beneficiario['beneficiarios'][0])

        atendimentos = repository.get_atendimentos_by_period(
            self.today - timedelta(days=200), self.today
        )
        self.assertGreater(atendimentos['total_atendimentos'], 0)
        self.assertEqual(
            sum(atendimentos['por_status'].values()), atendimentos['total_atendimentos']
        )

        ranking = repository.get_top_especialidades(3)
        self.assertEqual(len(ranking['especialidades']), 3)
        self.assertEqual(len(repository.get_planos_overview()['planos']), 4)

    def test_vendas_queries(self):
        repository = VendasRepository()

        summary = repository.get_sales_by_period(self.today - timedelta(days=200), self.today)
        self.assertGreater(summary['pedidos_pagos'], 0)
        self.assertGreater(summary['faturamento'], 0)

        products = repository.get_top_products(5)
        receitas = [item['receita'] for item in products['produtos']]
        self.assertEqual(receitas, sorted(receitas, reverse=True))

        customer = repository.get_orders_by_customer('Alfa')
        self.assertEqual(customer['count'], 1)

    def test_estoque_low_stock_matches_demo_scenario(self):
        repository = EstoqueRepository()

        low = repository.get_low_stock(10)
        skus = {item['sku'] for item in low['produtos']}
        self.assertEqual(skus, {'SKU-1002', 'SKU-1005', 'SKU-1007'})

        stock = repository.get_stock_by_product('SKU-1002')
        self.assertEqual(stock['produtos'][0]['situacao'], 'abaixo_do_minimo')
        self.assertEqual(stock['produtos'][0]['total_em_estoque'], 7)

        movements = repository.get_movements_by_period(
            self.today - timedelta(days=90), self.today
        )
        self.assertGreater(movements['total_movimentacoes'], 0)


class DemoDomainsEngineTest(TestCase):
    """Executa as ferramentas pelo mesmo caminho que a IA usa (FunctionCallingEngine)."""

    def setUp(self):
        today = date.today()
        seed_convenio(random.Random(42), today)
        seed_vendas(random.Random(42), today)
        seed_estoque(random.Random(42), today)

        registry = ToolRegistry()
        for register in REGISTER_FUNCTIONS.values():
            register(registry)
        self.engine = FunctionCallingEngine(
            ai_provider=object(),
            tool_registry=registry,
            repositories={
                'convenio': ConvenioRepository(),
                'vendas': VendasRepository(),
                'estoque': EstoqueRepository(),
            },
        )

    def test_tools_execute_and_return_json_serializable_results(self):
        arguments = [
            ('get_convenio_beneficiario', {'nome': 'Carlos'}),
            ('get_convenio_planos', {}),
            ('get_convenio_top_especialidades', {'limit': 2}),
            ('get_vendas_periodo', {'data_inicio': '2026-01-01', 'data_fim': '2026-12-31'}),
            ('get_vendas_top_produtos', {'limit': 3}),
            ('get_vendas_por_cliente', {'nome': 'Mercado'}),
            ('get_estoque_produto', {'termo': 'SKU-1001'}),
            ('get_estoque_abaixo_minimo', {'limit': 5}),
            ('get_estoque_movimentacoes', {'data_inicio': '2026-01-01', 'data_fim': '2026-12-31', 'tipo': 'saida'}),
        ]
        for name, params in arguments:
            with self.subTest(tool=name):
                result = self.engine._execute_tool(name, json.dumps(params))
                json.dumps(result)

    def test_invalid_date_is_reported_as_tool_error(self):
        with self.assertRaises(ValueError):
            self.engine._execute_tool(
                'get_vendas_periodo', json.dumps({'data_inicio': '21/10/2026', 'data_fim': '2026-10-21'})
            )

    def test_invalid_movement_type_is_rejected(self):
        with self.assertRaises(ValueError):
            self.engine._execute_tool(
                'get_estoque_movimentacoes',
                json.dumps({'data_inicio': '2026-01-01', 'data_fim': '2026-12-31', 'tipo': 'venda'}),
            )
