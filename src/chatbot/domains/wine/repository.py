import time
import logging
from typing import Dict, Any, List
from decimal import Decimal
from datetime import date

from django.db.models import Sum, Count, Avg, Q
from django.core.cache import cache
from django.conf import settings

from chatbot.models import FatoConsumoVinho


logger = logging.getLogger(__name__)


class WineRepository:
    """Repository para consultas relacionadas a consumo de vinhos"""
    
    def __init__(self):
        self.cache_ttl = settings.CHATBOT_CONFIG.get('CACHE_TTL', 300)
    
    def get_consumo_by_period(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Obter consumos de vinho por período"""
        start_time = time.time()
        
        cache_key = f'wine_consumo_{start_date}_{end_date}'
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Cache HIT: get_consumo_by_period({start_date}, {end_date})")
            return cached_result
        
        logger.info(f"Cache MISS: get_consumo_by_period({start_date}, {end_date})")
        
        consumos = FatoConsumoVinho.objects.filter(
            data_consumo__gte=start_date,
            data_consumo__lte=end_date
        ).order_by('-data_consumo')
        
        total_qtd = consumos.aggregate(total=Sum('qtd'))['total'] or 0
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
                    'data': c.data_consumo.isoformat(),
                    'vinho': c.vinho,
                    'uva': c.uva,
                    'safra': c.safra,
                    'produtor': c.produtor,
                    'cor': c.cor,
                    'pais': c.pais,
                    'regiao': c.regiao,
                    'opiniao': c.opiniao,
                    'preco': float(c.preco) if c.preco else None,
                    'quantidade': c.qtd,
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
        
        consumos_by_country = FatoConsumoVinho.objects.filter(
            data_consumo__gte=start_date,
            data_consumo__lte=end_date,
            pais__isnull=False
        ).values('pais').annotate(
            total_qtd=Sum('qtd'),
            total_valor=Sum('total'),
            count=Count('id_fato_consumo'),
            preco_medio=Avg('preco')
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
                    'pais': item['pais'],
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
        """Obter os vinhos mais consumidos"""
        limit = max(1, min(limit, 100))
        
        cache_key = f'top_wines_{limit}'
        
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        top_wines = FatoConsumoVinho.objects.values('vinho', 'produtor', 'pais').annotate(
            total_consumo=Sum('qtd'),
            total_valor=Sum('total'),
            preco_medio=Avg('preco'),
            count=Count('id_fato_consumo')
        ).order_by('-total_consumo')[:limit]
        
        result = {
            'count': len(top_wines),
            'wines': [
                {
                    'vinho': wine['vinho'],
                    'produtor': wine['produtor'],
                    'pais': wine['pais'],
                    'total_consumo': wine['total_consumo'],
                    'valor_total': float(wine['total_valor']) if wine['total_valor'] else 0,
                    'preco_medio': float(wine['preco_medio']) if wine['preco_medio'] else 0,
                    'vezes_consumido': wine['count'],
                    'currency': 'BRL'
                }
                for wine in top_wines
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
        
        wines = FatoConsumoVinho.objects.filter(
            opiniao__icontains=opinion
        ).values('vinho', 'produtor', 'pais', 'opiniao', 'preco', 'data_consumo').annotate(
            total_consumo=Sum('qtd')
        ).order_by('-data_consumo')[:50]
        
        result = {
            'opinion_filter': opinion,
            'count': len(wines),
            'wines': [
                {
                    'vinho': wine['vinho'],
                    'produtor': wine['produtor'],
                    'pais': wine['pais'],
                    'opiniao': wine['opiniao'],
                    'preco': float(wine['preco']) if wine['preco'] else None,
                    'data_consumo': wine['data_consumo'].isoformat(),
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
