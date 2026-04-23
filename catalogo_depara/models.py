"""Django compatibility wrapper.

The actual domain/entity definitions live in `catalogo_depara.entity`.
This module keeps imports and migrations stable (they expect `catalogo_depara.models`).
"""

from .entity import CatalogoDePara

__all__ = ["CatalogoDePara"]
