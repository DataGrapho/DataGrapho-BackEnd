"""Cria dados fictícios de demonstração para os domínios de convênio, vendas e estoque.

Não é executado pelas migrations: rode manualmente, apenas em ambientes de
demonstração. Se um domínio já tiver dados, ele é mantido sem alterações.
"""

import random
from datetime import date

from django.core.management.base import BaseCommand

from chatbot.domains.convenio import seed as convenio_seed
from chatbot.domains.estoque import seed as estoque_seed
from chatbot.domains.vendas import seed as vendas_seed


class Command(BaseCommand):
    help = 'Cria dados fictícios de demonstração para os domínios convenio, vendas e estoque.'

    def handle(self, *args, **options):
        today = date.today()
        seeders = [
            ('convenio', convenio_seed.seed_demo_data),
            ('vendas', vendas_seed.seed_demo_data),
            ('estoque', estoque_seed.seed_demo_data),
        ]
        for name, seed in seeders:
            # Semente fixa: a mesma execução gera sempre os mesmos dados de demonstração.
            created = seed(random.Random(42), today)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Dados de demonstração criados: {name}'))
            else:
                self.stdout.write(f'Dados já existentes, mantidos: {name}')
