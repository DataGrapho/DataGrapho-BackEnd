"""Dados fictícios de demonstração do domínio de convênio médico."""

import random
from datetime import date, timedelta
from decimal import Decimal

from chatbot.domains.convenio.models import (
    ConvenioAtendimento,
    ConvenioBeneficiario,
    ConvenioPlano,
)


PLANOS = [
    ('Plano Essencial', 'Saúde Demo Seguros', 'ambulatorial', Decimal('189.90')),
    ('Plano Básico Jovem', 'Vida Exemplo Saúde', 'ambulatorial', Decimal('129.50')),
    ('Plano Conforto', 'Saúde Demo Seguros', 'hospitalar', Decimal('359.90')),
    ('Plano Premium', 'Vida Exemplo Saúde', 'completo', Decimal('589.00')),
]

BENEFICIARIOS = [
    'Mariana Alves', 'Carlos Lima', 'Beatriz Ferreira', 'Rafael Santos',
    'Juliana Costa', 'Lucas Oliveira', 'Patrícia Nunes', 'Felipe Rocha',
    'Camila Barbosa', 'Gustavo Pereira',
]

CIDADES = ['São Paulo', 'Curitiba', 'Belo Horizonte', 'Porto Alegre']

ESPECIALIDADES = [
    ('Clínica Geral', 'consulta', (150, 300)),
    ('Cardiologia', 'consulta', (250, 420)),
    ('Ortopedia', 'consulta', (220, 380)),
    ('Dermatologia', 'consulta', (180, 320)),
    ('Pediatria', 'consulta', (160, 280)),
    ('Oftalmologia', 'exame', (120, 350)),
    ('Laboratório', 'exame', (80, 260)),
    ('Psicologia', 'terapia', (120, 200)),
    ('Internação clínica', 'internacao', (2000, 9000)),
]


def seed_demo_data(rng: random.Random, today: date) -> bool:
    """Cria planos, beneficiários e atendimentos. Não sobrescreve dados existentes."""
    if ConvenioPlano.objects.exists():
        return False

    planos = [
        ConvenioPlano.objects.create(
            nome=nome, operadora=operadora, tipo=tipo, mensalidade=mensalidade
        )
        for nome, operadora, tipo, mensalidade in PLANOS
    ]

    beneficiarios = []
    for index, nome in enumerate(BENEFICIARIOS):
        beneficiarios.append(ConvenioBeneficiario.objects.create(
            nome=nome,
            plano=planos[index % len(planos)],
            cidade=rng.choice(CIDADES),
            data_adesao=today - timedelta(days=rng.randint(120, 1500)),
        ))

    for beneficiario in beneficiarios:
        for _ in range(rng.randint(3, 9)):
            especialidade, tipo, (minimo, maximo) = rng.choice(ESPECIALIDADES)
            roll = rng.random()
            status = 'autorizado' if roll < 0.85 else ('negado' if roll < 0.92 else 'pendente')
            ConvenioAtendimento.objects.create(
                beneficiario=beneficiario,
                tipo=tipo,
                especialidade=especialidade,
                data=today - timedelta(days=rng.randint(0, 180)),
                valor=Decimal(rng.randint(minimo, maximo)),
                status=status,
            )
    return True
