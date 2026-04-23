from django.contrib import admin
from .entity import DePara


@admin.register(DePara)
class DeparaAdmin(admin.ModelAdmin):
    """
    Admin interface for DePara model.
    """
    list_display = [
        'id_depara',
        'id_catalogo',
        'codigo_origem',
        'codigo_destino',
        'ativo',
        'criado_em'
    ]
    list_filter = ['ativo', 'id_catalogo', 'criado_em']
    search_fields = ['codigo_origem', 'codigo_destino', 'descricao_origem', 'descricao_destino']
    readonly_fields = ['id_depara', 'criado_em', 'atualizado_em']
    
    fieldsets = (
        ('Catálogo', {
            'fields': ('id_catalogo', 'id_acesso')
        }),
        ('Mapeamento de Origem', {
            'fields': ('codigo_origem', 'descricao_origem')
        }),
        ('Mapeamento de Destino', {
            'fields': ('codigo_destino', 'descricao_destino')
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
        ('Metadados', {
            'fields': ('id_depara', 'criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['id_catalogo']
        return []
