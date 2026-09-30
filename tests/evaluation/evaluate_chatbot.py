"""Evaluate live model tool choices and factual grounding on a fixed test catalog.

Run from the backend root with: python tests/evaluation/evaluate_chatbot.py
This script never changes the application's configured database.
"""

import argparse
import json
import logging
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.evaluation.sqlite_settings'

import django

django.setup()
logging.getLogger().setLevel(logging.ERROR)

from django.core.management import call_command  # noqa: E402
from chatbot.core.ai_providers.base import AIMessage  # noqa: E402
from chatbot.core.ai_providers.openai_provider import OpenAIProvider  # noqa: E402
from chatbot.core.engine import FunctionCallingEngine  # noqa: E402
from chatbot.core.tool_registry import ToolRegistry  # noqa: E402
from chatbot.domains.wine.repository import WineRepository  # noqa: E402
from chatbot.domains.wine.tools import register_wine_tools  # noqa: E402
from chatbot.models import (  # noqa: E402
    GrapeVariety, Wine, WineConsumption, WineCountry, WineGrape,
    WineOffer, WineProducer, WineRegion, WineReview,
)


@dataclass(frozen=True)
class Case:
    name: str
    question: str
    tools: frozenset[str]
    filters: dict = field(default_factory=dict)
    required_names: tuple[str, ...] = ()
    required_countries: tuple[str, ...] = ()
    required_prices: tuple[Decimal, ...] = ()
    no_results: bool = False
    history: tuple[AIMessage, ...] = ()


def normalize(value):
    text = unicodedata.normalize('NFKD', str(value or '')).casefold()
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).split())


def money_in(text):
    values = set()
    for match in re.finditer(r'R\$\s*([\d.]+,\d{2}|\d+\.\d{2})', text):
        raw = match.group(1)
        if ',' in raw:
            raw = raw.replace('.', '').replace(',', '.')
        values.add(Decimal(raw))
    return values


def seed_catalog():
    # Migrations seed demonstration rows. Remove them only from this in-memory DB.
    for model in (
        WineConsumption, WineReview, WineOffer, WineGrape, Wine,
        GrapeVariety, WineProducer, WineRegion, WineCountry,
    ):
        model.objects.all().delete()

    argentina = WineCountry.objects.create(name='Argentina', iso_code='AR')
    chile = WineCountry.objects.create(name='Chile', iso_code='CL')
    mendoza = WineRegion.objects.create(name='Mendoza', country=argentina)
    maipo = WineRegion.objects.create(name='Vale do Maipo', country=chile)
    andina = WineProducer.objects.create(name='Bodega Andina', region=mendoza)
    cordilheira = WineProducer.objects.create(name='Casa Cordilheira', region=mendoza)
    central = WineProducer.objects.create(name='Vinícola Central', region=maipo)
    malbec = GrapeVariety.objects.create(name='Malbec', color='tinta')
    cabernet = GrapeVariety.objects.create(name='Cabernet Sauvignon', color='tinta')

    rows = (
        ('Andes Malbec', andina, '89.90', ((malbec, '100.00'),)),
        ('Blend Andino', andina, '99.90', ((malbec, '60.00'), (cabernet, '40.00'))),
        ('Cordilheira Reserva', cordilheira, '129.90', ((malbec, '100.00'),)),
        ('Vale Cabernet', central, '79.90', ((cabernet, '100.00'),)),
    )
    for name, producer, price, grapes in rows:
        wine = Wine.objects.create(
            name=name, producer=producer, color='tinto', sweetness='seco',
            description=f'{name} é um vinho tinto seco de teste.', is_demo=True,
        )
        for grape, percentage in grapes:
            WineGrape.objects.create(wine=wine, grape=grape, percentage=percentage)
        WineOffer.objects.create(
            wine=wine, vintage_year=2024, price=price,
            stock=0 if name == 'Blend Andino' else 8,
        )


CASES = (
    Case(
        name='specific_wine',
        question='Quanto custa o Andes Malbec e de qual país ele é?',
        tools=frozenset({'get_wine_by_name', 'search_wine_catalog'}),
        required_names=('Andes Malbec',),
        required_countries=('Argentina',),
        required_prices=(Decimal('89.90'),),
    ),
    Case(
        name='country_and_price',
        question='Quais vinhos argentinos do catálogo custam menos de R$ 100?',
        tools=frozenset({'search_wine_catalog'}),
        filters={'country': 'Argentina', 'max_price': 100, 'in_stock': False},
        required_names=('Andes Malbec', 'Blend Andino'),
    ),
    Case(
        name='blend',
        question='Quais vinhos do catálogo usam mais de uma variedade de uva?',
        tools=frozenset({'search_wine_catalog'}),
        filters={'min_grape_varieties': 2},
        required_names=('Blend Andino',),
    ),
    Case(
        name='catalog_leader',
        question='Qual país tem mais vinhos cadastrados no catálogo?',
        tools=frozenset({'get_wine_database_summary'}),
        filters={'group_by': 'pais', 'source': 'catalogo'},
    ),
    Case(
        name='no_result',
        question='Existe algum vinho japonês no catálogo?',
        tools=frozenset({'search_wine_catalog'}),
        filters={'country': 'Japão'},
        no_results=True,
    ),
    Case(
        name='followup',
        question='E quanto custa ele?',
        tools=frozenset({'get_wine_by_name', 'search_wine_catalog'}),
        required_names=('Andes Malbec',),
        required_prices=(Decimal('89.90'),),
        history=(
            AIMessage(role='user', content='Estou interessado no Andes Malbec.'),
            AIMessage(role='assistant', content='O Andes Malbec é um vinho argentino de Mendoza.'),
        ),
    ),
)


class RecordingEngine(FunctionCallingEngine):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.executions = []

    def _execute_tool(self, tool_name, arguments_json, user_message=''):
        result = super()._execute_tool(tool_name, arguments_json, user_message)
        self.executions.append({
            'name': tool_name,
            'arguments': json.loads(arguments_json),
            'result': result,
        })
        return result


def actual_filters(execution):
    result = execution['result']
    if execution['name'] == 'search_wine_catalog':
        return result.get('filters', {})
    if execution['name'] == 'get_wine_database_summary':
        return {'group_by': result.get('group_by'), 'source': result.get('source')}
    return execution['arguments']


def check_facts(case, answer, executions, all_wines, all_countries):
    issues = []
    normalized_answer = normalize(answer)
    mentioned_wines = {
        name for name in all_wines if normalize(name) in normalized_answer
    }
    sourced_wines = {
        wine['nome']
        for execution in executions
        for wine in execution['result'].get('wines', [])
        if isinstance(wine, dict) and 'nome' in wine
    }
    unsupported_names = mentioned_wines - sourced_wines
    if unsupported_names:
        issues.append(f'vinhos citados sem retorno da ferramenta: {sorted(unsupported_names)}')

    mentioned_countries = {
        country for country in all_countries
        if normalize(country) in normalized_answer
    }
    sourced_countries = {
        wine['pais']
        for execution in executions
        for wine in execution['result'].get('wines', [])
        if isinstance(wine, dict) and wine.get('pais')
    }
    sourced_countries.update(
        group['grupo']
        for execution in executions
        if execution['result'].get('group_by') == 'pais'
        for group in execution['result'].get('groups', [])
    )
    unsupported_countries = mentioned_countries - sourced_countries
    if unsupported_countries:
        issues.append(
            f'países citados sem retorno da ferramenta: {sorted(unsupported_countries)}'
        )

    for required in case.required_names:
        if normalize(required) not in normalized_answer:
            issues.append(f'vinho esperado não identificado na resposta: {required}')
    for required in case.required_countries:
        if normalize(required) not in normalized_answer:
            issues.append(f'país esperado não identificado na resposta: {required}')

    prices = money_in(answer)
    sourced_prices = {
        Decimal(str(wine['preco']))
        for execution in executions
        for wine in execution['result'].get('wines', [])
        if isinstance(wine, dict) and wine.get('preco') is not None
    }
    threshold_prices = money_in(case.question)
    for price in prices - sourced_prices - threshold_prices:
        issues.append(f'preço sem suporte nos dados retornados: R$ {price}')
    for price in case.required_prices:
        if price not in prices:
            issues.append(f'preço esperado ausente: R$ {price}')
    if re.search(r'\bavaliad[oa]\s+em\s+R\$', answer, flags=re.IGNORECASE):
        issues.append('preço descrito como nota de avaliação')

    if case.name == 'catalog_leader':
        summaries = [
            execution['result'] for execution in executions
            if execution['name'] == 'get_wine_database_summary'
        ]
        if summaries and not any(
            normalize(leader) in normalized_answer
            for leader in summaries[-1].get('leaders', [])
        ):
            issues.append('líder do agrupamento não aparece na resposta')
        if summaries:
            allowed_counts = {
                summaries[-1].get('count'),
                summaries[-1].get('largest_count'),
                *(group['quantidade_vinhos'] for group in summaries[-1].get('groups', [])),
            }
            claimed_counts = {int(value) for value in re.findall(r'\b\d+\b', answer)}
            if claimed_counts - allowed_counts:
                issues.append(
                    f'contagens sem suporte no resumo: {sorted(claimed_counts - allowed_counts)}'
                )

    if case.no_results:
        no_result_signals = (
            'nao encontrei', 'nao ha', 'nenhum', 'nenhuma', 'sem resultados',
            'nao existem', 'nao existe', 'nao foi encontrado', 'nao foram encontrados',
        )
        if not any(signal in normalized_answer for signal in no_result_signals):
            issues.append('resposta não reconhece a ausência de resultados')
        if any(execution['result'].get('count', 0) for execution in executions):
            issues.append('consulta retornou registros quando não deveria')
    return issues


def evaluate(case, model, base_url, api_key, all_wines, all_countries):
    provider = OpenAIProvider(
        api_key=api_key, model=model, base_url=base_url,
        timeout=120, max_retries=1,
    )
    usage = []
    original_create = provider.client.chat.completions.create

    def measured_create(**kwargs):
        response = original_create(**kwargs)
        item = response.usage
        usage.append({
            'input': getattr(item, 'prompt_tokens', None),
            'output': getattr(item, 'completion_tokens', None),
        })
        return response

    provider.client.chat.completions.create = measured_create
    registry = ToolRegistry()
    register_wine_tools(registry)
    engine = RecordingEngine(
        ai_provider=provider, tool_registry=registry,
        repositories={'wine': WineRepository()},
    )
    result = engine.execute_query(case.question, list(case.history))
    executions = engine.executions
    issues = []
    matching = [item for item in executions if item['name'] in case.tools]
    tool_ok = bool(matching)
    filters_ok = True
    if not tool_ok:
        issues.append(f'ferramenta esperada não usada: {sorted(case.tools)}')
    elif case.filters:
        filters_ok = any(all(
            normalize(actual_filters(item).get(key)) == normalize(value)
            for key, value in case.filters.items()
        ) for item in matching)
        if not filters_ok:
            issues.append(f'filtros esperados não aplicados: {case.filters}')
    fact_issues = check_facts(
        case, result.response, executions, all_wines, all_countries
    )
    issues.extend(fact_issues)
    if result.error:
        issues.append(f'erro do fluxo: {result.error}')
    return {
        'case': case.name,
        'ok': not issues,
        'checks': {
            'tool': tool_ok,
            'filters': filters_ok if tool_ok else False,
            'facts': not fact_issues and not result.error,
        },
        'issues': issues,
        'question': case.question,
        'answer': result.response,
        'tool_calls': [
            {'name': item['name'], 'arguments': item['arguments'],
             'filters': actual_filters(item)}
            for item in executions
        ],
        'input_tokens': sum(item['input'] or 0 for item in usage),
        'output_tokens': sum(item['output'] or 0 for item in usage),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='qwen2.5-7b-instruct')
    parser.add_argument('--base-url', default='http://127.0.0.1:1234/v1')
    parser.add_argument(
        '--api-key-env', default='',
        help='Name of an environment variable containing the provider API key',
    )
    parser.add_argument('--case', choices=[case.name for case in CASES])
    args = parser.parse_args()
    api_key = os.getenv(args.api_key_env) if args.api_key_env else 'local-evaluation'
    if not api_key:
        parser.error(f'Environment variable {args.api_key_env} is empty or missing')

    call_command('migrate', verbosity=0)
    seed_catalog()
    all_wines = set(Wine.objects.values_list('name', flat=True))
    all_countries = set(WineCountry.objects.values_list('name', flat=True))
    selected = [case for case in CASES if not args.case or case.name == args.case]
    results = []
    for case in selected:
        report = evaluate(
            case, args.model, args.base_url, api_key, all_wines, all_countries
        )
        results.append(report)
        print(json.dumps(report, ensure_ascii=False), flush=True)

    print(json.dumps({
        'summary': {
            'passed': sum(item['ok'] for item in results),
            'total': len(results),
            'input_tokens': sum(item['input_tokens'] for item in results),
            'output_tokens': sum(item['output_tokens'] for item in results),
        }
    }, ensure_ascii=False), flush=True)
    return 0 if all(item['ok'] for item in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
