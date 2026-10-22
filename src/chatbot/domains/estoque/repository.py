"""Consultas do domínio de estoque de produtos.

Todas as respostas usam apenas tipos serializáveis em JSON.
"""

from datetime import date
from typing import Any, Dict, Optional

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce

from chatbot.domains.estoque.models import EstoqueMovimentacao, EstoqueProduto


class EstoqueRepository:
    """Consultas sobre produtos, saldos por depósito e movimentações."""

    def get_stock_by_product(self, termo: str) -> Dict[str, Any]:
        queryset = (
            EstoqueProduto.objects.filter(Q(nome__icontains=termo) | Q(sku__iexact=termo))
            .annotate(total=Coalesce(Sum('saldos__quantidade'), 0))
            .order_by('nome')
        )

        produtos = []
        for produto in queryset[:5]:
            produtos.append({
                'sku': produto.sku,
                'produto': produto.nome,
                'categoria': produto.categoria,
                'unidade': produto.unidade,
                'estoque_minimo': produto.estoque_minimo,
                'total_em_estoque': produto.total,
                'situacao': (
                    'abaixo_do_minimo' if produto.total < produto.estoque_minimo else 'ok'
                ),
                'por_deposito': [
                    {'deposito': saldo.deposito.nome, 'quantidade': saldo.quantidade}
                    for saldo in produto.saldos.select_related('deposito').order_by(
                        'deposito__nome'
                    )
                ],
            })

        return {
            'count': queryset.count(),
            'produtos': produtos,
            'answer_guidance': (
                'Informe o total em estoque, o saldo por depósito e se está abaixo do mínimo.'
            ),
        }

    def get_low_stock(self, limit: int = 10) -> Dict[str, Any]:
        queryset = (
            EstoqueProduto.objects.annotate(total=Coalesce(Sum('saldos__quantidade'), 0))
            .filter(total__lt=F('estoque_minimo'))
            .order_by('total', 'nome')
        )
        return {
            'count': queryset.count(),
            'produtos': [
                {
                    'sku': produto.sku,
                    'produto': produto.nome,
                    'total_em_estoque': produto.total,
                    'estoque_minimo': produto.estoque_minimo,
                    'faltam': produto.estoque_minimo - produto.total,
                }
                for produto in queryset[:limit]
            ],
            'answer_guidance': (
                'Produtos cujo total em estoque está abaixo do mínimo configurado.'
            ),
        }

    def get_movements_by_period(
        self, data_inicio: date, data_fim: date, tipo: Optional[str] = None
    ) -> Dict[str, Any]:
        queryset = EstoqueMovimentacao.objects.filter(data__range=(data_inicio, data_fim))
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        totais = queryset.aggregate(
            entradas=Sum('quantidade', filter=Q(tipo='entrada')),
            saidas=Sum('quantidade', filter=Q(tipo='saida')),
        )
        por_produto = (
            queryset.values('produto__nome')
            .annotate(unidades=Sum('quantidade'), movimentacoes=Count('pk'))
            .order_by('-quantidade', 'produto__nome')[:5]
        )
        return {
            'periodo': {'inicio': data_inicio.isoformat(), 'fim': data_fim.isoformat()},
            'total_movimentacoes': queryset.count(),
            'unidades_entrada': totais['entradas'] or 0,
            'unidades_saida': totais['saidas'] or 0,
            'top_produtos_movimentados': [
                {
                    'produto': row['produto__nome'],
                    'unidades': row['unidades'],
                    'movimentacoes': row['movimentacoes'],
                }
                for row in por_produto
            ],
            'answer_guidance': 'Quantidades em unidades, sem conversão monetária.',
        }
