from django.db import models


class CatalogoDePara(models.Model):

    """Model for Catálogo DePara entity.

    Represents a catalog that maps the origin table information
    used in data transformation mappings.
    """

    id_catalogo = models.AutoField(primary_key=True, verbose_name="ID do Catálogo")

    tabela_origem = models.CharField(max_length=100, null=False, verbose_name="Tabela de Origem")

    descricao = models.TextField(null=True, blank=True, verbose_name="Descrição")

    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        db_table = "catalogo_depara"
        verbose_name = "Catálogo DePara"
        verbose_name_plural = "Catálogos DePara"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.tabela_origem} - {self.descricao}"
