from typing import List, Optional

from django.db.models import Q

from .models import DePara


class DeparaRepository:
    """
    Repository layer for DePara model.
    
    Encapsulates all database operations related to DePara.
    Implements the repository pattern to abstract database access.
    """

    @staticmethod
    def create(data: dict) -> DePara:
        """
        Create a new DePara record.
        
        Args:
            data: Dictionary containing depara data
            
        Returns:
            Created DePara instance
        """
        return DePara.objects.create(**data)

    @staticmethod
    def get_by_id(id_depara: int) -> Optional[DePara]:
        """
        Get a DePara record by ID.
        
        Args:
            id_depara: Primary key of the depara
            
        Returns:
            DePara instance or None if not found
        """
        try:
            return DePara.objects.select_related('id_catalogo').get(id_depara=id_depara)
        except DePara.DoesNotExist:
            return None

    @staticmethod
    def get_all(filters: Optional[dict] = None) -> List[DePara]:
        """
        Get all DePara records with optional filters.
        
        Args:
            filters: Dictionary with optional filter criteria
            
        Returns:
            List of DePara instances
        """
        queryset = DePara.objects.select_related('id_catalogo').all()
        
        if filters:
            if 'ativo' in filters:
                queryset = queryset.filter(ativo=filters['ativo'])
            
            if 'id_catalogo' in filters:
                queryset = queryset.filter(id_catalogo=filters['id_catalogo'])
            
            if 'codigo_origem' in filters:
                queryset = queryset.filter(
                    codigo_origem__icontains=filters['codigo_origem']
                )
            
            if 'codigo_destino' in filters:
                queryset = queryset.filter(
                    codigo_destino__icontains=filters['codigo_destino']
                )
            
            if 'search' in filters:
                queryset = queryset.filter(
                    Q(codigo_origem__icontains=filters['search']) |
                    Q(codigo_destino__icontains=filters['search']) |
                    Q(descricao_origem__icontains=filters['search']) |
                    Q(descricao_destino__icontains=filters['search'])
                )
        
        return list(queryset.order_by('-criado_em'))

    @staticmethod
    def update(id_depara: int, data: dict) -> Optional[DePara]:
        """
        Update an existing DePara record.
        
        Args:
            id_depara: Primary key of the depara to update
            data: Dictionary containing fields to update
            
        Returns:
            Updated DePara instance or None if not found
        """
        depara = DeparaRepository.get_by_id(id_depara)
        
        if not depara:
            return None
        
        for key, value in data.items():
            if hasattr(depara, key) and key != 'id_depara':
                setattr(depara, key, value)
        
        depara.save()
        return depara

    @staticmethod
    def delete(id_depara: int) -> bool:
        """
        Delete a DePara record.
        
        Args:
            id_depara: Primary key of the depara to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            depara = DePara.objects.get(id_depara=id_depara)
            depara.delete()
            return True
        except DePara.DoesNotExist:
            return False

    @staticmethod
    def count(filters: Optional[dict] = None) -> int:
        """
        Count total DePara records.
        
        Args:
            filters: Optional filter criteria
            
        Returns:
            Total count of records
        """
        queryset = DePara.objects.all()
        
        if filters:
            if 'ativo' in filters:
                queryset = queryset.filter(ativo=filters['ativo'])
            
            if 'id_catalogo' in filters:
                queryset = queryset.filter(id_catalogo=filters['id_catalogo'])
        
        return queryset.count()

    @staticmethod
    def get_by_catalogo(id_catalogo: int) -> List[DePara]:
        """
        Get all DePara records for a specific catalog.
        
        Args:
            id_catalogo: ID of the catalog
            
        Returns:
            List of DePara instances
        """
        return list(
            DePara.objects
            .select_related('id_catalogo')
            .filter(id_catalogo=id_catalogo)
            .order_by('-criado_em')
        )

    @staticmethod
    def exists_mapping(
        id_catalogo: int,
        codigo_origem: str,
        codigo_destino: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Check if a mapping already exists.
        
        Args:
            id_catalogo: ID of the catalog
            codigo_origem: Origin code
            codigo_destino: Destination code
            exclude_id: Optional ID to exclude from check (for updates)
            
        Returns:
            True if mapping exists, False otherwise
        """
        query = DePara.objects.filter(
            id_catalogo=id_catalogo,
            codigo_origem=codigo_origem,
            codigo_destino=codigo_destino
        )
        
        if exclude_id:
            query = query.exclude(id_depara=exclude_id)
        
        return query.exists()
