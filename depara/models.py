"""Django compatibility wrapper.

The actual domain/entity definitions live in `depara.entity`.
This module keeps imports and migrations stable (they expect `depara.models`).
"""

from .entity import DePara

__all__ = ["DePara"]
