from django.contrib import admin
from .models import CatalogoDePara


@admin.register(CatalogoDePara)
class CatalogoDeparaAdmin(admin.ModelAdmin):
    """
    Admin interface for CatalogoDePara model.
    """
    list_display = [
        'id_catalogo',
        'tabela_origem',
        'descricao',
        'ativo',
        'criado_em'
    ]
    list_filter = ['ativo', 'criado_em']
    search_fields = ['tabela_origem', 'descricao']
    readonly_fields = ['id_catalogo', 'criado_em', 'atualizado_em']
    
    fieldsets = (
        ('Informações Principais', {
            'fields': ('tabela_origem', 'descricao', 'ativo')
        }),
        ('Metadados', {
            'fields': ('id_catalogo', 'criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields
        return []
