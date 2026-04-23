"""Django compatibility wrapper.

The actual domain/entity definitions live in `accounts.entity`.
This module keeps imports and migrations stable (they expect `accounts.models`).
"""

from .entity import (
    Empresa,
    Filial,
    Perfil,
    Setor,
    Usuario,
    UsuarioAcesso,
    UsuarioManager,
)

__all__ = [
    "UsuarioManager",
    "Empresa",
    "Filial",
    "Setor",
    "Perfil",
    "Usuario",
    "UsuarioAcesso",
]
