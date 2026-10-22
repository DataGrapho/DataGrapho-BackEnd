"""Estrutura organizacional fictícia para demonstração: empresas, filiais, setores e perfis.

Os CNPJs usam o prefixo 90.000.000, reservado para testes, e nenhum nome corresponde
a uma empresa real. Os dados são criados apenas quando ainda não existe nenhuma empresa.
"""

from accounts.models import Empresa, Filial, Perfil, Setor


PERFIS = [
    ("Administrador", "Acesso administrativo à organização"),
    ("Gestor", "Gestão da unidade e da equipe"),
    ("Analista", "Operação e análise de dados"),
    ("Médico", "Atendimento clínico"),
    ("Enfermeiro", "Atendimento e apoio clínico"),
    ("Atendente", "Recepção e atendimento ao público"),
]

# cnpj, nome, endereço, filiais: [(nome, endereço, setores)]
EMPRESAS = [
    (
        "90.000.000/0001-01",
        "Hospital Santa Clara",
        "Av. das Acácias, 1500 - Centro",
        [
            ("Unidade Centro", "Av. das Acácias, 1500 - Centro", ["Pronto-Socorro", "Laboratório", "Faturamento"]),
            ("Unidade Norte", "Rua das Palmeiras, 320 - Zona Norte", ["Ambulatório", "Recepção"]),
        ],
    ),
    (
        "90.000.000/0002-02",
        "Distribuidora Alfa Comércio",
        "Rua do Comércio, 800 - Brás",
        [
            ("Matriz São Paulo", "Rua do Comércio, 800 - Brás", ["Comercial", "Estoque", "Financeiro"]),
            ("Filial Curitiba", "Rua XV de Novembro, 45 - Centro", ["Comercial", "Expedição"]),
        ],
    ),
    (
        "90.000.000/0003-03",
        "Construtora Horizonte Ltda",
        "Av. Horizonte, 2200 - Jardim Paulista",
        [
            ("Sede", "Av. Horizonte, 2200 - Jardim Paulista", ["Engenharia", "Compras"]),
            ("Obra Litoral", "Rod. Litorânea, km 12", ["Almoxarifado"]),
        ],
    ),
    (
        "90.000.000/0004-04",
        "Logística Rota Sul",
        "Rod. BR-116, km 390 - Pinhais",
        [
            ("Centro de Distribuição Sul", "Rod. BR-116, km 390 - Pinhais", ["Recebimento", "Expedição", "Inventário"]),
        ],
    ),
]


def seed_demo_organizacao() -> bool:
    """Cria perfis, empresas, filiais e setores. Não altera nada se já houver empresas."""
    for nome, descricao in PERFIS:
        Perfil.objects.get_or_create(nome=nome, defaults={"descricao": descricao})

    if Empresa.objects.exists():
        return False

    for cnpj, nome, endereco, filiais in EMPRESAS:
        empresa = Empresa.objects.create(nome=nome, cnpj=cnpj, endereco=endereco)
        for nome_filial, endereco_filial, setores in filiais:
            filial = Filial.objects.create(empresa=empresa, nome=nome_filial, endereco=endereco_filial)
            for nome_setor in setores:
                Setor.objects.create(filial=filial, nome=nome_setor)
    return True


# Usuários de demonstração: três por empresa, com acesso no nível indicado.
# (papel, perfil, índice da filial, índice do setor ou None, é administrador)
PAPEIS_USUARIO = [
    ("admin", "Administrador", None, None, True),
    ("gestor", "Gestor", 0, None, False),
    ("operacional", None, 0, 0, False),
]

# Perfil do usuário operacional de cada empresa, na mesma ordem de EMPRESAS.
PERFIL_OPERACIONAL = ["Médico", "Analista", "Analista", "Atendente"]

NOMES_USUARIO = [
    "Mariana Alves", "Carlos Lima", "Beatriz Ferreira", "Rafael Santos",
    "Juliana Costa", "Lucas Oliveira", "Patrícia Nunes", "Felipe Rocha",
    "Camila Barbosa", "Gustavo Pereira", "Renata Dias", "Bruno Carvalho",
]


def _slug(texto: str) -> str:
    return (
        texto.lower()
        .replace(" ", "-")
        .replace("ç", "c").replace("ã", "a").replace("á", "a").replace("é", "e")
        .replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ê", "e")
        .replace("ô", "o").replace("â", "a").replace("à", "a")
    )


def seed_demo_usuarios(senha: str | None) -> int:
    """Cria três usuários de demonstração por empresa, somente se houver uma senha.

    Sem senha, nada é criado: contas com senha conhecida não devem existir em produção
    por padrão. Retorna quantos usuários foram criados.
    """
    if not senha:
        return 0

    from accounts.models import Usuario, UsuarioAcesso

    criados = 0
    for indice, (cnpj, nome_empresa, _endereco, _filiais) in enumerate(EMPRESAS):
        empresa = Empresa.objects.filter(cnpj=cnpj).first()
        if empresa is None:
            continue
        filiais_db = list(Filial.objects.filter(empresa=empresa).order_by("pk"))
        setores_db = list(Setor.objects.filter(filial=filiais_db[0]).order_by("pk")) if filiais_db else []

        for papel, perfil_nome, indice_filial, indice_setor, admin in PAPEIS_USUARIO:
            perfil_nome = perfil_nome or PERFIL_OPERACIONAL[indice]
            email = f"{papel}.{_slug(nome_empresa)}@demo.datagrapho.test"
            if Usuario.objects.filter(email=email).exists():
                continue

            numero = indice * 3 + ["admin", "gestor", "operacional"].index(papel)
            usuario = Usuario.objects.create_user(
                email=email,
                password=senha,
                cpf=f"900.000.{numero:03d}-{numero:02d}",
                nome=NOMES_USUARIO[numero],
            )
            if admin:
                usuario.is_staff = True
                usuario.save(update_fields=["is_staff"])

            filial = filiais_db[indice_filial] if indice_filial is not None else None
            setor = setores_db[indice_setor] if indice_setor is not None and setores_db else None
            UsuarioAcesso.objects.create(
                usuario=usuario,
                empresa=empresa,
                filial=filial,
                setor=setor,
                perfil=Perfil.objects.get(nome=perfil_nome),
            )
            criados += 1
    return criados
