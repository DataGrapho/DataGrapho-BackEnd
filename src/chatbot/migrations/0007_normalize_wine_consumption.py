import re
import unicodedata
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import django.db.models.deletion
from django.db import migrations, models


COUNTRIES = [
    ('Argentina', 'AR', 'Mendoza'), ('Austrália', 'AU', 'Barossa Valley'),
    ('África do Sul', 'ZA', 'Stellenbosch'), ('Alemanha', 'DE', 'Mosel'),
    ('Brasil', 'BR', 'Serra Gaúcha'), ('Chile', 'CL', 'Valle del Maipo'),
    ('Espanha', 'ES', 'Rioja'), ('Estados Unidos', 'US', 'Napa Valley'),
    ('França', 'FR', 'Bordeaux'), ('Grécia', 'GR', 'Santorini'),
    ('Hungria', 'HU', 'Tokaj'), ('Itália', 'IT', 'Toscana'),
    ('Japão', 'JP', 'Yamanashi'), ('Nova Zelândia', 'NZ', 'Marlborough'),
    ('Portugal', 'PT', 'Douro'), ('Romênia', 'RO', 'Dealu Mare'),
    ('Suíça', 'CH', 'Valais'), ('Uruguai', 'UY', 'Canelones'),
    ('Áustria', 'AT', 'Wachau'), ('Canadá', 'CA', 'Okanagan Valley'),
]

GRAPES = [
    ('Cabernet Sauvignon', 'tinta'), ('Chardonnay', 'branca'),
    ('Malbec', 'tinta'), ('Merlot', 'tinta'), ('Pinot Noir', 'tinta'),
    ('Riesling', 'branca'), ('Sangiovese', 'tinta'), ('Sauvignon Blanc', 'branca'),
    ('Syrah', 'tinta'), ('Tempranillo', 'tinta'),
    ('Touriga Nacional', 'tinta'), ('Tannat', 'tinta'),
]

ISO_BY_COUNTRY = {name: code for name, code, _region in COUNTRIES}
OPINION_SCORES = {
    'ruim': Decimal('2.0'), 'bom': Decimal('3.5'),
    'muito bom': Decimal('4.3'), 'otimo': Decimal('4.7'),
    'excelente': Decimal('5.0'),
}


def normalize(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(char for char in text if not unicodedata.combining(char)).strip().casefold()


def useful(value):
    return bool(value and normalize(value) not in {'nao informado', '(nao informado)', 'null'})


def decimal_or_none(value):
    if value in (None, ''):
        return None
    try:
        cleaned = str(value).replace('%', '').replace(',', '.').strip()
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def style(value, options, default):
    normalized = normalize(value).replace(' ', '_').replace('-', '_')
    return normalized if normalized in options else default


def migrate_and_seed(apps, schema_editor):
    Legacy = apps.get_model('chatbot', 'FatoConsumoVinho')
    Country = apps.get_model('chatbot', 'WineCountry')
    Region = apps.get_model('chatbot', 'WineRegion')
    Producer = apps.get_model('chatbot', 'WineProducer')
    Grape = apps.get_model('chatbot', 'GrapeVariety')
    Wine = apps.get_model('chatbot', 'Wine')
    WineGrape = apps.get_model('chatbot', 'WineGrape')
    Offer = apps.get_model('chatbot', 'WineOffer')
    Review = apps.get_model('chatbot', 'WineReview')
    Consumption = apps.get_model('chatbot', 'WineConsumption')

    grape_cache = {}
    for grape_name, grape_color in GRAPES:
        grape_cache[normalize(grape_name)] = Grape.objects.get_or_create(
            name=grape_name, defaults={'color': grape_color}
        )[0]

    for row in Legacy.objects.all().iterator():
        country_name = row.pais.strip() if useful(row.pais) else 'Origem não informada'
        iso_code = ISO_BY_COUNTRY.get(country_name)
        if not iso_code:
            iso_code = f'X{Country.objects.filter(iso_code__startswith="X").count() % 10}'
            while Country.objects.filter(iso_code=iso_code).exclude(name=country_name).exists():
                iso_code = f'Y{Country.objects.filter(iso_code__startswith="Y").count() % 10}'
        country, _ = Country.objects.get_or_create(
            name=country_name, defaults={'iso_code': iso_code}
        )
        region_name = row.regiao.strip() if useful(row.regiao) else f'Região não informada - {country_name}'
        region, _ = Region.objects.get_or_create(
            country=country, name=region_name, defaults={'climate': ''}
        )
        producer_name = row.produtor.strip() if useful(row.produtor) else f'Produtor não informado - {country_name}'
        producer, _ = Producer.objects.get_or_create(
            name=producer_name, defaults={'region': region}
        )
        wine_name = row.vinho.strip() if useful(row.vinho) else f'Vinho legado {row.pk}'
        alcohol = decimal_or_none(row.teor_alcoolico)
        wine, created = Wine.objects.get_or_create(
            producer=producer,
            name=wine_name,
            defaults={
                'color': style(row.cor, {'tinto', 'branco', 'rose', 'espumante'}, 'tinto'),
                'sweetness': style(
                    row.teor_acucar, {'seco', 'meio_seco', 'suave', 'doce'}, 'seco'
                ),
                'alcohol_percentage': alcohol,
                'description': 'Importado do histórico legado de consumo.',
                'active': True,
                'is_demo': False,
            },
        )
        if useful(row.uva):
            grape_names = [item.strip(' *') for item in re.split(r'[,;/]|\s+e\s+', row.uva) if useful(item)]
            for grape_name in grape_names:
                key = normalize(grape_name)
                grape = grape_cache.get(key)
                if grape is None:
                    grape, _ = Grape.objects.get_or_create(
                        name=grape_name[:120], defaults={'color': 'tinta'}
                    )
                    grape_cache[key] = grape
                WineGrape.objects.get_or_create(wine=wine, grape=grape)
        if row.preco is not None:
            Offer.objects.get_or_create(
                wine=wine, vintage_year=row.safra,
                defaults={'price': row.preco, 'stock': 0, 'active': False},
            )
        opinion = row.opiniao.strip() if useful(row.opiniao) else ''
        score = OPINION_SCORES.get(normalize(opinion))
        if score is not None and not Review.objects.filter(
            wine=wine, reviewer='Histórico legado', comment=opinion
        ).exists():
            Review.objects.create(
                wine=wine, reviewer='Histórico legado', score=score, comment=opinion
            )
        Consumption.objects.create(
            wine=wine,
            event_type=row.evento or 'C',
            consumed_at=row.data_consumo,
            vintage_year=row.safra,
            opinion=opinion,
            unit_price=row.preco,
            quantity=max(1, row.qtd or 1),
            optimal_quantity=row.qtd_otimo,
            total=row.total,
            tasting_score=row.degustacao,
            is_demo=False,
        )

    demo_grapes = list(grape_cache.values())
    base_date = date(2023, 1, 1)
    for country_index, (country_name, iso_code, region_name) in enumerate(COUNTRIES):
        country, _ = Country.objects.get_or_create(
            name=country_name, defaults={'iso_code': iso_code}
        )
        region, _ = Region.objects.get_or_create(
            country=country, name=region_name, defaults={'climate': 'Clima vinícola demonstrativo'}
        )
        for producer_index in range(1, 3):
            producer, _ = Producer.objects.get_or_create(
                name=f'Vinícola Demo {country_name} {producer_index}',
                defaults={'region': region},
            )
            for wine_index in range(1, 5):
                serial = country_index * 8 + (producer_index - 1) * 4 + wine_index
                grape = demo_grapes[(serial - 1) % len(demo_grapes)]
                color = 'branco' if grape.color == 'branca' else 'tinto'
                wine, _ = Wine.objects.get_or_create(
                    producer=producer,
                    name=f'Reserva Demo {country_name} {producer_index}-{wine_index}',
                    defaults={
                        'color': color,
                        'sweetness': 'seco' if serial % 4 else 'meio_seco',
                        'alcohol_percentage': Decimal('11.5') + Decimal(serial % 7) / 2,
                        'description': 'Registro demonstrativo para consultas do chatbot.',
                        'active': True,
                        'is_demo': True,
                    },
                )
                WineGrape.objects.get_or_create(
                    wine=wine, grape=grape, defaults={'percentage': Decimal('100.00')}
                )
                price = Decimal('45.00') + Decimal(serial * 3)
                Offer.objects.get_or_create(
                    wine=wine, vintage_year=2018 + serial % 7,
                    defaults={'price': price, 'stock': 5 + serial % 40, 'active': True},
                )
                if not Review.objects.filter(wine=wine, reviewer='Catálogo demonstrativo').exists():
                    Review.objects.create(
                        wine=wine,
                        reviewer='Catálogo demonstrativo',
                        score=Decimal('3.5') + Decimal(serial % 15) / 10,
                        comment='Avaliação fictícia para testes.',
                    )
                Consumption.objects.get_or_create(
                    wine=wine,
                    consumed_at=base_date + timedelta(days=serial * 5),
                    defaults={
                        'event_type': 'C', 'vintage_year': 2018 + serial % 7,
                        'opinion': 'Bom' if serial % 3 else 'Muito Bom',
                        'unit_price': price, 'quantity': 1 + serial % 5,
                        'total': price * (1 + serial % 5), 'is_demo': True,
                    },
                )


def restore_legacy(apps, schema_editor):
    Legacy = apps.get_model('chatbot', 'FatoConsumoVinho')
    Consumption = apps.get_model('chatbot', 'WineConsumption')
    Wine = apps.get_model('chatbot', 'Wine')

    for item in Consumption.objects.filter(is_demo=False).select_related(
        'wine__producer__region__country'
    ).prefetch_related('wine__grape_links__grape'):
        wine = item.wine
        Legacy.objects.create(
            evento=(item.event_type or 'C')[:1], data_consumo=item.consumed_at,
            vinho=wine.name,
            uva=', '.join(link.grape.name for link in wine.grape_links.all()),
            safra=item.vintage_year, produtor=wine.producer.name,
            cor=wine.color, teor_acucar=wine.sweetness,
            teor_alcoolico=str(wine.alcohol_percentage or ''),
            pais=wine.producer.region.country.name, regiao=wine.producer.region.name,
            opiniao=item.opinion, preco=item.unit_price, qtd=item.quantity,
            qtd_otimo=item.optimal_quantity, total=item.total, degustacao=item.tasting_score,
        )
    Wine.objects.filter(name__startswith='Reserva Demo ').delete()
    Wine.objects.filter(description='Importado do histórico legado de consumo.').delete()


class Migration(migrations.Migration):
    dependencies = [('chatbot', '0006_seed_wine_catalog')]

    operations = [
        migrations.CreateModel(
            name='WineConsumption',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(default='consumo', max_length=20)),
                ('consumed_at', models.DateField(verbose_name='Data do consumo')),
                ('vintage_year', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('opinion', models.CharField(blank=True, max_length=100)),
                ('unit_price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('optimal_quantity', models.PositiveIntegerField(blank=True, null=True)),
                ('total', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('tasting_score', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('is_demo', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('wine', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='consumptions', to='chatbot.wine')),
            ],
            options={'db_table': 'chatbot_wine_consumption', 'ordering': ['-consumed_at']},
        ),
        migrations.AddIndex(
            model_name='wineconsumption',
            index=models.Index(fields=['consumed_at'], name='idx_wine_consumed_at'),
        ),
        migrations.AddIndex(
            model_name='wineconsumption',
            index=models.Index(fields=['wine', '-consumed_at'], name='idx_wine_consumption'),
        ),
        migrations.AddConstraint(
            model_name='wineconsumption',
            constraint=models.CheckConstraint(condition=models.Q(('quantity__gte', 1)), name='ck_consumption_quantity'),
        ),
        migrations.AddConstraint(
            model_name='wineconsumption',
            constraint=models.CheckConstraint(condition=models.Q(('unit_price__isnull', True), ('unit_price__gte', 0), _connector='OR'), name='ck_consumption_unit_price'),
        ),
        migrations.RunPython(migrate_and_seed, restore_legacy),
        migrations.DeleteModel(name='FatoConsumoVinho'),
    ]
