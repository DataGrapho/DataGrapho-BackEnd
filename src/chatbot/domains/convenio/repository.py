"""Consultas do domínio de convênio médico.

Todas as respostas usam apenas tipos serializáveis em JSON.
"""

from datetime import date
from typing import Any, Dict, Optional

from django.db.models import Count, Q, Sum

from chatbot.domains.convenio.models import (
    ConvenioAtendimento,
    ConvenioBeneficiario,
    ConvenioPlano,
)


STATUS_AUTORIZADO = 'autorizado'


def _money(value) -> float:
    return float(value or 0)


class ConvenioRepository:
    """Consultas sobre beneficiários, planos e atendimentos."""

    def get_beneficiario_by_name(self, nome: str) -> Dict[str, Any]:
        queryset = ConvenioBeneficiario.objects.select_related('plano').filter(
            nome__icontains=nome
        ).order_by('nome')

        beneficiarios = []
        for beneficiario in queryset[:5]:
            atendimentos = beneficiario.atendimentos.all()
            beneficiarios.append({
                'nome': beneficiario.nome,
                'plano': beneficiario.plano.nome,
                'operadora': beneficiario.plano.operadora,
                'tipo_plano': beneficiario.plano.get_tipo_display(),
                'mensalidade': _money(beneficiario.plano.mensalidade),
                'data_adesao': beneficiario.data_adesao.isoformat(),
                'ativo': beneficiario.ativo,
                'total_atendimentos': atendimentos.count(),
                'valor_autorizado': _money(
                    atendimentos.filter(status=STATUS_AUTORIZADO).aggregate(
                        total=Sum('valor')
                    )['total']
                ),
            })

        return {
            'count': queryset.count(),
            'beneficiarios': beneficiarios,
            'answer_guidance': (
                'Informe nome do beneficiário, plano, operadora e valores em R$.'
            ),
        }

    def get_atendimentos_by_period(
        self, data_inicio: date, data_fim: date, tipo: Optional[str] = None
    ) -> Dict[str, Any]:
        queryset = ConvenioAtendimento.objects.filter(data__range=(data_inicio, data_fim))
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        por_status = {
            row['status']: row['quantidade']
            for row in queryset.values('status').annotate(quantidade=Count('pk'))
        }
        por_tipo = [
            {
                'tipo': row['tipo'],
                'quantidade': row['quantidade'],
                'valor_autorizado': _money(row['valor_autorizado']),
            }
            for row in queryset.values('tipo')
            .annotate(
                quantidade=Count('pk'),
                valor_autorizado=Sum('valor', filter=Q(status=STATUS_AUTORIZADO)),
            )
            .order_by('tipo')
        ]

        return {
            'periodo': {'inicio': data_inicio.isoformat(), 'fim': data_fim.isoformat()},
            'total_atendimentos': queryset.count(),
            'por_status': por_status,
            'valor_autorizado': _money(
                queryset.filter(status=STATUS_AUTORIZADO).aggregate(total=Sum('valor'))['total']
            ),
            'por_tipo': por_tipo,
            'answer_guidance': (
                'Informe o período consultado, o total de atendimentos e o valor autorizado em R$.'
            ),
        }

    def get_top_especialidades(self, limit: int = 5) -> Dict[str, Any]:
        rows = (
            ConvenioAtendimento.objects.values('especialidade')
            .annotate(
                atendimentos=Count('pk'),
                valor_autorizado=Sum('valor', filter=Q(status=STATUS_AUTORIZADO)),
            )
            .order_by('-atendimentos', 'especialidade')[:limit]
        )
        return {
            'especialidades': [
                {
                    'especialidade': row['especialidade'],
                    'atendimentos': row['atendimentos'],
                    'valor_autorizado': _money(row['valor_autorizado']),
                }
                for row in rows
            ],
            'answer_guidance': (
                'Ranking por quantidade de atendimentos; empates devem ser informados.'
            ),
        }

    def get_planos_overview(self) -> Dict[str, Any]:
        planos = (
            ConvenioPlano.objects.filter(ativo=True)
            .annotate(beneficiarios_ativos=Count('beneficiarios', filter=Q(beneficiarios__ativo=True)))
            .order_by('nome')
        )
        return {
            'planos': [
                {
                    'nome': plano.nome,
                    'operadora': plano.operadora,
                    'tipo': plano.get_tipo_display(),
                    'mensalidade': _money(plano.mensalidade),
                    'beneficiarios_ativos': plano.beneficiarios_ativos,
                }
                for plano in planos
            ],
            'answer_guidance': 'Valores de mensalidade em R$.',
        }
