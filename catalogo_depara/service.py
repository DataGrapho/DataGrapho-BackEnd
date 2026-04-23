from typing import List, Optional, Dict, Any
from django.db import transaction
from .entity import CatalogoDePara
from .repository import CatalogoDeparaRepository


class CatalogoDeparaService:
    """
    Service layer for CatalogoDePara entity.
    
    Encapsulates business logic and orchestrates between
    the controller and repository layers.
    """

    def __init__(self):
        self.repository = CatalogoDeparaRepository()

    @transaction.atomic
    def create_catalogo(self, data: dict) -> CatalogoDePara:
        """
        Create a new catalog with business logic validation.
        
        Args:
            data: Dictionary containing catalog data
            
        Returns:
            Created CatalogoDePara instance
            
        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        if not data.get('tabela_origem'):
            raise ValueError('tabela_origem é obrigatório')
        
        # Validate tabela_origem format
        if len(data['tabela_origem'].strip()) == 0:
            raise ValueError('tabela_origem não pode estar vazia')
        
        # Set default values
        if 'ativo' not in data:
            data['ativo'] = True
        
        # Create the catalog
        catalog = self.repository.create(data)
        
        return catalog

    def get_catalogo_by_id(self, id_catalogo: int) -> Optional[CatalogoDePara]:
        """
        Get a catalog by its ID.
        
        Args:
            id_catalogo: ID of the catalog
            
        Returns:
            CatalogoDePara instance or None
        """
        return self.repository.get_by_id(id_catalogo)

    def list_catalogos(
        self,
        ativo: Optional[bool] = None,
        tabela_origem: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[CatalogoDePara]:
        """
        List all catalogs with optional filtering.
        
        Args:
            ativo: Filter by active status
            tabela_origem: Filter by origin table name
            search: Search in multiple fields
            
        Returns:
            List of CatalogoDePara instances
        """
        filters = {}
        
        if ativo is not None:
            filters['ativo'] = ativo
        
        if tabela_origem:
            filters['tabela_origem'] = tabela_origem
        
        if search:
            filters['search'] = search
        
        return self.repository.get_all(filters)

    @transaction.atomic
    def update_catalogo(self, id_catalogo: int, data: dict) -> Optional[CatalogoDePara]:
        """
        Update an existing catalog.
        
        Args:
            id_catalogo: ID of the catalog to update
            data: Dictionary with fields to update
            
        Returns:
            Updated CatalogoDePara instance or None if not found
            
        Raises:
            ValueError: If validation fails
        """
        catalog = self.repository.get_by_id(id_catalogo)
        
        if not catalog:
            return None
        
        # Validate tabela_origem if it's being updated
        if 'tabela_origem' in data:
            if not data['tabela_origem'] or len(data['tabela_origem'].strip()) == 0:
                raise ValueError('tabela_origem não pode estar vazia')
        
        updated_catalog = self.repository.update(id_catalogo, data)
        
        return updated_catalog

    @transaction.atomic
    def delete_catalogo(self, id_catalogo: int) -> bool:
        """
        Delete a catalog.
        
        Args:
            id_catalogo: ID of the catalog to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        return self.repository.delete(id_catalogo)

    def get_total_count(self, ativo: Optional[bool] = None) -> int:
        """
        Get total count of catalogs.
        
        Args:
            ativo: Optional filter by active status
            
        Returns:
            Total count
        """
        filters = {}
        if ativo is not None:
            filters['ativo'] = ativo
        
        return self.repository.count(filters)

    def activate_catalogo(self, id_catalogo: int) -> Optional[CatalogoDePara]:
        """
        Activate a catalog.
        
        Args:
            id_catalogo: ID of the catalog
            
        Returns:
            Updated catalog or None if not found
        """
        return self.update_catalogo(id_catalogo, {'ativo': True})

    def deactivate_catalogo(self, id_catalogo: int) -> Optional[CatalogoDePara]:
        """
        Deactivate a catalog.
        
        Args:
            id_catalogo: ID of the catalog
            
        Returns:
            Updated catalog or None if not found
        """
        return self.update_catalogo(id_catalogo, {'ativo': False})
