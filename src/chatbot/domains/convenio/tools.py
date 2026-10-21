"""Ferramentas do domínio de convênio médico."""

from datetime import date
from typing import Any, Dict

from chatbot.core.base_tool import Tool


TIPOS_ATENDIMENTO = {'consulta', 'exame', 'terapia', 'internacao'}


def _parse_date(value: Any, parameter: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f'{parameter} deve estar no formato AAAA-MM-DD') from exc


class GetConvenioBeneficiarioTool(Tool):
    def __init__(self):
        super().__init__(
            name='get_convenio_beneficiario',
            description=(
                'Buscar um beneficiário de convênio médico pelo nome. Use para responder '
                'sobre plano, operadora, data de adesão, atendimentos e valor autorizado.'
            ),
            parameters={'nome': 'string'},
            required_parameters=['nome'],
            domain='convenio',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        nome = str(params.get('nome', '')).strip()
        if not nome:
            raise ValueError('nome é obrigatório')
        return repository.get_beneficiario_by_name(nome)


class GetConvenioAtendimentosTool(Tool):
    def __init__(self):
        super().__init__(
            name='get_convenio_atendimentos',
            description=(
                'Resumir atendimentos de convênio médico em um período (datas AAAA-MM-DD), '
                'com total, status, valor autorizado e tipo. Filtro de tipo é opcional.'
            ),
            parameters={'data_inicio': 'date', 'data_fim': 'date', 'tipo': 'string'},
            required_parameters=['data_inicio', 'data_fim'],
            domain='convenio',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        inicio = _parse_date(params.get('data_inicio'), 'data_inicio')
        fim = _parse_date(params.get('data_fim'), 'data_fim')
        if inicio > fim:
            raise ValueError('data_inicio não pode ser posterior a data_fim')
        tipo = str(params.get('tipo', '') or '').strip().lower() or None
        if tipo and tipo not in TIPOS_ATENDIMENTO:
            raise ValueError(f'tipo deve ser um de: {sorted(TIPOS_ATENDIMENTO)}')
        return repository.get_atendimentos_by_period(inicio, fim, tipo)


class GetConvenioTopEspecialidadesTool(Tool):
    def __init__(self):
        super().__init__(
            name='get_convenio_top_especialidades',
            description=(
                'Ranking das especialidades com mais atendimentos de convênio médico, '
                'com quantidade e valor autorizado.'
            ),
            parameters={'limit': 'integer'},
            required_parameters=[],
            domain='convenio',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        try:
            limit = max(1, min(int(params.get('limit', 5)), 20))
        except (TypeError, ValueError):
            limit = 5
        return repository.get_top_especialidades(limit)


class GetConvenioPlanosTool(Tool):
    def __init__(self):
        super().__init__(
            name='get_convenio_planos',
            description=(
                'Listar os planos de convênio médico ativos, com operadora, tipo, '
                'mensalidade e número de beneficiários ativos.'
            ),
            parameters={},
            required_parameters=[],
            domain='convenio',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        return repository.get_planos_overview()


def register_convenio_tools(registry):
    """Registra as ferramentas do domínio de convênio médico."""
    registry.register_tool(GetConvenioBeneficiarioTool())
    registry.register_tool(GetConvenioAtendimentosTool())
    registry.register_tool(GetConvenioTopEspecialidadesTool())
    registry.register_tool(GetConvenioPlanosTool())
