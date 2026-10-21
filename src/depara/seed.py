"""Catálogos e mapeamentos De/Para de demonstração.

Os códigos são genéricos (unidades de medida, status e tipos de atendimento) e não
correspondem a dados de nenhum cliente. O seed só cria registros quando ainda não
existe nenhum catálogo, então não altera nada que já tenha sido cadastrado.
"""

from catalogo_depara.models import CatalogoDePara
from depara.models import DePara


# (codigo_origem, descricao_origem, codigo_destino, descricao_destino, filhos)
CATALOGOS = [
    {
        "tabela_origem": "produtos.unidade",
        "descricao": "Unidades de medida do sistema de origem",
        "mapeamentos": [
            ("UN", "Unidade", "UNIDADE", "Unidade", []),
            ("CX", "Caixa", "CAIXA", "Caixa", []),
            ("KG", "Quilograma", "QUILOGRAMA", "Quilograma", []),
            ("RL", "Rolo", "ROLO", "Rolo", []),
            ("PR", "Par", "PAR", "Par", []),
            ("LT", "Lata", "LATA", "Lata", []),
        ],
    },
    {
        "tabela_origem": "pedidos.status",
        "descricao": "Situação dos pedidos de venda",
        "mapeamentos": [
            ("P", "Pago", "PAGO", "Pago", []),
            ("PE", "Pendente", "PENDENTE", "Pendente", []),
            ("C", "Cancelado", "CANCELADO", "Cancelado", []),
        ],
    },
    {
        "tabela_origem": "atendimentos.tipo",
        "descricao": "Tipos de atendimento de convênio",
        "mapeamentos": [
            ("CON", "Consulta", "CONSULTA", "Consulta médica", []),
            (
                "EXA", "Exame", "EXAME", "Exame",
                [("EXA-LAB", "Exame laboratorial", "EXAME_LABORATORIAL", "Exame laboratorial")],
            ),
            ("TER", "Terapia", "TERAPIA", "Terapia", []),
            ("INT", "Internação", "INTERNACAO", "Internação", []),
        ],
    },
]


def seed_demo_depara() -> bool:
    """Cria catálogos e mapeamentos De/Para. Não altera nada se já houver catálogos."""
    if CatalogoDePara.objects.exists():
        return False

    for info in CATALOGOS:
        catalogo = CatalogoDePara.objects.create(
            tabela_origem=info["tabela_origem"],
            descricao=info["descricao"],
        )
        for origem, desc_origem, destino, desc_destino, filhos in info["mapeamentos"]:
            pai = DePara.objects.create(
                id_catalogo=catalogo,
                codigo_origem=origem,
                descricao_origem=desc_origem,
                codigo_destino=destino,
                descricao_destino=desc_destino,
            )
            for filho_origem, filho_desc_origem, filho_destino, filho_desc_destino in filhos:
                DePara.objects.create(
                    id_catalogo=catalogo,
                    id_depara_pai=pai,
                    codigo_origem=filho_origem,
                    descricao_origem=filho_desc_origem,
                    codigo_destino=filho_destino,
                    descricao_destino=filho_desc_destino,
                )
    return True
