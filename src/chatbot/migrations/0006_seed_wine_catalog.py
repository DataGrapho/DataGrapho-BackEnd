from decimal import Decimal

from django.db import migrations


COUNTRIES = [
    ('Argentina', 'AR'),
    ('Brasil', 'BR'),
    ('Chile', 'CL'),
    ('França', 'FR'),
    ('Itália', 'IT'),
    ('Portugal', 'PT'),
]

REGIONS = [
    ('Mendoza', 'Argentina', 'Continental e seco'),
    ('Serra Gaúcha', 'Brasil', 'Subtropical de altitude'),
    ('Valle del Maipo', 'Chile', 'Mediterrâneo'),
    ('Bordeaux', 'França', 'Oceânico temperado'),
    ('Toscana', 'Itália', 'Mediterrâneo'),
    ('Douro', 'Portugal', 'Mediterrâneo continental'),
]

PRODUCERS = [
    ('Bodega Ernesto Catena', 'Mendoza', 2002),
    ('Catena Zapata', 'Mendoza', 1902),
    ('Casa Valduga', 'Serra Gaúcha', 1875),
    ('Concha y Toro', 'Valle del Maipo', 1883),
    ('Château Belair Demo', 'Bordeaux', None),
    ('Antinori', 'Toscana', 1385),
    ('Quinta do Crasto', 'Douro', 1615),
]

GRAPES = [
    ('Cabernet Sauvignon', 'tinta'),
    ('Chardonnay', 'branca'),
    ('Malbec', 'tinta'),
    ('Merlot', 'tinta'),
    ('Sangiovese', 'tinta'),
    ('Tinta Roriz', 'tinta'),
    ('Touriga Nacional', 'tinta'),
]

WINES = [
    {
        'name': 'Alma Negra Malbec', 'producer': 'Bodega Ernesto Catena',
        'color': 'tinto', 'sweetness': 'seco', 'alcohol': '13.50',
        'description': 'Malbec argentino demonstrativo de Mendoza.',
        'grapes': [('Malbec', '100.00')], 'vintage': 2021,
        'price': '149.90', 'stock': 18, 'score': '4.7',
    },
    {
        'name': 'Catena Malbec', 'producer': 'Catena Zapata',
        'color': 'tinto', 'sweetness': 'seco', 'alcohol': '13.50',
        'description': 'Malbec demonstrativo, encorpado e frutado.',
        'grapes': [('Malbec', '100.00')], 'vintage': 2022,
        'price': '139.90', 'stock': 24, 'score': '4.6',
    },
    {
        'name': 'Marques de Casa Concha Cabernet Sauvignon', 'producer': 'Concha y Toro',
        'color': 'tinto', 'sweetness': 'seco', 'alcohol': '14.00',
        'description': 'Cabernet Sauvignon chileno demonstrativo.',
        'grapes': [('Cabernet Sauvignon', '100.00')], 'vintage': 2021,
        'price': '169.90', 'stock': 15, 'score': '4.4',
    },
    {
        'name': 'Quinta do Crasto Douro Tinto', 'producer': 'Quinta do Crasto',
        'color': 'tinto', 'sweetness': 'seco', 'alcohol': '14.00',
        'description': 'Blend português demonstrativo da região do Douro.',
        'grapes': [('Touriga Nacional', '60.00'), ('Tinta Roriz', '40.00')],
        'vintage': 2020, 'price': '189.90', 'stock': 8, 'score': '4.5',
    },
    {
        'name': 'Peppoli Chianti Classico', 'producer': 'Antinori',
        'color': 'tinto', 'sweetness': 'seco', 'alcohol': '13.50',
        'description': 'Tinto italiano demonstrativo baseado em Sangiovese.',
        'grapes': [('Sangiovese', '90.00'), ('Cabernet Sauvignon', '10.00')],
        'vintage': 2021, 'price': '259.90', 'stock': 10, 'score': '4.3',
    },
    {
        'name': 'Casa Valduga Terroir Chardonnay', 'producer': 'Casa Valduga',
        'color': 'branco', 'sweetness': 'seco', 'alcohol': '12.50',
        'description': 'Branco brasileiro demonstrativo da Serra Gaúcha.',
        'grapes': [('Chardonnay', '100.00')], 'vintage': 2022,
        'price': '99.90', 'stock': 30, 'score': '4.2',
    },
    {
        'name': 'Casa Valduga Naturelle Tinto Suave', 'producer': 'Casa Valduga',
        'color': 'tinto', 'sweetness': 'suave', 'alcohol': '11.50',
        'description': 'Tinto suave brasileiro demonstrativo.',
        'grapes': [('Merlot', '60.00'), ('Cabernet Sauvignon', '40.00')],
        'vintage': 2023, 'price': '59.90', 'stock': 40, 'score': '3.9',
    },
    {
        'name': 'Bordeaux Reserve Demo', 'producer': 'Château Belair Demo',
        'color': 'tinto', 'sweetness': 'seco', 'alcohol': '13.00',
        'description': 'Blend francês fictício criado para testes relacionais.',
        'grapes': [('Cabernet Sauvignon', '70.00'), ('Merlot', '30.00')],
        'vintage': 2020, 'price': '349.90', 'stock': 6, 'score': '4.6',
    },
]


def seed_catalog(apps, schema_editor):
    WineCountry = apps.get_model('chatbot', 'WineCountry')
    WineRegion = apps.get_model('chatbot', 'WineRegion')
    WineProducer = apps.get_model('chatbot', 'WineProducer')
    GrapeVariety = apps.get_model('chatbot', 'GrapeVariety')
    Wine = apps.get_model('chatbot', 'Wine')
    WineGrape = apps.get_model('chatbot', 'WineGrape')
    WineOffer = apps.get_model('chatbot', 'WineOffer')
    WineReview = apps.get_model('chatbot', 'WineReview')

    countries = {
        name: WineCountry.objects.get_or_create(name=name, defaults={'iso_code': code})[0]
        for name, code in COUNTRIES
    }
    regions = {
        name: WineRegion.objects.get_or_create(
            name=name,
            country=countries[country],
            defaults={'climate': climate},
        )[0]
        for name, country, climate in REGIONS
    }
    producers = {
        name: WineProducer.objects.get_or_create(
            name=name,
            defaults={'region': regions[region], 'founded_year': founded_year},
        )[0]
        for name, region, founded_year in PRODUCERS
    }
    grapes = {
        name: GrapeVariety.objects.get_or_create(name=name, defaults={'color': color})[0]
        for name, color in GRAPES
    }

    for item in WINES:
        wine, _ = Wine.objects.get_or_create(
            name=item['name'],
            producer=producers[item['producer']],
            defaults={
                'color': item['color'],
                'sweetness': item['sweetness'],
                'alcohol_percentage': Decimal(item['alcohol']),
                'description': item['description'],
                'active': True,
                'is_demo': True,
            },
        )
        for grape_name, percentage in item['grapes']:
            WineGrape.objects.get_or_create(
                wine=wine,
                grape=grapes[grape_name],
                defaults={'percentage': Decimal(percentage)},
            )
        WineOffer.objects.get_or_create(
            wine=wine,
            vintage_year=item['vintage'],
            defaults={
                'price': Decimal(item['price']),
                'currency': 'BRL',
                'stock': item['stock'],
                'active': True,
            },
        )
        WineReview.objects.get_or_create(
            wine=wine,
            reviewer='Equipe DataGrapho (demonstração)',
            defaults={
                'score': Decimal(item['score']),
                'comment': 'Avaliação fictícia para teste do chatbot.',
            },
        )


def remove_demo_catalog(apps, schema_editor):
    Wine = apps.get_model('chatbot', 'Wine')
    WineProducer = apps.get_model('chatbot', 'WineProducer')
    WineRegion = apps.get_model('chatbot', 'WineRegion')
    WineCountry = apps.get_model('chatbot', 'WineCountry')
    GrapeVariety = apps.get_model('chatbot', 'GrapeVariety')

    Wine.objects.filter(is_demo=True, name__in=[item['name'] for item in WINES]).delete()
    WineProducer.objects.filter(
        name__in=[item[0] for item in PRODUCERS], wines__isnull=True
    ).delete()
    WineRegion.objects.filter(
        name__in=[item[0] for item in REGIONS], producers__isnull=True
    ).delete()
    WineCountry.objects.filter(
        name__in=[item[0] for item in COUNTRIES], regions__isnull=True
    ).delete()
    GrapeVariety.objects.filter(
        name__in=[item[0] for item in GRAPES], wine_links__isnull=True
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('chatbot', '0005_expand_wine_catalog')]

    operations = [migrations.RunPython(seed_catalog, remove_demo_catalog)]
