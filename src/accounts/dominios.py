"""Regras de acesso aos domínios de dados da IA.

Uma concessão (`DominioAcesso`) vale para o alvo e para tudo abaixo dele. O usuário
enxerga a união de tudo o que recebeu pelas empresas, filiais, setores e pelo próprio
cadastro em que tem acesso ativo. Não há exceções de retirada em níveis descendentes.
"""

from __future__ import annotations

from typing import Iterable

from django.conf import settings
from django.db import models
from django.db.models import Q

from accounts.models import (
    DominioAcesso,
    Empresa,
    Filial,
    Setor,
    Usuario,
    UsuarioAcesso,
)


NOMES_DOMINIO = {
    "wine": "Vinhos",
    "convenio": "Convênio médico",
    "vendas": "Vendas e pedidos",
    "estoque": "Estoque",
}


def dominios_ativos() -> list[str]:
    """Domínios configurados no chatbot (CHATBOT_ACTIVE_DOMAINS)."""
    return [d for d in settings.CHATBOT_CONFIG.get("ACTIVE_DOMAINS", []) if d]


def nome_dominio(chave: str) -> str:
    return NOMES_DOMINIO.get(chave, chave)


def _concessoes(empresa_ids: Iterable[int], filial_ids: Iterable[int], setor_ids: Iterable[int], usuario_id=None):
    filtro = Q(empresa_id__in=list(empresa_ids)) | Q(filial_id__in=list(filial_ids)) | Q(setor_id__in=list(setor_ids))
    if usuario_id is not None:
        filtro |= Q(usuario_id=usuario_id)
    return DominioAcesso.objects.filter(filtro)


def dominios_do_usuario(user) -> set[str]:
    """Domínios que o usuário pode consultar pelo chat."""
    if user.is_superuser:
        return set(dominios_ativos())

    acessos = UsuarioAcesso.objects.filter(usuario=user, ativo=True)
    concedidos = _concessoes(
        empresa_ids=acessos.values_list("empresa_id", flat=True),
        filial_ids=acessos.exclude(filial__isnull=True).values_list("filial_id", flat=True),
        setor_ids=acessos.exclude(setor__isnull=True).values_list("setor_id", flat=True),
        usuario_id=user.pk,
    )
    ativos = set(dominios_ativos())
    return {d for d in concedidos.values_list("dominio", flat=True) if d in ativos}


def ids_administrados(user) -> set[int]:
    """Empresas que o administrador pode gerenciar. Superusuário não usa esta lista."""
    return set(
        UsuarioAcesso.objects.filter(usuario=user, ativo=True).values_list("empresa_id", flat=True)
    )


def pode_gerenciar(user, nivel: str, alvo) -> bool:
    """Indica se o administrador pode conceder ou retirar acesso ao alvo informado."""
    if user.is_superuser:
        return True
    empresas = ids_administrados(user)
    if not empresas:
        return False
    if nivel == "empresa":
        return alvo.pk in empresas
    if nivel == "filial":
        return alvo.empresa_id in empresas
    if nivel == "setor":
        return alvo.filial.empresa_id in empresas
    if nivel == "usuario":
        return alvo.acessos.filter(empresa_id__in=empresas).exists()
    return False


def concessoes_herdadas(nivel: str, alvo) -> list[dict]:
    """Concessões de níveis acima que já cobrem o alvo, com a origem de cada uma."""
    if nivel == "empresa":
        return []

    if nivel == "filial":
        empresa_ids: list[int] = [alvo.empresa_id]
        filial_ids: list[int] = []
        setor_ids: list[int] = []
        usuario_id = None
    elif nivel == "setor":
        empresa_ids, filial_ids, setor_ids = [alvo.filial.empresa_id], [alvo.filial_id], []
        usuario_id = None
    else:  # usuario: herda de todas as empresas/filiais/setores em que tem acesso ativo
        acessos = UsuarioAcesso.objects.filter(usuario=alvo, ativo=True)
        empresa_ids = list(acessos.values_list("empresa_id", flat=True))
        filial_ids = list(acessos.exclude(filial__isnull=True).values_list("filial_id", flat=True))
        setor_ids = list(acessos.exclude(setor__isnull=True).values_list("setor_id", flat=True))
        usuario_id = None

    herdadas = []
    for concessao in _concessoes(empresa_ids, filial_ids, setor_ids, usuario_id).select_related(
        "empresa", "filial", "setor"
    ):
        origem = concessao.empresa or concessao.filial or concessao.setor
        herdadas.append({
            "dominio": concessao.dominio,
            "nivel": concessao.nivel,
            "origem": str(getattr(origem, "nome", origem)),
        })
    return herdadas


def concessoes_diretas(nivel: str, alvo) -> list[DominioAcesso]:
    return list(DominioAcesso.objects.filter(**{f"{nivel}_id": alvo.pk}).order_by("dominio"))


MODELOS_ALVO: dict[str, type[models.Model]] = {
    "empresa": Empresa,
    "filial": Filial,
    "setor": Setor,
    "usuario": Usuario,
}


def carregar_alvo(nivel: str, alvo_id: int):
    """Busca o objeto de um alvo de concessão, ou None se o nível ou o alvo não existirem."""
    modelo = MODELOS_ALVO.get(nivel)
    if modelo is None:
        return None
    return modelo.objects.filter(pk=alvo_id).first()
