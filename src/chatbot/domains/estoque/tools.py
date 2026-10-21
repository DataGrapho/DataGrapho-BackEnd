"""Ferramentas do domínio de estoque de produtos."""

from datetime import date
from typing import Any, Dict

from chatbot.core.base_tool import Tool


TIPOS_MOVIMENTACAO = {'entrada', 'saida'}


def _parse_date(value: Any, parameter: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f'{parameter} deve estar no formato AAAA-MM-DD') from exc


class GetEstoqueProdutoTool(Tool):
    def __init__(self):
        super().__init__(
            name='get_estoque_produto',
            description=(
                'Consultar o estoque de um produto pelo nome ou SKU: total, saldo por depósito '
                'e se está abaixo do estoque mínimo.'
            ),
            parameters={'termo': 'string'},
            required_parameters=['termo'],
            domain='estoque',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        termo = str(params.get('termo', '')).strip()
        if not termo:
            raise ValueError('termo é obrigatório')
        return repository.get_stock_by_product(termo)


class GetEstoqueAbaixoMinimoTool(Tool):
    def __init__(self):
        super().__init__(
            name='get_estoque_abaixo_minimo',
            description=(
                'Listar produtos com estoque total abaixo do mínimo configurado, '
                'do mais crítico para o menos crítico.'
            ),
            parameters={'limit': 'integer'},
            required_parameters=[],
            domain='estoque',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        try:
            limit = max(1, min(int(params.get('limit', 10)), 50))
        except (TypeError, ValueError):
            limit = 10
        return repository.get_low_stock(limit)


class GetEstoqueMovimentacoesTool(Tool):
    def __init__(self):
        super().__init__(
            name='get_estoque_movimentacoes',
            description=(
                'Resumir entradas e saídas de estoque em um período (datas AAAA-MM-DD), '
                'com os produtos mais movimentados. Filtro de tipo é opcional.'
            ),
            parameters={'data_inicio': 'date', 'data_fim': 'date', 'tipo': 'string'},
            required_parameters=['data_inicio', 'data_fim'],
            domain='estoque',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        inicio = _parse_date(params.get('data_inicio'), 'data_inicio')
        fim = _parse_date(params.get('data_fim'), 'data_fim')
        if inicio > fim:
            raise ValueError('data_inicio não pode ser posterior a data_fim')
        tipo = str(params.get('tipo', '') or '').strip().lower() or None
        if tipo and tipo not in TIPOS_MOVIMENTACAO:
            raise ValueError(f'tipo deve ser um de: {sorted(TIPOS_MOVIMENTACAO)}')
        return repository.get_movements_by_period(inicio, fim, tipo)


def register_estoque_tools(registry):
    """Registra as ferramentas do domínio de estoque de produtos."""
    registry.register_tool(GetEstoqueProdutoTool())
    registry.register_tool(GetEstoqueAbaixoMinimoTool())
    registry.register_tool(GetEstoqueMovimentacoesTool())
