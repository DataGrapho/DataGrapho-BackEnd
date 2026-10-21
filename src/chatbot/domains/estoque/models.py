"""Modelos do domínio de estoque de produtos.

Os dados são fictícios e servem apenas para demonstração do chatbot.
"""

from django.db import models


class EstoqueDeposito(models.Model):
    nome = models.CharField(max_length=120, unique=True)
    cidade = models.CharField(max_length=100)

    class Meta:
        db_table = 'chatbot_estoque_deposito'
        verbose_name = 'Depósito'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class EstoqueProduto(models.Model):
    sku = models.CharField(max_length=30, unique=True)
    nome = models.CharField(max_length=200)
    categoria = models.CharField(max_length=80)
    unidade = models.CharField(max_length=10, default='un')
    estoque_minimo = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'chatbot_estoque_produto'
        verbose_name = 'Produto em estoque'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.sku})'


class EstoqueSaldo(models.Model):
    produto = models.ForeignKey(
        EstoqueProduto, on_delete=models.CASCADE, related_name='saldos'
    )
    deposito = models.ForeignKey(
        EstoqueDeposito, on_delete=models.CASCADE, related_name='saldos'
    )
    quantidade = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'chatbot_estoque_saldo'
        verbose_name = 'Saldo de estoque'
        constraints = [
            models.UniqueConstraint(
                fields=['produto', 'deposito'], name='uq_estoque_saldo_produto_deposito'
            ),
        ]

    def __str__(self):
        return f'{self.produto} em {self.deposito}: {self.quantidade}'


class EstoqueMovimentacao(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    ]

    produto = models.ForeignKey(
        EstoqueProduto, on_delete=models.PROTECT, related_name='movimentacoes'
    )
    deposito = models.ForeignKey(
        EstoqueDeposito, on_delete=models.PROTECT, related_name='movimentacoes'
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    quantidade = models.PositiveIntegerField()
    data = models.DateField()
    motivo = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'chatbot_estoque_movimentacao'
        verbose_name = 'Movimentação de estoque'
        ordering = ['-data']

    def __str__(self):
        return f'{self.tipo} de {self.quantidade} de {self.produto} em {self.data}'
