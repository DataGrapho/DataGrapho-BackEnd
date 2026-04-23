from rest_framework import serializers

from .models import DePara


class DeparaSerializer(serializers.ModelSerializer):
    """
    Serializer for DePara model.
    
    Converts DePara model instances to/from JSON representation.
    """
    
    class Meta:
        model = DePara
        fields = [
            'id_depara',
            'id_catalogo',
            'id_acesso',
            'codigo_origem',
            'descricao_origem',
            'codigo_destino',
            'descricao_destino',
            'ativo',
            'criado_em',
            'atualizado_em'
        ]
        read_only_fields = [
            'id_depara',
            'criado_em',
            'atualizado_em'
        ]


class DeparaListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for DePara list views.
    """
    
    catalogo_tabela = serializers.CharField(
        source='id_catalogo.tabela_origem',
        read_only=True
    )
    
    class Meta:
        model = DePara
        fields = [
            'id_depara',
            'id_catalogo',
            'catalogo_tabela',
            'codigo_origem',
            'codigo_destino',
            'ativo',
            'criado_em'
        ]


class DeparaDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for DePara with catalog information.
    """
    
    catalogo = serializers.SerializerMethodField()
    
    class Meta:
        model = DePara
        fields = [
            'id_depara',
            'id_catalogo',
            'catalogo',
            'id_acesso',
            'codigo_origem',
            'descricao_origem',
            'codigo_destino',
            'descricao_destino',
            'ativo',
            'criado_em',
            'atualizado_em'
        ]
        read_only_fields = [
            'id_depara',
            'criado_em',
            'atualizado_em'
        ]
    
    def get_catalogo(self, obj):
        return {
            'id_catalogo': obj.id_catalogo.id_catalogo,
            'tabela_origem': obj.id_catalogo.tabela_origem,
            'descricao': obj.id_catalogo.descricao,
            'ativo': obj.id_catalogo.ativo
        }
