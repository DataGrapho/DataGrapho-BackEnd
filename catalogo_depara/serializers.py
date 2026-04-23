from rest_framework import serializers
from .models import CatalogoDePara


class CatalogoDeparaSerializer(serializers.ModelSerializer):
    """
    Serializer for CatalogoDePara model.
    
    Converts CatalogoDePara model instances to/from JSON representation.
    """
    
    class Meta:
        model = CatalogoDePara
        fields = [
            'id_catalogo',
            'tabela_origem',
            'descricao',
            'ativo',
            'criado_em',
            'atualizado_em'
        ]
        read_only_fields = [
            'id_catalogo',
            'criado_em',
            'atualizado_em'
        ]


class CatalogoDeparaListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for CatalogoDePara list views.
    """
    
    class Meta:
        model = CatalogoDePara
        fields = [
            'id_catalogo',
            'tabela_origem',
            'descricao',
            'ativo'
        ]
