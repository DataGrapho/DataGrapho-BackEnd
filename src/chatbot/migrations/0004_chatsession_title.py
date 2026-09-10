from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chatbot", "0003_seed_fato_consumo_vinho"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatsession",
            name="title",
            field=models.CharField(default="Novo chat", max_length=120),
        ),
    ]
