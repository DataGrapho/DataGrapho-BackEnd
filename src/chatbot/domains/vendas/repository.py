"""Consultas do domínio de vendas e pedidos.

Todas as respostas usam apenas tipos serializáveis em JSON.
"""

from datetime import date
from typing import Any, Dict, Optional

from django.db.models import Count, DecimalField, F, Sum

from chatbot.domains.vendas.models import VendasCliente, VendasItemPedido, VendasPedido


STATUS_PAGO = 'pago'

_REVENUE_FIELD = DecimalField(max_digits=14, decimal_places=2)


def _money(value) -> float:
    return float(value or 0)


def _revenue(prefix: str = '') -> Sum:
    """Soma quantidade * preco_unitario dos itens; use prefix='itens__' a partir de pedidos."""
    return Sum(
        F(f'{prefix}quantidade') * F(f'{prefix}preco_unitario'),
        output_field=_REVENUE_FIELD,
    )


class VendasRepository:
    """Consultas sobre pedidos, produtos e clientes."""

    def get_sales_by_period(self, data_inicio: date, data_fim: date) -> Dict[str, Any]:
        pedidos = VendasPedido.objects.filter(data__range=(data_inicio, data_fim))
        pagos = pedidos.filter(status=STATUS_PAGO)

        faturamento = _money(
            VendasItemPedido.objects.filter(pedido__in=pagos).aggregate(total=_revenue())['total']
        )
        total_pagos = pagos.count()

        return {
            'periodo': {'inicio': data_inicio.isoformat(), 'fim': data_fim.isoformat()},
            'total_pedidos': pedidos.count(),
            'pedidos_pagos': total_pagos,
            'faturamento': faturamento,
            'ticket_medio': round(faturamento / total_pagos, 2) if total_pagos else 0.0,
            'por_status': {
                row['status']: row['quantidade']
                for row in pedidos.values('status').annotate(quantidade=Count('pk'))
            },
            'top_vendedores': [
                {'vendedor': row['vendedor'], 'pedidos_pagos': row['pedidos']}
                for row in pagos.values('vendedor')
                .annotate(pedidos=Count('pk'))
                .order_by('-pedidos', 'vendedor')[:5]
            ],
            'answer_guidance': (
                'Faturamento e ticket médio em R$, considerando apenas pedidos pagos.'
            ),
        }

    def get_top_products(
        self,
        limit: int = 5,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> Dict[str, Any]:
        itens = VendasItemPedido.objects.filter(pedido__status=STATUS_PAGO)
        if data_inicio and data_fim:
            itens = itens.filter(pedido__data__range=(data_inicio, data_fim))

        rows = (
            itens.values('produto__nome', 'produto__categoria')
            .annotate(unidades=Sum('quantidade'), receita=_revenue())
            .order_by('-receita', 'produto__nome')[:limit]
        )
        return {
            'produtos': [
                {
                    'produto': row['produto__nome'],
                    'categoria': row['produto__categoria'],
                    'quantidade_vendida': row['unidades'],
                    'receita': _money(row['receita']),
                }
                for row in rows
            ],
            'answer_guidance': (
                'Ranking por receita, considerando apenas pedidos pagos; valores em R$.'
            ),
        }

    def get_orders_by_customer(self, nome: str) -> Dict[str, Any]:
        clientes = VendasCliente.objects.filter(nome__icontains=nome).order_by('nome')

        resultados = []
        for cliente in clientes[:5]:
            pedidos = cliente.pedidos.annotate(total=_revenue('itens__')).order_by('-data')
            pagos_total = VendasItemPedido.objects.filter(
                pedido__cliente=cliente, pedido__status=STATUS_PAGO
            ).aggregate(total=_revenue())['total']
            resultados.append({
                'cliente': cliente.nome,
                'cidade': f'{cliente.cidade}/{cliente.uf}',
                'cliente_desde': cliente.desde.isoformat(),
                'total_pedidos': pedidos.count(),
                'total_pago': _money(pagos_total),
                'ultimos_pedidos': [
                    {
                        'data': pedido.data.isoformat(),
                        'status': pedido.get_status_display(),
                        'vendedor': pedido.vendedor,
                        'total': _money(pedido.total),
                    }
                    for pedido in pedidos[:5]
                ],
            })

        return {
            'count': clientes.count(),
            'clientes': resultados,
            'answer_guidance': 'Valores em R$.',
        }
