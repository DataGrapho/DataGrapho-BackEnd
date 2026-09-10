"""Atalhos para os modelos do domínio de vinhos.

Os modelos Django ficam em ``chatbot.models`` para que migrations e runtime
tenham uma única fonte de verdade.
"""

from chatbot.models import (
    GrapeVariety,
    Wine,
    WineCountry,
    WineGrape,
    WineOffer,
    WineProducer,
    WineRegion,
    WineReview,
    WineConsumption,
)

__all__ = [
    'WineCountry',
    'WineRegion',
    'WineProducer',
    'GrapeVariety',
    'Wine',
    'WineGrape',
    'WineOffer',
    'WineReview',
    'WineConsumption',
]
