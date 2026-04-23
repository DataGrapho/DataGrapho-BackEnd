from django.db import models

from catalogo_depara.entity import CatalogoDePara


class DePara(models.Model):
    """Model for DePara entity."""

    id_depara = models.AutoField(primary_key=True, verbose_name="ID DePara")

    id_catalogo = models.ForeignKey(CatalogoDePara, on_delete=models.CASCADE, verbose_name="ID Catálogo")

    id_acesso = models.IntegerField(null=True, blank=True, verbose_name="ID Acesso")

    codigo_origem = models.CharField(max_length=100, null=False, verbose_name="Código de Origem")

    descricao_origem = models.TextField(null=True, blank=True, verbose_name="Descrição de Origem")

    codigo_destino = models.CharField(max_length=100, null=False, verbose_name="Código de Destino")

    descricao_destino = models.TextField(null=True, blank=True, verbose_name="Descrição de Destino")

    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        db_table = "depara"
        verbose_name = "DePara"
        verbose_name_plural = "DePara"
        ordering = ["-criado_em"]
        unique_together = [["id_catalogo", "codigo_origem", "codigo_destino"]]

    def __str__(self):
        return f"{self.codigo_origem} -> {self.codigo_destino}"
