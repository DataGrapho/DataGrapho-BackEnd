"""Dados fictícios de demonstração do domínio de estoque de produtos."""

import random
from datetime import date, timedelta

from chatbot.domains.estoque.models import (
    EstoqueDeposito,
    EstoqueMovimentacao,
    EstoqueProduto,
    EstoqueSaldo,
)


DEPOSITOS = [
    ('Depósito Central', 'São Paulo'),
    ('Depósito Sul', 'Curitiba'),
    ('Loja Centro', 'Belo Horizonte'),
]

# sku, nome, categoria, unidade, estoque mínimo, saldo por depósito (na ordem de DEPOSITOS)
PRODUTOS = [
    ('SKU-1001', 'Parafuso sextavado M8', 'Ferragens', 'un', 500, (320, 150, 40)),
    ('SKU-1002', 'Furadeira de impacto 650W', 'Ferramentas', 'un', 10, (4, 3, 0)),
    ('SKU-1003', 'Tinta acrílica branca 18L', 'Tintas', 'lata', 20, (30, 12, 5)),
    ('SKU-1004', 'Lâmpada LED 9W', 'Elétrica', 'un', 100, (180, 90, 60)),
    ('SKU-1005', 'Cabo flexível 2,5mm (rolo 100m)', 'Elétrica', 'rolo', 15, (6, 2, 0)),
    ('SKU-1006', 'Luva de proteção nitrílica (par)', 'EPI', 'par', 60, (40, 25, 30)),
    ('SKU-1007', 'Fita isolante', 'Elétrica', 'un', 80, (0, 20, 35)),
]


def seed_demo_data(rng: random.Random, today: date) -> bool:
    """Cria depósitos, produtos, saldos e movimentações. Não sobrescreve dados existentes."""
    if EstoqueProduto.objects.exists():
        return False

    depositos = [
        EstoqueDeposito.objects.create(nome=nome, cidade=cidade)
        for nome, cidade in DEPOSITOS
    ]

    produtos = []
    for sku, nome, categoria, unidade, minimo, saldos in PRODUTOS:
        produto = EstoqueProduto.objects.create(
            sku=sku, nome=nome, categoria=categoria, unidade=unidade, estoque_minimo=minimo
        )
        produtos.append(produto)
        for deposito, quantidade in zip(depositos, saldos):
            EstoqueSaldo.objects.create(produto=produto, deposito=deposito, quantidade=quantidade)

    for _ in range(40):
        tipo = rng.choice(['entrada', 'saida'])
        quantidade = rng.randint(5, 50) if tipo == 'entrada' else rng.randint(1, 20)
        EstoqueMovimentacao.objects.create(
            produto=rng.choice(produtos),
            deposito=rng.choice(depositos),
            tipo=tipo,
            quantidade=quantidade,
            data=today - timedelta(days=rng.randint(0, 90)),
            motivo='Reposição de fornecedor' if tipo == 'entrada' else 'Venda ou consumo interno',
        )
    return True
