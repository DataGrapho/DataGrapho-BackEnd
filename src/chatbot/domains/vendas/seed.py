"""Dados fictícios de demonstração do domínio de vendas e pedidos."""

import random
from datetime import date, timedelta
from decimal import Decimal

from chatbot.domains.vendas.models import (
    VendasCliente,
    VendasItemPedido,
    VendasPedido,
    VendasProduto,
)


CLIENTES = [
    ('Empresa Alfa Comércio', 'São Paulo', 'SP'),
    ('Mercado Beta Ltda', 'Curitiba', 'PR'),
    ('Oficina Gama', 'Belo Horizonte', 'MG'),
    ('Distribuidora Delta', 'Porto Alegre', 'RS'),
    ('Loja Épsilon', 'Campinas', 'SP'),
    ('Construtora Zeta', 'Londrina', 'PR'),
    ('Papelaria Eta', 'Uberlândia', 'MG'),
    ('Atacado Theta', 'Joinville', 'SC'),
]

PRODUTOS = [
    ('Notebook Ultra 14', 'Informática', Decimal('4299.90')),
    ('Monitor 24 polegadas', 'Informática', Decimal('899.00')),
    ('Teclado mecânico', 'Informática', Decimal('329.00')),
    ('Mouse sem fio', 'Informática', Decimal('89.90')),
    ('Cadeira ergonômica', 'Escritório', Decimal('1290.00')),
    ('Mesa de escritório', 'Escritório', Decimal('780.00')),
    ('Caneta esferográfica (caixa com 50)', 'Papelaria', Decimal('45.00')),
    ('Papel A4 (resma)', 'Papelaria', Decimal('27.50')),
]

VENDEDORES = ['Juliana Costa', 'Rafael Mendes', 'Patrícia Nunes']


def seed_demo_data(rng: random.Random, today: date) -> bool:
    """Cria clientes, produtos e pedidos. Não sobrescreve dados existentes."""
    if VendasPedido.objects.exists():
        return False

    clientes = [
        VendasCliente.objects.create(
            nome=nome, cidade=cidade, uf=uf,
            desde=today - timedelta(days=rng.randint(200, 1200)),
        )
        for nome, cidade, uf in CLIENTES
    ]
    produtos = [
        VendasProduto.objects.create(nome=nome, categoria=categoria, preco_unitario=preco)
        for nome, categoria, preco in PRODUTOS
    ]

    for _ in range(60):
        roll = rng.random()
        status = 'pago' if roll < 0.80 else ('pendente' if roll < 0.90 else 'cancelado')
        pedido = VendasPedido.objects.create(
            cliente=rng.choice(clientes),
            data=today - timedelta(days=rng.randint(0, 180)),
            vendedor=rng.choice(VENDEDORES),
            status=status,
        )
        for produto in rng.sample(produtos, k=rng.randint(1, 4)):
            VendasItemPedido.objects.create(
                pedido=pedido,
                produto=produto,
                quantidade=rng.randint(1, 5),
                preco_unitario=produto.preco_unitario,
            )
    return True
