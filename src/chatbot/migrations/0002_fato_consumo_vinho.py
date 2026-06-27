

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FatoConsumoVinho',
            fields=[
                ('id_fato_consumo', models.AutoField(db_column='IdFatoConsumo', primary_key=True, serialize=False)),
                ('evento', models.CharField(db_column='Evento', max_length=1, verbose_name='Evento')),
                ('data_consumo', models.DateField(db_column='DataConsumo', verbose_name='Data do Consumo')),
                ('vinho', models.CharField(db_column='Vinho', max_length=300, verbose_name='Vinho')),
                ('uva', models.CharField(blank=True, db_column='Uva', max_length=300, null=True, verbose_name='Uva')),
                ('safra', models.IntegerField(blank=True, db_column='Safra', null=True, verbose_name='Safra')),
                ('produtor', models.CharField(blank=True, db_column='Produtor', max_length=300, null=True, verbose_name='Produtor')),
                ('cor', models.CharField(db_column='Cor', max_length=50, verbose_name='Cor')),
                ('teor_acucar', models.CharField(blank=True, db_column='TeorAcucar', max_length=50, null=True, verbose_name='Teor de Açúcar')),
                ('teor_alcoolico', models.CharField(blank=True, db_column='TeorAlcoolico', max_length=10, null=True, verbose_name='Teor Alcoólico')),
                ('pais', models.CharField(blank=True, db_column='Pais', max_length=100, null=True, verbose_name='País')),
                ('regiao', models.CharField(blank=True, db_column='Regiao', max_length=300, null=True, verbose_name='Região')),
                ('opiniao', models.CharField(blank=True, db_column='Opiniao', max_length=100, null=True, verbose_name='Opinião')),
                ('preco', models.DecimalField(blank=True, db_column='Preco', decimal_places=2, max_digits=10, null=True, verbose_name='Preço')),
                ('qtd', models.IntegerField(db_column='Qtd', default=1, verbose_name='Quantidade')),
                ('qtd_otimo', models.IntegerField(blank=True, db_column='QtdOtimo', null=True, verbose_name='Quantidade Ótimo')),
                ('total', models.DecimalField(blank=True, db_column='Total', decimal_places=2, max_digits=10, null=True, verbose_name='Total')),
                ('degustacao', models.IntegerField(blank=True, db_column='Degustacao', null=True, verbose_name='Degustação')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
            ],
            options={
                'verbose_name': 'Fato Consumo Vinho',
                'verbose_name_plural': 'Fatos Consumo Vinho',
                'db_table': 'chatbot_fato_consumo_vinho',
                'ordering': ['-data_consumo'],
                'indexes': [
                    models.Index(fields=['data_consumo'], name='idx_fato_consumo_data'),
                    models.Index(fields=['vinho'], name='idx_fato_consumo_vinho'),
                    models.Index(fields=['pais'], name='idx_fato_consumo_pais'),
                ],
            },
        ),
    ]
