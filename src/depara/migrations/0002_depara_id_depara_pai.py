# Generated migration for adding self-referencing foreign key

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('depara', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='depara',
            name='id_depara_pai',
            field=models.ForeignKey(blank=True, db_column='id_depara_pai', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='de_paras_filhos', to='depara.depara', verbose_name='ID DePara Pai'),
        ),
    ]
