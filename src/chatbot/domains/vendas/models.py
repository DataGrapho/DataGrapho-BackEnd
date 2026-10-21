"""Modelos do domínio de vendas e pedidos.

Os dados são fictícios e servem apenas para demonstração do chatbot.
"""

from django.db import models


class VendasCliente(models.Model):
    nome = models.CharField(max_length=200)
    cidade = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    desde = models.DateField()

    class Meta:
        db_table = 'chatbot_vendas_cliente'
        verbose_name = 'Cliente'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class VendasProduto(models.Model):
    nome = models.CharField(max_length=200)
    categoria = models.CharField(max_length=80)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'chatbot_vendas_produto'
        verbose_name = 'Produto de venda'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class VendasPedido(models.Model):
    STATUS_CHOICES = [
        ('pago', 'Pago'),
        ('pendente', 'Pendente'),
        ('cancelado', 'Cancelado'),
    ]

    cliente = models.ForeignKey(
        VendasCliente, on_delete=models.PROTECT, related_name='pedidos'
    )
    data = models.DateField()
    vendedor = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pago')

    class Meta:
        db_table = 'chatbot_vendas_pedido'
        verbose_name = 'Pedido'
        ordering = ['-data']

    def __str__(self):
        return f'Pedido {self.pk} de {self.cliente}'


class VendasItemPedido(models.Model):
    pedido = models.ForeignKey(
        VendasPedido, on_delete=models.CASCADE, related_name='itens'
    )
    produto = models.ForeignKey(
        VendasProduto, on_delete=models.PROTECT, related_name='itens'
    )
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'chatbot_vendas_item_pedido'
        verbose_name = 'Item do pedido'

    def __str__(self):
        return f'{self.quantidade}x {self.produto}'
