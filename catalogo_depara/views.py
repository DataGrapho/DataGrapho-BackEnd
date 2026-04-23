from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import CatalogoDePara
from .serializers import CatalogoDeparaSerializer, CatalogoDeparaListSerializer
from .service import CatalogoDeparaService


class CatalogoDeparaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing CatalogoDePara entities.
    
    Provides CRUD operations through REST API endpoints.
    Implements the controller layer handling HTTP requests/responses.
    """
    
    queryset = CatalogoDePara.objects.all()
    serializer_class = CatalogoDeparaSerializer
    lookup_field = 'id_catalogo'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = CatalogoDeparaService()

    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the action.
        """
        if self.action == 'list':
            return CatalogoDeparaListSerializer
        return CatalogoDeparaSerializer

    def list(self, request, *args, **kwargs):
        """
        List all catalogs with optional filters.
        
        Query Parameters:
            - ativo: Filter by active status (true/false)
            - tabela_origem: Filter by origin table name
            - search: Search in multiple fields
        """
        try:
            ativo = request.query_params.get('ativo')
            if ativo is not None:
                ativo = ativo.lower() == 'true'
            
            tabela_origem = request.query_params.get('tabela_origem')
            search = request.query_params.get('search')
            
            catalogs = self.service.list_catalogos(
                ativo=ativo,
                tabela_origem=tabela_origem,
                search=search
            )
            
            serializer = self.get_serializer(catalogs, many=True)
            
            return Response({
                'success': True,
                'count': len(catalogs),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        """
        Create a new catalog.
        """
        try:
            catalog = self.service.create_catalogo(request.data)
            serializer = self.get_serializer(catalog)
            
            return Response({
                'success': True,
                'message': 'Catálogo criado com sucesso',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific catalog by ID.
        """
        try:
            id_catalogo = kwargs.get('id_catalogo')
            catalog = self.service.get_catalogo_by_id(id_catalogo)
            
            if not catalog:
                return Response({
                    'success': False,
                    'error': 'Catálogo não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(catalog)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """
        Update a catalog (full update).
        """
        try:
            id_catalogo = kwargs.get('id_catalogo')
            
            catalog = self.service.update_catalogo(id_catalogo, request.data)
            
            if not catalog:
                return Response({
                    'success': False,
                    'error': 'Catálogo não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(catalog)
            
            return Response({
                'success': True,
                'message': 'Catálogo atualizado com sucesso',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, *args, **kwargs):
        """
        Partial update of a catalog.
        """
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a catalog.
        """
        try:
            id_catalogo = kwargs.get('id_catalogo')
            
            deleted = self.service.delete_catalogo(id_catalogo)
            
            if not deleted:
                return Response({
                    'success': False,
                    'error': 'Catálogo não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'success': True,
                'message': 'Catálogo removido com sucesso'
            }, status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def total_count(self, request):
        """
        Get total count of catalogs.
        
        Query Parameters:
            - ativo: Filter by active status (true/false)
        """
        try:
            ativo = request.query_params.get('ativo')
            if ativo is not None:
                ativo = ativo.lower() == 'true'
            
            count = self.service.get_total_count(ativo=ativo)
            
            return Response({
                'success': True,
                'total': count
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def activate(self, request, id_catalogo=None):
        """
        Activate a catalog.
        """
        try:
            catalog = self.service.activate_catalogo(id_catalogo)
            
            if not catalog:
                return Response({
                    'success': False,
                    'error': 'Catálogo não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(catalog)
            
            return Response({
                'success': True,
                'message': 'Catálogo ativado com sucesso',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, id_catalogo=None):
        """
        Deactivate a catalog.
        """
        try:
            catalog = self.service.deactivate_catalogo(id_catalogo)
            
            if not catalog:
                return Response({
                    'success': False,
                    'error': 'Catálogo não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(catalog)
            
            return Response({
                'success': True,
                'message': 'Catálogo desativado com sucesso',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
