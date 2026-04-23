from typing import List, Optional
from django.db.models import Q
from .entity import CatalogoDePara


class CatalogoDeparaRepository:
    """
    Repository layer for CatalogoDePara model.
    
    Encapsulates all database operations related to CatalogoDePara.
    Implements the repository pattern to abstract database access.
    """

    @staticmethod
    def create(data: dict) -> CatalogoDePara:
        """
        Create a new CatalogoDePara record.
        
        Args:
            data: Dictionary containing catalogo_depara data
            
        Returns:
            Created CatalogoDePara instance
        """
        return CatalogoDePara.objects.create(**data)

    @staticmethod
    def get_by_id(id_catalogo: int) -> Optional[CatalogoDePara]:
        """
        Get a CatalogoDePara record by ID.
        
        Args:
            id_catalogo: Primary key of the catalog
            
        Returns:
            CatalogoDePara instance or None if not found
        """
        try:
            return CatalogoDePara.objects.get(id_catalogo=id_catalogo)
        except CatalogoDePara.DoesNotExist:
            return None

    @staticmethod
    def get_all(filters: Optional[dict] = None) -> List[CatalogoDePara]:
        """
        Get all CatalogoDePara records with optional filters.
        
        Args:
            filters: Dictionary with optional filter criteria
            
        Returns:
            List of CatalogoDePara instances
        """
        queryset = CatalogoDePara.objects.all()
        
        if filters:
            if 'ativo' in filters:
                queryset = queryset.filter(ativo=filters['ativo'])
            
            if 'tabela_origem' in filters:
                queryset = queryset.filter(
                    tabela_origem__icontains=filters['tabela_origem']
                )
            
            if 'search' in filters:
                queryset = queryset.filter(
                    Q(tabela_origem__icontains=filters['search']) |
                    Q(descricao__icontains=filters['search'])
                )
        
        return list(queryset.order_by('-criado_em'))

    @staticmethod
    def update(id_catalogo: int, data: dict) -> Optional[CatalogoDePara]:
        """
        Update an existing CatalogoDePara record.
        
        Args:
            id_catalogo: Primary key of the catalog to update
            data: Dictionary containing fields to update
            
        Returns:
            Updated CatalogoDePara instance or None if not found
        """
        catalog = CatalogoDeparaRepository.get_by_id(id_catalogo)
        
        if not catalog:
            return None
        
        for key, value in data.items():
            if hasattr(catalog, key) and key != 'id_catalogo':
                setattr(catalog, key, value)
        
        catalog.save()
        return catalog

    @staticmethod
    def delete(id_catalogo: int) -> bool:
        """
        Delete a CatalogoDePara record.
        
        Args:
            id_catalogo: Primary key of the catalog to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            catalog = CatalogoDePara.objects.get(id_catalogo=id_catalogo)
            catalog.delete()
            return True
        except CatalogoDePara.DoesNotExist:
            return False

    @staticmethod
    def count(filters: Optional[dict] = None) -> int:
        """
        Count total CatalogoDePara records.
        
        Args:
            filters: Optional filter criteria
            
        Returns:
            Total count of records
        """
        queryset = CatalogoDePara.objects.all()
        
        if filters:
            if 'ativo' in filters:
                queryset = queryset.filter(ativo=filters['ativo'])
        
        return queryset.count()
