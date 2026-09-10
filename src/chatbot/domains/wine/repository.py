import time
import logging
import hashlib
import unicodedata
from typing import Dict, Any, List
from decimal import Decimal
from datetime import date

from django.db.models import Sum, Count, Avg, Q, Prefetch
from django.core.cache import cache
from django.conf import settings

from chatbot.models import Wine, WineConsumption, WineGrape, WineOffer


logger = logging.getLogger(__name__)


class WineRepository:
    """Repository para consultas relacionadas a consumo de vinhos"""
    
    def __init__(self):
        self.cache_ttl = settings.CHATBOT_CONFIG.get('CACHE_TTL', 300)

    def get_wine_by_name(self, wine_name: str) -> Dict[str, Any]:
        """Busca vinhos pelo nome e retorna apenas dados persistidos no banco."""
        normalized_name = wine_name.strip()
        if not normalized_name:
            raise ValueError("wine_name is required")

        name_hash = hashlib.sha256(normalized_name.casefold().encode("utf-8")).hexdigest()
        cache_key = f"wine_by_name_{name_hash}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        catalog_result = self.search_wine_catalog(query=normalized_name, limit=10)
        if catalog_result['count']:
            result = {
                'query': normalized_name,
                'count': catalog_result['count'],
                'wines': catalog_result['wines'],
                'source': 'relational_catalog',
            }
            cache.set(cache_key, result, self.cache_ttl)
            return result

        result = {"query": normalized_name, "count": 0, "wines": []}
        cache.set(cache_key, result, self.cache_ttl)
        return result

    def search_wine_catalog(
        self,
        query: str = '',
        country: str = '',
        region: str = '',
        producer: str = '',
        grape: str = '',
        color: str = '',
        sweetness: str = '',
        max_price: float = None,
        min_rating: float = None,
        min_grape_varieties: int = None,
        in_stock: bool = False,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Pesquisa o catálogo usando relações entre vinho, origem, uvas e ofertas."""
        limit = max(1, min(int(limit or 10), 30))
        queryset = (
            Wine.objects.filter(active=True)
            .select_related('producer__region__country')
            .prefetch_related(
                Prefetch(
                    'grape_links',
                    queryset=WineGrape.objects.select_related('grape').order_by('-percentage'),
                ),
                Prefetch(
                    'offers',
                    queryset=WineOffer.objects.filter(active=True).order_by('price'),
                    to_attr='active_offers',
                ),
            )
            .annotate(
                average_rating=Avg('reviews__score'),
                grape_variety_count=Count('grapes', distinct=True),
            )
        )

        query = str(query or '').strip()
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(producer__name__icontains=query)
                | Q(producer__region__name__icontains=query)
                | Q(producer__region__country__name__icontains=query)
                | Q(grapes__name__icontains=query)
            )
        if country:
            queryset = queryset.filter(producer__region__country__name__icontains=country)
        if region:
            queryset = queryset.filter(producer__region__name__icontains=region)
        if producer:
            queryset = queryset.filter(producer__name__icontains=producer)
        if grape:
            queryset = queryset.filter(grapes__name__icontains=grape)
        if color:
            queryset = queryset.filter(color__iexact=self._normalize_style(color))
        if sweetness:
            queryset = queryset.filter(sweetness__iexact=self._normalize_style(sweetness))
        if max_price not in (None, ''):
            queryset = queryset.filter(
                offers__active=True,
                offers__price__lte=Decimal(str(max_price)),
            )
        if min_rating not in (None, ''):
            queryset = queryset.filter(average_rating__gte=Decimal(str(min_rating)))
        if min_grape_varieties not in (None, ''):
            queryset = queryset.filter(grape_variety_count__gte=min_grape_varieties)
        if self._as_bool(in_stock):
            queryset = queryset.filter(offers__active=True, offers__stock__gt=0)

        wines = list(queryset.distinct().order_by('-average_rating', 'name')[:limit])
        return {
            'filters': {
                'query': query,
                'country': country,
                'region': region,
                'producer': producer,
                'grape': grape,
                'color': color,
                'sweetness': sweetness,
                'max_price': max_price,
                'min_rating': min_rating,
                'min_grape_varieties': min_grape_varieties,
                'in_stock': self._as_bool(in_stock),
            },
            'count': len(wines),
            'wines': [self._serialize_catalog_wine(wine) for wine in wines],
            'notice': 'Registros com dado_demonstrativo=true usam valores fictícios de teste.',
        }

    def get_catalog_summary(self, group_by: str, source: str = 'todos') -> Dict[str, Any]:
        """Agrupa catálogo e/ou histórico, deduplicando vinhos dentro de cada grupo."""
        group_aliases = {
            'pais': 'pais', 'country': 'pais',
            'regiao': 'regiao', 'region': 'regiao',
            'produtor': 'produtor', 'producer': 'produtor',
            'uva': 'uva', 'grape': 'uva',
            'cor': 'cor', 'color': 'cor',
            'tipo': 'tipo', 'sweetness': 'tipo',
        }
        source_aliases = {
            'catalogo': 'catalogo', 'catalog': 'catalogo',
            'historico': 'historico', 'history': 'historico',
            'todos': 'todos', 'all': 'todos',
        }
        dimension = group_aliases.get(self._normalize_style(group_by))
        normalized_source = source_aliases.get(self._normalize_style(source or 'todos'))
        if not dimension:
            raise ValueError('group_by must be pais, regiao, produtor, uva, cor or tipo')
        if not normalized_source:
            raise ValueError('source must be catalogo, historico or todos')

        buckets = {}

        def add_wine(group_value, wine_name, price, rating, item_source):
            if not group_value or not wine_name:
                return
            group_key = self._normalize_style(group_value)
            wine_key = self._normalize_text(wine_name)
            bucket = buckets.setdefault(
                group_key,
                {'grupo': str(group_value), 'wines': {}},
            )
            # O catálogo estruturado tem precedência quando o vinho existe nas duas fontes.
            if wine_key in bucket['wines'] and item_source == 'historico':
                return
            bucket['wines'][wine_key] = {
                'preco': float(price) if price is not None else None,
                'avaliacao': float(rating) if rating is not None else None,
                'fonte': item_source,
            }

        if normalized_source in {'catalogo', 'todos'}:
            catalog_wines = (
                Wine.objects.filter(active=True)
                .select_related('producer__region__country')
                .prefetch_related(
                    Prefetch(
                        'grape_links',
                        queryset=WineGrape.objects.select_related('grape'),
                    ),
                    Prefetch(
                        'offers',
                        queryset=WineOffer.objects.filter(active=True).order_by('price'),
                        to_attr='active_offers',
                    ),
                )
                .annotate(average_rating=Avg('reviews__score'))
            )
            for wine in catalog_wines:
                group_values = {
                    'pais': [wine.producer.region.country.name],
                    'regiao': [wine.producer.region.name],
                    'produtor': [wine.producer.name],
                    'uva': [link.grape.name for link in wine.grape_links.all()],
                    'cor': [wine.get_color_display()],
                    'tipo': [wine.get_sweetness_display()],
                }[dimension]
                best_offer = wine.active_offers[0] if wine.active_offers else None
                for group_value in group_values:
                    add_wine(
                        group_value,
                        wine.name,
                        best_offer.price if best_offer else None,
                        wine.average_rating,
                        'catalogo',
                    )

        if normalized_source in {'historico', 'todos'}:
            history_wines = (
                Wine.objects.filter(consumptions__isnull=False)
                .select_related('producer__region__country')
                .prefetch_related('grape_links__grape')
                .annotate(
                    average_rating=Avg('reviews__score'),
                    historical_price=Avg('consumptions__unit_price'),
                )
                .distinct()
            )
            for wine in history_wines:
                group_values = {
                    'pais': [wine.producer.region.country.name],
                    'regiao': [wine.producer.region.name],
                    'produtor': [wine.producer.name],
                    'uva': [link.grape.name for link in wine.grape_links.all()],
                    'cor': [wine.get_color_display()],
                    'tipo': [wine.get_sweetness_display()],
                }[dimension]
                for group_value in group_values:
                    add_wine(
                        group_value,
                        wine.name,
                        wine.historical_price,
                        wine.average_rating,
                        'historico',
                    )

        groups = []
        for bucket in buckets.values():
            records = list(bucket['wines'].values())
            prices = [item['preco'] for item in records if item['preco'] is not None]
            ratings = [
                item['avaliacao'] for item in records if item['avaliacao'] is not None
            ]
            groups.append({
                'grupo': bucket['grupo'],
                'quantidade_vinhos': len(records),
                'preco_medio': round(sum(prices) / len(prices), 2) if prices else None,
                'avaliacao_media': (
                    round(sum(ratings) / len(ratings), 2) if ratings else None
                ),
                'vinhos_com_preco': len(prices),
                'vinhos_com_avaliacao': len(ratings),
                'moeda': 'BRL',
                'fontes': sorted({item['fonte'] for item in records}),
            })
        groups.sort(key=lambda item: (-item['quantidade_vinhos'], item['grupo'].casefold()))
        largest_count = groups[0]['quantidade_vinhos'] if groups else 0
        leaders = [
            item['grupo'] for item in groups
            if item['quantidade_vinhos'] == largest_count
        ]

        descriptions = {
            'catalogo': 'Somente o catálogo relacional de produtos.',
            'historico': 'Somente os vinhos distintos do histórico de consumo.',
            'todos': (
                'Catálogo relacional e histórico de consumo combinados, com vinhos '
                'de mesmo nome contados uma única vez por grupo.'
            ),
        }
        guidance = {
            'catalogo': (
                'Informe que a resposta considera somente o catálogo relacional de produtos.'
            ),
            'historico': (
                'Informe que a resposta considera somente o histórico de consumo.'
            ),
            'todos': (
                'Informe obrigatoriamente que a resposta combina o catálogo relacional e o '
                'histórico de consumo. Não descreva o resultado como sendo somente do catálogo.'
            ),
        }
        return {
            'group_by': dimension,
            'source': normalized_source,
            'source_description': descriptions[normalized_source],
            'answer_guidance': guidance[normalized_source],
            'counting_rule': 'Quantidade de nomes distintos de vinho por grupo.',
            'averages_rule': (
                'Preço e avaliação médios usam somente vinhos que possuem o respectivo dado; '
                'consulte vinhos_com_preco e vinhos_com_avaliacao antes de interpretar a média.'
            ),
            'count': len(groups),
            'largest_count': largest_count,
            'leaders': leaders,
            'has_tie': len(leaders) > 1,
            'groups': groups,
        }

    @staticmethod
    def _normalize_style(value: str) -> str:
        normalized = unicodedata.normalize('NFKD', str(value or ''))
        normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
        return normalized.strip().casefold().replace('-', '_').replace(' ', '_')

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = unicodedata.normalize('NFKD', str(value or ''))
        normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
        return ' '.join(normalized.casefold().split())

    @staticmethod
    def _as_bool(value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().casefold() not in {'false', '0', 'nao', 'não', ''}
        return bool(value)

    @staticmethod
    def _serialize_catalog_wine(wine: Wine) -> Dict[str, Any]:
        offers = getattr(wine, 'active_offers', [])
        best_offer = offers[0] if offers else None
        return {
            'nome': wine.name,
            'produtor': wine.producer.name,
            'pais': wine.producer.region.country.name,
            'regiao': wine.producer.region.name,
            'clima_regiao': wine.producer.region.climate or None,
            'cor': wine.get_color_display(),
            'tipo': wine.get_sweetness_display(),
            'teor_alcoolico': (
                float(wine.alcohol_percentage)
                if wine.alcohol_percentage is not None else None
            ),
            'uvas': [
                {
                    'nome': link.grape.name,
                    'percentual': float(link.percentage) if link.percentage is not None else None,
                }
                for link in wine.grape_links.all()
            ],
            'safra': best_offer.vintage_year if best_offer else None,
            'preco': float(best_offer.price) if best_offer else None,
            'preco_formatado': (
                f'R$ {best_offer.price:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
                if best_offer else None
            ),
            'moeda': best_offer.currency if best_offer else None,
            'estoque': best_offer.stock if best_offer else 0,
            'avaliacao_media': (
                round(float(wine.average_rating), 2)
                if wine.average_rating is not None else None
            ),
            'descricao': wine.description,
            'dado_demonstrativo': wine.is_demo,
        }
    
    def get_consumo_by_period(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Obter consumos de vinho por período"""
        start_time = time.time()
        
        cache_key = f'wine_consumo_{start_date}_{end_date}'
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Cache HIT: get_consumo_by_period({start_date}, {end_date})")
            return cached_result
        
        logger.info(f"Cache MISS: get_consumo_by_period({start_date}, {end_date})")
        
        consumos = WineConsumption.objects.filter(
            consumed_at__gte=start_date,
            consumed_at__lte=end_date,
        ).select_related(
            'wine__producer__region__country'
        ).prefetch_related('wine__grape_links__grape').order_by('-consumed_at')
        
        total_qtd = consumos.aggregate(total=Sum('quantity'))['total'] or 0
        total_valor = consumos.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        
        result = {
            'total_quantidade': total_qtd,
            'total_valor': float(total_valor),
            'currency': 'BRL',
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'count': consumos.count(),
            'records': [
                {
                    'data': c.consumed_at.isoformat(),
                    'vinho': c.wine.name,
                    'uva': ', '.join(link.grape.name for link in c.wine.grape_links.all()),
                    'safra': c.vintage_year,
                    'produtor': c.wine.producer.name,
                    'cor': c.wine.get_color_display(),
                    'pais': c.wine.producer.region.country.name,
                    'regiao': c.wine.producer.region.name,
                    'opiniao': c.opinion,
                    'preco': float(c.unit_price) if c.unit_price else None,
                    'quantidade': c.quantity,
                    'total': float(c.total) if c.total else None,
                }
                for c in consumos[:50]
            ]
        }
        
        cache.set(cache_key, result, self.cache_ttl)
        
        execution_time = time.time() - start_time
        logger.info(f"Query executed: get_consumo_by_period in {execution_time:.3f}s")
        
        return result
    
    def get_consumo_by_country(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Obter consumos agrupados por país"""
        cache_key = f'wine_by_country_{start_date}_{end_date}'
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        consumos_by_country = WineConsumption.objects.filter(
            consumed_at__gte=start_date,
            consumed_at__lte=end_date,
        ).values(
            'wine__producer__region__country__name'
        ).annotate(
            total_qtd=Sum('quantity'),
            total_valor=Sum('total'),
            count=Count('id'),
            preco_medio=Avg('unit_price'),
        ).order_by('-total_qtd')
        
        grand_total = sum(item['total_qtd'] for item in consumos_by_country)
        
        result = {
            'total_quantidade': grand_total,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'countries': [
                {
                    'pais': item['wine__producer__region__country__name'],
                    'quantidade': item['total_qtd'],
                    'valor_total': float(item['total_valor']) if item['total_valor'] else 0,
                    'count': item['count'],
                    'preco_medio': float(item['preco_medio']) if item['preco_medio'] else 0,
                    'percentage': round((item['total_qtd'] / grand_total * 100), 2) if grand_total > 0 else 0
                }
                for item in consumos_by_country
            ]
        }
        
        cache.set(cache_key, result, self.cache_ttl)
        
        return result
    
    def get_top_wines(self, limit: int = 10) -> Dict[str, Any]:
        """Obter os vinhos mais consumidos, preservando empates no corte."""
        limit = max(1, min(limit, 100))
        
        cache_key = f'top_wines_{limit}'
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        top_wines = WineConsumption.objects.values(
            'wine_id',
            'wine__name',
            'wine__producer__name',
            'wine__producer__region__country__name',
            'wine__is_demo',
        ).annotate(
            total_consumo=Sum('quantity'),
            total_valor=Sum('total'),
            preco_medio=Avg('unit_price'),
            count=Count('id'),
        ).order_by('-total_consumo', 'wine__name', 'wine_id')

        ranked_wines = list(top_wines)
        selected_wines = ranked_wines[:limit]
        cutoff_units = (
            selected_wines[-1]['total_consumo'] if selected_wines else None
        )
        if cutoff_units is not None:
            selected_wines = [
                wine for wine in ranked_wines
                if wine['total_consumo'] >= cutoff_units
            ]

        tie_at_cutoff = len(selected_wines) > min(limit, len(ranked_wines))
        
        result = {
            'count': len(selected_wines),
            'requested_limit': limit,
            'returned_count': len(selected_wines),
            'total_ranked_wines': len(ranked_wines),
            'ranking_metric': 'total_units_consumed',
            'cutoff_units': cutoff_units,
            'tie_at_cutoff': tie_at_cutoff,
            'note': (
                'O ranking soma as unidades consumidas. vezes_consumido representa '
                'a quantidade de eventos de consumo. Todos os empatados no corte são retornados.'
            ),
            'wines': [
                {
                    'vinho': wine['wine__name'],
                    'produtor': wine['wine__producer__name'],
                    'pais': wine['wine__producer__region__country__name'],
                    'total_consumo': wine['total_consumo'],
                    'valor_total': float(wine['total_valor']) if wine['total_valor'] else 0,
                    'preco_medio': float(wine['preco_medio']) if wine['preco_medio'] else 0,
                    'vezes_consumido': wine['count'],
                    'is_demo': wine['wine__is_demo'],
                    'currency': 'BRL'
                }
                for wine in selected_wines
            ]
        }
        
        cache.set(cache_key, result, self.cache_ttl)
        
        return result
    
    def get_wines_by_opinion(self, opinion: str) -> Dict[str, Any]:
        """Obter vinhos filtrados por opinião"""
        cache_key = f'wines_opinion_{opinion}'
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        wines = WineConsumption.objects.filter(
            opinion__icontains=opinion
        ).values(
            'wine__name',
            'wine__producer__name',
            'wine__producer__region__country__name',
            'opinion', 'unit_price', 'consumed_at',
        ).annotate(
            total_consumo=Sum('quantity')
        ).order_by('-consumed_at')[:50]
        
        result = {
            'opinion_filter': opinion,
            'count': len(wines),
            'wines': [
                {
                    'vinho': wine['wine__name'],
                    'produtor': wine['wine__producer__name'],
                    'pais': wine['wine__producer__region__country__name'],
                    'opiniao': wine['opinion'],
                    'preco': float(wine['unit_price']) if wine['unit_price'] else None,
                    'data_consumo': wine['consumed_at'].isoformat(),
                    'total_consumo': wine['total_consumo']
                }
                for wine in wines
            ]
        }
        
        cache.set(cache_key, result, self.cache_ttl)
        
        return result
    
    def compare_periods(
        self,
        period1_start: date,
        period1_end: date,
        period2_start: date,
        period2_end: date
    ) -> Dict[str, Any]:
        """Comparar consumo de vinhos entre dois períodos"""
        period1_data = self.get_consumo_by_period(period1_start, period1_end)
        period2_data = self.get_consumo_by_period(period2_start, period2_end)
        
        period1_qtd = period1_data['total_quantidade']
        period2_qtd = period2_data['total_quantidade']
        
        difference = period2_qtd - period1_qtd
        
        if period1_qtd > 0:
            percentage_change = (difference / period1_qtd) * 100
        else:
            percentage_change = 0 if period2_qtd == 0 else 100
        
        result = {
            'metric': 'consumo_vinho',
            'period1': {
                'start': period1_start.isoformat(),
                'end': period1_end.isoformat(),
                'quantidade': period1_qtd,
                'valor': period1_data['total_valor']
            },
            'period2': {
                'start': period2_start.isoformat(),
                'end': period2_end.isoformat(),
                'quantidade': period2_qtd,
                'valor': period2_data['total_valor']
            },
            'comparison': {
                'difference_qtd': difference,
                'percentage_change': round(percentage_change, 2),
                'trend': 'increase' if difference > 0 else 'decrease' if difference < 0 else 'stable'
            }
        }
        
        return result
