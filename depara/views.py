from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import DePara
from .serializers import DeparaSerializer, DeparaListSerializer, DeparaDetailSerializer
from .service import DeparaService


class DeparaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing DePara entities.
    
    Provides CRUD operations through REST API endpoints.
    Implements the controller layer handling HTTP requests/responses.
    """
    
    queryset = DePara.objects.all()
    serializer_class = DeparaSerializer
    lookup_field = 'id_depara'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = DeparaService()

    def get_serializer_class(self):
        """
        Return the appropriate serializer class based on the action.
        """
        if self.action == 'list':
            return DeparaListSerializer
        elif self.action == 'retrieve':
            return DeparaDetailSerializer
        return DeparaSerializer

    def list(self, request, *args, **kwargs):
        """
        List all depara records with optional filters.
        
        Query Parameters:
            - id_catalogo: Filter by catalog ID
            - ativo: Filter by active status (true/false)
            - codigo_origem: Filter by origin code
            - codigo_destino: Filter by destination code
            - search: Search in multiple fields
        """
        try:
            id_catalogo = request.query_params.get('id_catalogo')
            ativo = request.query_params.get('ativo')
            if ativo is not None:
                ativo = ativo.lower() == 'true'
            
            codigo_origem = request.query_params.get('codigo_origem')
            codigo_destino = request.query_params.get('codigo_destino')
            search = request.query_params.get('search')
            
            depara_list = self.service.list_depara(
                id_catalogo=int(id_catalogo) if id_catalogo else None,
                ativo=ativo,
                codigo_origem=codigo_origem,
                codigo_destino=codigo_destino,
                search=search
            )
            
            serializer = self.get_serializer(depara_list, many=True)
            
            return Response({
                'success': True,
                'count': len(depara_list),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        """
        Create a new depara mapping.
        """
        try:
            depara = self.service.create_depara(request.data)
            serializer = self.get_serializer(depara)
            
            return Response({
                'success': True,
                'message': 'Mapeamento DePara criado com sucesso',
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
        Retrieve a specific depara mapping by ID.
        """
        try:
            id_depara = kwargs.get('id_depara')
            depara = self.service.get_depara_by_id(id_depara)
            
            if not depara:
                return Response({
                    'success': False,
                    'error': 'Mapeamento DePara não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(depara)
            
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
        Update a depara mapping (full update).
        """
        try:
            id_depara = kwargs.get('id_depara')
            
            depara = self.service.update_depara(id_depara, request.data)
            
            if not depara:
                return Response({
                    'success': False,
                    'error': 'Mapeamento DePara não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(depara)
            
            return Response({
                'success': True,
                'message': 'Mapeamento DePara atualizado com sucesso',
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
        Partial update of a depara mapping.
        """
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a depara mapping.
        """
        try:
            id_depara = kwargs.get('id_depara')
            
            deleted = self.service.delete_depara(id_depara)
            
            if not deleted:
                return Response({
                    'success': False,
                    'error': 'Mapeamento DePara não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'success': True,
                'message': 'Mapeamento DePara removido com sucesso'
            }, status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def total_count(self, request):
        """
        Get total count of depara records.
        
        Query Parameters:
            - id_catalogo: Filter by catalog ID
            - ativo: Filter by active status (true/false)
        """
        try:
            id_catalogo = request.query_params.get('id_catalogo')
            ativo = request.query_params.get('ativo')
            if ativo is not None:
                ativo = ativo.lower() == 'true'
            
            count = self.service.get_total_count(
                id_catalogo=int(id_catalogo) if id_catalogo else None,
                ativo=ativo
            )
            
            return Response({
                'success': True,
                'total': count
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def by_catalogo(self, request):
        """
        Get all depara mappings for a specific catalog.
        
        Query Parameters:
            - id_catalogo: Catalog ID (required)
        """
        try:
            id_catalogo = request.query_params.get('id_catalogo')
            
            if not id_catalogo:
                return Response({
                    'success': False,
                    'error': 'id_catalogo é obrigatório'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            depara_list = self.service.get_by_catalogo(int(id_catalogo))
            serializer = self.get_serializer(depara_list, many=True)
            
            return Response({
                'success': True,
                'count': len(depara_list),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def activate(self, request, id_depara=None):
        """
        Activate a depara mapping.
        """
        try:
            depara = self.service.activate_depara(id_depara)
            
            if not depara:
                return Response({
                    'success': False,
                    'error': 'Mapeamento DePara não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(depara)
            
            return Response({
                'success': True,
                'message': 'Mapeamento DePara ativado com sucesso',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, id_depara=None):
        """
        Deactivate a depara mapping.
        """
        try:
            depara = self.service.deactivate_depara(id_depara)
            
            if not depara:
                return Response({
                    'success': False,
                    'error': 'Mapeamento DePara não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.get_serializer(depara)
            
            return Response({
                'success': True,
                'message': 'Mapeamento DePara desativado com sucesso',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
