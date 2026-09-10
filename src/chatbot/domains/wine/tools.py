from typing import Dict, Any
from datetime import datetime
from dateutil.relativedelta import relativedelta

from chatbot.core.base_tool import Tool


class GetWineByNameTool(Tool):
    """Busca pais, regiao, safra, produtor e preco de um vinho pelo nome."""

    def __init__(self):
        super().__init__(
            name='get_wine_by_name',
            description=(
                'Buscar um vinho pelo nome na base de dados. Use para responder perguntas '
                'sobre pais de origem, regiao, produtor, safra ou preco de um vinho especifico.'
            ),
            parameters={'wine_name': 'string'},
            domain='wine',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        wine_name = str(params.get('wine_name', '')).strip()
        if not wine_name:
            raise ValueError('wine_name parameter is required')
        return repository.get_wine_by_name(wine_name)


class SearchWineCatalogTool(Tool):
    """Pesquisa relacional flexível para descoberta e recomendação de vinhos."""

    def __init__(self):
        super().__init__(
            name='search_wine_catalog',
            description=(
                'Pesquisar e recomendar vinhos cruzando catalogo, produtor, regiao, pais, '
                'uvas, preco, estoque e avaliacao. Use min_grape_varieties=2 para vinhos '
                'com mais de uma uva. Todos os filtros sao opcionais.'
            ),
            parameters={
                'query': 'string',
                'country': 'string',
                'region': 'string',
                'producer': 'string',
                'grape': 'string',
                'color': 'string',
                'sweetness': 'string',
                'max_price': 'float',
                'min_rating': 'float',
                'min_grape_varieties': 'integer',
                'in_stock': 'boolean',
                'limit': 'integer',
            },
            required_parameters=[],
            domain='wine',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        return repository.search_wine_catalog(
            query=str(params.get('query', '') or '').strip(),
            country=str(params.get('country', '') or '').strip(),
            region=str(params.get('region', '') or '').strip(),
            producer=str(params.get('producer', '') or '').strip(),
            grape=str(params.get('grape', '') or '').strip(),
            color=str(params.get('color', '') or '').strip(),
            sweetness=str(params.get('sweetness', '') or '').strip(),
            max_price=params.get('max_price'),
            min_rating=params.get('min_rating'),
            min_grape_varieties=params.get('min_grape_varieties'),
            in_stock=params.get('in_stock', False),
            limit=params.get('limit', 10),
        )


class GetWineCatalogSummaryTool(Tool):
    """Agrupa o catálogo por uma dimensão relacionada."""

    def __init__(self):
        super().__init__(
            name='get_wine_database_summary',
            description=(
                'Resumir vinhos por pais, regiao, produtor, uva, cor ou tipo. A fonte pode '
                'ser catalogo, historico ou todos. A fonte final sera determinada pelo backend '
                'a partir da pergunta: perguntas genericas sempre usam todos. Quando o usuario '
                'pedir todos os grupos ou perguntar "quais", use result_mode="list". Para top N '
                'ou ranking, use result_mode="ranking" e informe N em limit. Para apenas o maior '
                'grupo, use result_mode="leader". Retorna todos os grupos para representar '
                'empates corretamente.'
            ),
            parameters={
                'group_by': 'string', 'source': 'string',
                'result_mode': 'string', 'limit': 'integer',
            },
            required_parameters=['group_by'],
            domain='wine',
        )

    def execute(self, repository, **params) -> Dict[str, Any]:
        group_by = str(params.get('group_by', '') or '').strip()
        if not group_by:
            raise ValueError('group_by parameter is required')
        source = str(params.get('source', 'todos') or 'todos').strip()
        result = dict(repository.get_catalog_summary(group_by, source))
        result_mode = str(params.get('result_mode', '') or '').strip().casefold()
        if result_mode in {'leader', 'list', 'ranking'}:
            result['result_mode'] = result_mode
        requested_limit = params.get('limit')
        if requested_limit not in (None, ''):
            result['requested_limit'] = max(1, int(requested_limit))
        return result


class GetConsumoByPeriodTool(Tool):
    """Ferramenta para obter consumo de vinhos por período"""
    
    def __init__(self):
        super().__init__(
            name='get_consumo_by_period',
            description='Obter consumos de vinho para um período específico. Use datas no formato YYYY-MM-DD.',
            parameters={
                'start_date': 'date',
                'end_date': 'date'
            },
            domain='wine',
        )
    
    def execute(self, repository, **params) -> Dict[str, Any]:
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        return repository.get_consumo_by_period(start_date, end_date)


class GetConsumoByCountryTool(Tool):
    """Ferramenta para obter consumo de vinhos agrupados por país"""
    
    def __init__(self):
        super().__init__(
            name='get_consumo_by_country',
            description='Obter consumos de vinho agrupados por país para um período. Use formato de período como "2024-01" para janeiro de 2024, "Q1-2024" para primeiro trimestre, ou "2024" para o ano inteiro.',
            parameters={
                'period': 'string'
            },
            domain='wine',
        )
    
    def execute(self, repository, **params) -> Dict[str, Any]:
        period = params.get('period')
        start_date, end_date = self._parse_period(period)
        return repository.get_consumo_by_country(start_date, end_date)
    
    def _parse_period(self, period: str):
        from datetime import date
        
        # Ano completo: "2024"
        if len(period) == 4 and period.isdigit():
            year = int(period)
            return date(year, 1, 1), date(year, 12, 31)
        
        # Mês específico: "2024-01"
        if len(period) == 7 and period[4] == '-':
            year, month = map(int, period.split('-'))
            start_date = date(year, month, 1)
            end_date = start_date + relativedelta(months=1, days=-1)
            return start_date, end_date
        
        # Trimestre: "Q1-2024"
        if period.startswith('Q') and '-' in period:
            quarter_str, year_str = period.split('-')
            quarter = int(quarter_str[1])
            year = int(year_str)
            
            quarter_months = {
                1: (1, 3),
                2: (4, 6),
                3: (7, 9),
                4: (10, 12)
            }
            
            start_month, end_month = quarter_months[quarter]
            start_date = date(year, start_month, 1)
            end_date = date(year, end_month, 1) + relativedelta(months=1, days=-1)
            return start_date, end_date
        
        raise ValueError(f"Invalid period format: {period}. Use YYYY, YYYY-MM, or QX-YYYY")


class GetTopWinesTool(Tool):
    """Ferramenta para obter os vinhos mais consumidos"""
    
    def __init__(self):
        super().__init__(
            name='get_top_wines',
            description=(
                'Obter o ranking de vinhos por total de unidades consumidas. '
                'A resposta diferencia unidades de eventos, identifica dados demonstrativos '
                'e inclui todos os vinhos empatados na posição de corte. '
                'O limite padrão é 10, máximo é 100.'
            ),
            parameters={
                'limit': 'integer'
            },
            domain='wine',
        )
    
    def execute(self, repository, **params) -> Dict[str, Any]:
        limit = params.get('limit', 10)
        
        if limit < 1:
            limit = 10
        if limit > 100:
            limit = 100
        
        return repository.get_top_wines(limit)


class GetWinesByOpinionTool(Tool):
    """Ferramenta para obter vinhos por opinião"""
    
    def __init__(self):
        super().__init__(
            name='get_wines_by_opinion',
            description='Obter vinhos filtrados por opinião. Exemplos: "Ótimo", "Muito Bom", "Bom", "Excelente".',
            parameters={
                'opinion': 'string'
            },
            domain='wine',
        )
    
    def execute(self, repository, **params) -> Dict[str, Any]:
        opinion = params.get('opinion')
        
        if not opinion:
            raise ValueError("opinion parameter is required")
        
        return repository.get_wines_by_opinion(opinion)


class ComparePeriodsTool(Tool):
    """Ferramenta para comparar consumo de vinhos entre períodos"""
    
    def __init__(self):
        super().__init__(
            name='compare_periods',
            description='Comparar consumo de vinhos entre dois períodos. Use datas no formato YYYY-MM-DD.',
            parameters={
                'period1_start': 'date',
                'period1_end': 'date',
                'period2_start': 'date',
                'period2_end': 'date'
            },
            domain='wine',
        )
    
    def execute(self, repository, **params) -> Dict[str, Any]:
        period1_start = params.get('period1_start')
        period1_end = params.get('period1_end')
        period2_start = params.get('period2_start')
        period2_end = params.get('period2_end')
        
        if isinstance(period1_start, str):
            period1_start = datetime.strptime(period1_start, '%Y-%m-%d').date()
        if isinstance(period1_end, str):
            period1_end = datetime.strptime(period1_end, '%Y-%m-%d').date()
        if isinstance(period2_start, str):
            period2_start = datetime.strptime(period2_start, '%Y-%m-%d').date()
        if isinstance(period2_end, str):
            period2_end = datetime.strptime(period2_end, '%Y-%m-%d').date()
        
        return repository.compare_periods(
            period1_start, period1_end,
            period2_start, period2_end
        )


def register_wine_tools(registry):
    """Registrar todas as ferramentas relacionadas a vinhos"""
    registry.register_tool(GetWineByNameTool())
    registry.register_tool(SearchWineCatalogTool())
    registry.register_tool(GetWineCatalogSummaryTool())
    registry.register_tool(GetConsumoByPeriodTool())
    registry.register_tool(GetConsumoByCountryTool())
    registry.register_tool(GetTopWinesTool())
    registry.register_tool(GetWinesByOpinionTool())
    registry.register_tool(ComparePeriodsTool())
