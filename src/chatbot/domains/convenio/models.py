"""Modelos do domínio de convênio médico.

Os dados são fictícios e servem apenas para demonstração do chatbot.
"""

from django.db import models


class ConvenioPlano(models.Model):
    TIPO_CHOICES = [
        ('ambulatorial', 'Ambulatorial'),
        ('hospitalar', 'Hospitalar'),
        ('completo', 'Completo'),
    ]

    nome = models.CharField(max_length=120)
    operadora = models.CharField(max_length=120)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    mensalidade = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'chatbot_convenio_plano'
        verbose_name = 'Plano de convênio'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.operadora})'


class ConvenioBeneficiario(models.Model):
    nome = models.CharField(max_length=200)
    plano = models.ForeignKey(
        ConvenioPlano, on_delete=models.PROTECT, related_name='beneficiarios'
    )
    cidade = models.CharField(max_length=100, blank=True)
    data_adesao = models.DateField()
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'chatbot_convenio_beneficiario'
        verbose_name = 'Beneficiário'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class ConvenioAtendimento(models.Model):
    TIPO_CHOICES = [
        ('consulta', 'Consulta'),
        ('exame', 'Exame'),
        ('terapia', 'Terapia'),
        ('internacao', 'Internação'),
    ]
    STATUS_CHOICES = [
        ('autorizado', 'Autorizado'),
        ('negado', 'Negado'),
        ('pendente', 'Pendente'),
    ]

    beneficiario = models.ForeignKey(
        ConvenioBeneficiario, on_delete=models.PROTECT, related_name='atendimentos'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    especialidade = models.CharField(max_length=80)
    data = models.DateField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='autorizado')

    class Meta:
        db_table = 'chatbot_convenio_atendimento'
        verbose_name = 'Atendimento'
        ordering = ['-data']

    def __str__(self):
        return f'{self.tipo} {self.especialidade} em {self.data}'
