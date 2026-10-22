"""Cria dados fictícios de demonstração: estrutura organizacional e domínios do chatbot.

É executado pelo container `web` logo após as migrations, a cada inicialização.
Cada parte só cria dados quando ainda não existem registros, sem alterar o que já houver.
"""

import random
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.seed import SENHA_DEMO_USUARIOS, seed_demo_organizacao, seed_demo_usuarios
from depara.seed import seed_demo_depara
from chatbot.domains.convenio import seed as convenio_seed
from chatbot.domains.estoque import seed as estoque_seed
from chatbot.domains.vendas import seed as vendas_seed


class Command(BaseCommand):
    help = (
        'Cria dados fictícios de demonstração: empresas, filiais, setores, perfis '
        'e os domínios convenio, vendas e estoque.'
    )

    def handle(self, *args, **options):
        if seed_demo_organizacao():
            self.stdout.write(self.style.SUCCESS('Estrutura organizacional de demonstração criada'))
        else:
            self.stdout.write('Estrutura organizacional já existente, mantida')

        if seed_demo_depara():
            self.stdout.write(self.style.SUCCESS('Catálogos De/Para de demonstração criados'))
        else:
            self.stdout.write('Catálogos De/Para já existentes, mantidos')

        # Usuários com senha conhecida existem só em ambiente local (DEBUG=True).
        if settings.DEBUG:
            criados = seed_demo_usuarios(SENHA_DEMO_USUARIOS)
            if criados:
                self.stdout.write(self.style.SUCCESS(f'Usuários de demonstração criados: {criados}'))
            else:
                self.stdout.write('Usuários de demonstração já existentes, mantidos')
        else:
            self.stdout.write('Usuários de demonstração não criados: somente em ambiente local (DEBUG)')

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
