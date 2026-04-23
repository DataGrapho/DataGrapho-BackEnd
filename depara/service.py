from typing import List, Optional

from django.db import transaction

from .models import DePara
from .repository import DeparaRepository


class DeparaService:
    """
    Service layer for DePara entity.
    
    Encapsulates business logic and orchestrates between
    the controller and repository layers.
    """

    def __init__(self):
        self.repository = DeparaRepository()

    @transaction.atomic
    def create_depara(self, data: dict) -> DePara:
        """
        Create a new depara mapping with business logic validation.
        
        Args:
            data: Dictionary containing depara data
            
        Returns:
            Created DePara instance
            
        Raises:
            ValueError: If validation fails
        """
        # Validate required fields
        if not data.get('id_catalogo'):
            raise ValueError('id_catalogo é obrigatório')
        
        if not data.get('codigo_origem'):
            raise ValueError('codigo_origem é obrigatório')
        
        if not data.get('codigo_destino'):
            raise ValueError('codigo_destino é obrigatório')
        
        # Validate codes format
        if len(data['codigo_origem'].strip()) == 0:
            raise ValueError('codigo_origem não pode estar vazia')
        
        if len(data['codigo_destino'].strip()) == 0:
            raise ValueError('codigo_destino não pode estar vazia')
        
        # Check for duplicate mapping
        if self.repository.exists_mapping(
            data['id_catalogo'].id_catalogo if hasattr(data['id_catalogo'], 'id_catalogo') else data['id_catalogo'],
            data['codigo_origem'],
            data['codigo_destino']
        ):
            raise ValueError('Mapeamento já existe para este catálogo')
        
        # Set default values
        if 'ativo' not in data:
            data['ativo'] = True
        
        # Create the depara
        depara = self.repository.create(data)
        
        return depara

    def get_depara_by_id(self, id_depara: int) -> Optional[DePara]:
        """
        Get a depara by its ID.
        
        Args:
            id_depara: ID of the depara
            
        Returns:
            DePara instance or None
        """
        return self.repository.get_by_id(id_depara)

    def list_depara(
        self,
        id_catalogo: Optional[int] = None,
        ativo: Optional[bool] = None,
        codigo_origem: Optional[str] = None,
        codigo_destino: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[DePara]:
        """
        List all depara records with optional filtering.
        
        Args:
            id_catalogo: Filter by catalog ID
            ativo: Filter by active status
            codigo_origem: Filter by origin code
            codigo_destino: Filter by destination code
            search: Search in multiple fields
            
        Returns:
            List of DePara instances
        """
        filters = {}
        
        if id_catalogo is not None:
            filters['id_catalogo'] = id_catalogo
        
        if ativo is not None:
            filters['ativo'] = ativo
        
        if codigo_origem:
            filters['codigo_origem'] = codigo_origem
        
        if codigo_destino:
            filters['codigo_destino'] = codigo_destino
        
        if search:
            filters['search'] = search
        
        return self.repository.get_all(filters)

    @transaction.atomic
    def update_depara(self, id_depara: int, data: dict) -> Optional[DePara]:
        """
        Update an existing depara record.
        
        Args:
            id_depara: ID of the depara to update
            data: Dictionary with fields to update
            
        Returns:
            Updated DePara instance or None if not found
            
        Raises:
            ValueError: If validation fails
        """
        depara = self.repository.get_by_id(id_depara)
        
        if not depara:
            return None
        
        # Validate codes if they're being updated
        if 'codigo_origem' in data:
            if not data['codigo_origem'] or len(data['codigo_origem'].strip()) == 0:
                raise ValueError('codigo_origem não pode estar vazia')
        
        if 'codigo_destino' in data:
            if not data['codigo_destino'] or len(data['codigo_destino'].strip()) == 0:
                raise ValueError('codigo_destino não pode estar vazia')
        
        # Check for duplicate mapping if codes are being changed
        if 'codigo_origem' in data or 'codigo_destino' in data:
            codigo_origem = data.get('codigo_origem', depara.codigo_origem)
            codigo_destino = data.get('codigo_destino', depara.codigo_destino)
            id_catalogo = data.get('id_catalogo', depara.id_catalogo)
            
            catalogo_id = id_catalogo.id_catalogo if hasattr(id_catalogo, 'id_catalogo') else id_catalogo
            
            if self.repository.exists_mapping(
                catalogo_id,
                codigo_origem,
                codigo_destino,
                exclude_id=id_depara
            ):
                raise ValueError('Mapeamento já existe para este catálogo')
        
        updated_depara = self.repository.update(id_depara, data)
        
        return updated_depara

    @transaction.atomic
    def delete_depara(self, id_depara: int) -> bool:
        """
        Delete a depara record.
        
        Args:
            id_depara: ID of the depara to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        return self.repository.delete(id_depara)

    def get_total_count(
        self,
        id_catalogo: Optional[int] = None,
        ativo: Optional[bool] = None
    ) -> int:
        """
        Get total count of depara records.
        
        Args:
            id_catalogo: Optional filter by catalog ID
            ativo: Optional filter by active status
            
        Returns:
            Total count
        """
        filters = {}
        if id_catalogo is not None:
            filters['id_catalogo'] = id_catalogo
        if ativo is not None:
            filters['ativo'] = ativo
        
        return self.repository.count(filters)

    def get_by_catalogo(self, id_catalogo: int) -> List[DePara]:
        """
        Get all depara records for a specific catalog.
        
        Args:
            id_catalogo: ID of the catalog
            
        Returns:
            List of DePara instances
        """
        return self.repository.get_by_catalogo(id_catalogo)

    def activate_depara(self, id_depara: int) -> Optional[DePara]:
        """
        Activate a depara record.
        
        Args:
            id_depara: ID of the depara
            
        Returns:
            Updated depara or None if not found
        """
        return self.update_depara(id_depara, {'ativo': True})

    def deactivate_depara(self, id_depara: int) -> Optional[DePara]:
        """
        Deactivate a depara record.
        
        Args:
            id_depara: ID of the depara
            
        Returns:
            Updated depara or None if not found
        """
        return self.update_depara(id_depara, {'ativo': False})
