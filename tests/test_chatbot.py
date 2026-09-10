import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from chatbot.core.ai_providers.base import AIResponse
from chatbot.core.ai_providers.gemini_provider import GeminiProvider
from chatbot.core.engine import FunctionCallingEngine
from chatbot.core.tool_registry import ToolRegistry
from chatbot.domains.wine.repository import WineRepository
from chatbot.domains.wine.tools import (
    GetWineByNameTool,
    GetWineCatalogSummaryTool,
    SearchWineCatalogTool,
)
from chatbot.models import (
    ChatMessage,
    ChatSession,
    GrapeVariety,
    Wine,
    WineCountry,
    WineGrape,
    WineOffer,
    WineProducer,
    WineRegion,
    WineReview,
    WineConsumption,
)


class WineLookupTest(TestCase):
    def test_returns_country_and_price_from_database(self):
        country = WineCountry.objects.create(name='Argentina Teste', iso_code='XZ')
        region = WineRegion.objects.create(name='Mendoza Teste', country=country)
        producer = WineProducer.objects.create(name='Tikal Teste', region=region)
        wine = Wine.objects.create(
            name='Alma Negra Malbec Teste', producer=producer,
            color='tinto', sweetness='seco',
        )
        WineOffer.objects.create(
            wine=wine, vintage_year=2021, price='149.90', stock=1,
        )

        result = WineRepository().get_wine_by_name('Alma Negra Malbec Teste')

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["wines"][0]["pais"], "Argentina Teste")
        self.assertEqual(result["wines"][0]["preco"], 149.90)


class RelationalWineCatalogTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        country = WineCountry.objects.create(name='País Teste', iso_code='XT')
        region = WineRegion.objects.create(
            name='Região Teste', country=country, climate='Temperado'
        )
        producer = WineProducer.objects.create(name='Vinícola Teste', region=region)
        grape = GrapeVariety.objects.create(name='Uva Teste', color='tinta')
        cls.wine = Wine.objects.create(
            name='Reserva Relacional',
            producer=producer,
            color='tinto',
            sweetness='seco',
            alcohol_percentage='13.50',
            is_demo=True,
        )
        WineGrape.objects.create(wine=cls.wine, grape=grape, percentage='100.00')
        WineOffer.objects.create(
            wine=cls.wine, vintage_year=2024, price='79.90', stock=12
        )
        WineReview.objects.create(
            wine=cls.wine, reviewer='Teste automatizado', score='4.8'
        )
        WineConsumption.objects.create(
            consumed_at=date(2025, 1, 1), wine=cls.wine,
            unit_price='89.90', quantity=1,
        )
        cls.historical_wine = Wine.objects.create(
            name='Rótulo Somente Histórico', producer=producer,
            color='tinto', sweetness='seco', active=False,
        )
        WineGrape.objects.create(
            wine=cls.historical_wine, grape=grape, percentage='100.00'
        )
        WineConsumption.objects.create(
            consumed_at=date(2025, 2, 1), wine=cls.historical_wine,
            unit_price='49.90', quantity=1,
        )

    def test_search_crosses_country_grape_offer_and_review(self):
        result = WineRepository().search_wine_catalog(
            country='País Teste',
            grape='Uva Teste',
            sweetness='seco',
            max_price=100,
            min_rating=4.5,
        )

        self.assertEqual(result['count'], 1)
        wine = result['wines'][0]
        self.assertEqual(wine['nome'], 'Reserva Relacional')
        self.assertEqual(wine['regiao'], 'Região Teste')
        self.assertEqual(wine['uvas'][0]['nome'], 'Uva Teste')
        self.assertEqual(wine['preco'], 79.90)
        self.assertEqual(wine['preco_formatado'], 'R$ 79,90')
        self.assertEqual(wine['avaliacao_media'], 4.8)

    def test_search_filters_wines_with_multiple_grape_varieties(self):
        second_grape = GrapeVariety.objects.create(name='Segunda Uva Teste', color='tinta')
        WineGrape.objects.create(
            wine=self.wine, grape=second_grape, percentage='25.00'
        )

        result = WineRepository().search_wine_catalog(
            country='País Teste', min_grape_varieties=2
        )

        self.assertEqual(result['count'], 1)
        self.assertEqual(result['wines'][0]['nome'], 'Reserva Relacional')

    def test_search_includes_rating_exactly_on_decimal_boundary(self):
        result = WineRepository().search_wine_catalog(
            country='País Teste', min_rating=4.8
        )

        self.assertEqual(result['count'], 1)
        self.assertEqual(result['wines'][0]['avaliacao_media'], 4.8)

    def test_ai_interprets_multi_grape_question_and_chooses_database_tool(self):
        class MultiGrapeProvider:
            def __init__(self):
                self.calls = 0

            def chat_completion(self, messages, tools, temperature):
                self.calls += 1
                if self.calls == 1:
                    return AIResponse(tool_calls=[{
                        'id': 'multi-grape',
                        'name': 'search_wine_catalog',
                        'arguments': json.dumps({
                            'min_grape_varieties': 2,
                            'limit': 30,
                        }),
                    }])
                return AIResponse(content='Encontrei os blends consultando o catálogo.')

        registry = ToolRegistry()
        registry.register_tool(SearchWineCatalogTool())
        provider = MultiGrapeProvider()
        engine = FunctionCallingEngine(
            ai_provider=provider,
            tool_registry=registry,
            repositories={'wine': WineRepository()},
        )

        result = engine.execute_query('Quais vinhos utilizam mais de uma uva?')

        self.assertEqual(provider.calls, 2)
        self.assertEqual(result.tools_used, ['search_wine_catalog'])
        self.assertIn('blends', result.response)

    def test_summary_groups_wines_through_country_relation(self):
        result = WineRepository().get_catalog_summary('pais', 'catalogo')
        test_group = next(
            group for group in result['groups'] if group['grupo'] == 'País Teste'
        )

        self.assertEqual(test_group['quantidade_vinhos'], 1)
        self.assertEqual(test_group['preco_medio'], 79.90)

    def test_combined_summary_deduplicates_wine_names_and_identifies_source(self):
        result = WineRepository().get_catalog_summary('país', 'todos')
        test_group = next(
            group for group in result['groups'] if group['grupo'] == 'País Teste'
        )

        self.assertEqual(test_group['quantidade_vinhos'], 2)
        self.assertEqual(test_group['fontes'], ['catalogo', 'historico'])
        self.assertEqual(result['source'], 'todos')
        self.assertIn('nomes distintos', result['counting_rule'])

    def test_history_summary_counts_distinct_wines_not_consumption_rows(self):
        WineConsumption.objects.create(
            consumed_at=date(2025, 3, 1), wine=self.historical_wine, quantity=1,
        )

        result = WineRepository().get_catalog_summary('pais', 'historico')
        test_group = next(
            group for group in result['groups'] if group['grupo'] == 'País Teste'
        )

        self.assertEqual(test_group['quantidade_vinhos'], 2)

    def test_search_tool_has_optional_filters_for_local_models(self):
        schema = SearchWineCatalogTool().to_openai_format()

        self.assertEqual(schema['function']['parameters']['required'], [])

    def test_summary_tool_requires_group_but_defaults_source_to_all(self):
        schema = GetWineCatalogSummaryTool().to_openai_format()

        self.assertEqual(schema['function']['parameters']['required'], ['group_by'])


class FakeWineRepository:
    def get_wine_by_name(self, wine_name):
        return {
            "count": 1,
            "wines": [{"nome": wine_name, "pais": "Portugal", "preco": 89.90}],
        }


class FakeSummaryRepository:
    def __init__(self):
        self.sources = []

    def get_catalog_summary(self, group_by, source):
        self.sources.append(source)
        return {'group_by': group_by, 'source': source}


class FakeAIProvider:
    def __init__(self):
        self.calls = 0

    def chat_completion(self, messages, tools, temperature):
        self.calls += 1
        if self.calls == 1:
            return AIResponse(
                tool_calls=[
                    {
                        "id": "call-1",
                        "name": "get_wine_by_name",
                        "arguments": json.dumps({"wine_name": "Vinho X"}),
                    }
                ],
                finish_reason="tool_calls",
            )
        return AIResponse(
            content="O Vinho X e de Portugal e custa R$ 89,90.",
            finish_reason="stop",
        )


class FunctionCallingEngineTest(TestCase):
    def test_executes_database_tool_before_answering(self):
        registry = ToolRegistry()
        registry.register_tool(GetWineByNameTool())
        provider = FakeAIProvider()
        engine = FunctionCallingEngine(
            ai_provider=provider,
            tool_registry=registry,
            repositories={"wine": FakeWineRepository()},
        )

        result = engine.execute_query("Qual o pais e o valor do Vinho X?")

        self.assertEqual(provider.calls, 2)
        self.assertEqual(result.tools_used, ["get_wine_by_name"])
        self.assertIn("Portugal", result.response)

    def test_factual_wine_question_cannot_be_answered_without_tool(self):
        class HallucinatingProvider:
            def __init__(self):
                self.calls = 0

            def chat_completion(self, messages, tools, temperature):
                self.calls += 1
                return AIResponse(content='Existem 20 países.', finish_reason='stop')

        provider = HallucinatingProvider()
        engine = FunctionCallingEngine(
            ai_provider=provider,
            tool_registry=ToolRegistry(),
            repositories={'wine': FakeWineRepository()},
        )

        result = engine.execute_query('Quantos países existem na base de vinhos?')

        self.assertEqual(provider.calls, 2)
        self.assertEqual(result.error, 'DATABASE_TOOL_REQUIRED')
        self.assertNotIn('20', result.response)

    def test_summary_uses_source_selected_by_ai(self):
        registry = ToolRegistry()
        registry.register_tool(GetWineCatalogSummaryTool())
        repository = FakeSummaryRepository()
        engine = FunctionCallingEngine(
            ai_provider=FakeAIProvider(),
            tool_registry=registry,
            repositories={'wine': repository},
        )

        result = engine._execute_tool(
            'get_wine_database_summary',
            json.dumps({'group_by': 'pais', 'source': 'catalogo'}),
            user_message='Qual país possui mais vinhos cadastrados?',
        )

        self.assertEqual(result['source'], 'catalogo')

    def test_summary_defaults_to_all_and_accepts_explicit_source(self):
        registry = ToolRegistry()
        registry.register_tool(GetWineCatalogSummaryTool())
        repository = FakeSummaryRepository()
        engine = FunctionCallingEngine(
            ai_provider=FakeAIProvider(),
            tool_registry=registry,
            repositories={'wine': repository},
        )

        all_sources = engine._execute_tool(
            'get_wine_database_summary',
            json.dumps({'group_by': 'pais'}),
            user_message='Considerando somente o catálogo, qual país lidera?',
        )
        history = engine._execute_tool(
            'get_wine_database_summary',
            json.dumps({'group_by': 'pais', 'source': 'historico'}),
            user_message='No histórico de consumo, qual país lidera?',
        )

        self.assertEqual(all_sources['source'], 'todos')
        self.assertEqual(history['source'], 'historico')

    def test_search_arguments_selected_by_ai_are_validated(self):
        sanitized = FunctionCallingEngine._sanitize_wine_search_arguments(
            {
                'country': 'Brasil',
                'sweetness': 'Meio seco',
                'max_price': 200,
                'min_rating': 4.4,
                'in_stock': 'false',
                'limit': 1000000000000000,
                'unsupported': 'ignored',
            }
        )

        self.assertEqual(sanitized['country'], 'Brasil')
        self.assertEqual(sanitized['sweetness'], 'meio_seco')
        self.assertEqual(sanitized['max_price'], 200)
        self.assertEqual(sanitized['min_rating'], 4.4)
        self.assertFalse(sanitized['in_stock'])
        self.assertEqual(sanitized['limit'], 30)
        self.assertNotIn('unsupported', sanitized)

    def test_multi_grape_filter_selected_by_ai_is_preserved(self):
        sanitized = FunctionCallingEngine._sanitize_wine_search_arguments(
            {'min_grape_varieties': 2}
        )

        self.assertEqual(sanitized['min_grape_varieties'], 2)

    def test_false_negative_search_response_is_replaced_with_database_result(self):
        tool_result = {
            'count': 1,
            'wines': [{
                'nome': 'Vinho Teste', 'produtor': 'Produtor', 'regiao': 'Região',
                'pais': 'Brasil', 'uvas': [{'nome': 'Merlot', 'percentual': 100.0}],
                'safra': 2024, 'preco_formatado': 'R$ 50,00',
                'avaliacao_media': 4.5,
            }],
        }

        response = FunctionCallingEngine._guard_grounded_response(
            'Não foram encontrados vinhos.',
            [('search_wine_catalog', tool_result)],
        )

        self.assertIn('Vinho Teste', response)
        self.assertNotIn('Não foram encontrados', response)


class GeminiProviderContractTest(TestCase):
    def test_formats_tool_for_supported_google_sdk(self):
        provider = GeminiProvider(api_key="x" * 30)
        formatted = provider.format_tool_definitions(
            [GetWineByNameTool().to_openai_format()]
        )

        declaration = formatted[0].function_declarations[0]
        self.assertEqual(declaration.name, "get_wine_by_name")


class ChatSessionApiTest(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="chat@datagrapho.test",
            cpf="111.222.333-44",
            nome="Chat User",
            password="strong-password",
        )
        self.other_user = user_model.objects.create_user(
            email="other@datagrapho.test",
            cpf="555.666.777-88",
            nome="Other User",
            password="strong-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_rename_search_and_retrieve_history(self):
        create_response = self.client.post(
            "/api/chatbot/sessions/", {"title": "Pesquisa de vinhos"}, format="json"
        )
        self.assertEqual(create_response.status_code, 201)
        session_id = create_response.data["id"]

        rename_response = self.client.patch(
            f"/api/chatbot/sessions/{session_id}/",
            {"title": "Vinhos argentinos"},
            format="json",
        )
        self.assertEqual(rename_response.status_code, 200)
        self.assertEqual(rename_response.data["title"], "Vinhos argentinos")

        session = ChatSession.objects.get(session_id=session_id)
        ChatMessage.objects.create(session=session, role="user", content="Qual o preco?")
        ChatMessage.objects.create(session=session, role="assistant", content="R$ 149,90")

        search_response = self.client.get("/api/chatbot/sessions/?search=argentinos")
        self.assertEqual(len(search_response.data), 1)

        detail_response = self.client.get(f"/api/chatbot/sessions/{session_id}/")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(len(detail_response.data["messages"]), 2)
        self.assertEqual(detail_response.data["messages"][0]["role"], "user")

    def test_cannot_read_another_users_session(self):
        session = ChatSession.objects.create(user=self.other_user, title="Privado")

        response = self.client.get(f"/api/chatbot/sessions/{session.session_id}/")

        self.assertEqual(response.status_code, 404)
