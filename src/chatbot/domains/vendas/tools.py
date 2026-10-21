"""Ferramentas do domínio de vendas e pedidos."""

from datetime import date
from typing import Any, Dict

from chatbot.core.base_tool import Tool


def _parse_date(value: Any, parameter: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f'{parameter} deve estar no formato AAAA-MM-DD') from exc


class GetVendasPeriodoTool(Tool):
    def __init__(self):
        super().__init__(
            name='get_vendas_periodo',
            description=(
                'Resumir vendas em um período (datas AAAA-MM-DD): faturamento, ticket médio, '
                'pedidos por status e principais vendedores. Considera pedidos pagos.'
            ),
            parameters={'data_inicio': 'date', 'data_fim': 'date'},
            required_parameters=['data_inicio', 'data_fim'],
            domain='vendas',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        inicio = _parse_date(params.get('data_inicio'), 'data_inicio')
        fim = _parse_date(params.get('data_fim'), 'data_fim')
        if inicio > fim:
            raise ValueError('data_inicio não pode ser posterior a data_fim')
        return repository.get_sales_by_period(inicio, fim)


class GetVendasTopProdutosTool(Tool):
    def __init__(self):
        super().__init__(
            name='get_vendas_top_produtos',
            description=(
                'Ranking dos produtos mais vendidos por receita, com quantidade vendida. '
                'Período (datas AAAA-MM-DD) é opcional; sem ele considera todo o histórico.'
            ),
            parameters={'limit': 'integer', 'data_inicio': 'date', 'data_fim': 'date'},
            required_parameters=[],
            domain='vendas',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        try:
            limit = max(1, min(int(params.get('limit', 5)), 20))
        except (TypeError, ValueError):
            limit = 5

        inicio_raw, fim_raw = params.get('data_inicio'), params.get('data_fim')
        inicio = fim = None
        if inicio_raw or fim_raw:
            if not (inicio_raw and fim_raw):
                raise ValueError('informe data_inicio e data_fim juntos')
            inicio = _parse_date(inicio_raw, 'data_inicio')
            fim = _parse_date(fim_raw, 'data_fim')
            if inicio > fim:
                raise ValueError('data_inicio não pode ser posterior a data_fim')
        return repository.get_top_products(limit, inicio, fim)


class GetVendasPorClienteTool(Tool):
    def __init__(self):
        super().__init__(
            name='get_vendas_por_cliente',
            description=(
                'Buscar um cliente pelo nome e mostrar pedidos, total pago e últimos pedidos.'
            ),
            parameters={'nome': 'string'},
            required_parameters=['nome'],
            domain='vendas',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        nome = str(params.get('nome', '')).strip()
        if not nome:
            raise ValueError('nome é obrigatório')
        return repository.get_orders_by_customer(nome)


def register_vendas_tools(registry):
    """Registra as ferramentas do domínio de vendas e pedidos."""
    registry.register_tool(GetVendasPeriodoTool())
    registry.register_tool(GetVendasTopProdutosTool())
    registry.register_tool(GetVendasPorClienteTool())
