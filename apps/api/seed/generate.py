"""Cenario de referencia do predio.

108 salas em 9 andares, 8 setores somando 7.000 funcionarios e 87 equipes
somando ~4.000 pessoas.

**Por que 4.000 e nao 7.000:** o enunciado diz que a empresa tem 7.000
funcionarios e (no exemplo da secao 12) 87 equipes contra 108 salas. As duas
coisas juntas dariam equipes de 80 pessoas em media contra salas de no maximo
130 -- o cenario nasceria inviavel e o motor so saberia dizer "nao coube". As
87 equipes aqui sao o subconjunto que precisa de espaco alocado; o total de
7.000 continua registrado em `Setor.total_funcionarios`, como manda a secao 5.

**Determinismo (AC-7):** tudo sai de um `random.Random(seed)` local. Nunca o
`random` global (estado compartilhado entre chamadas) e nunca iteracao sobre
`set` (ordem varia entre processos). O teste `test_seed.py` compara dois
snapshots gerados com a mesma seed e falha se um unico campo divergir.

A calibragem final -- quantas equipes ficam sem sala no cenario de referencia --
so pode ser verificada no D2, quando o solver existir.
"""

import argparse
import random

from sqlmodel import Session, select

from app.db import engine, reset_db
from app.enums import AlvoRestricao, Recurso, TipoRestricao, TipoSala, Turno
from app.models import Equipe, Restricao, Sala, Setor

ANDARES = 9
SALAS_POR_ANDAR = 12

#: Faixas de capacidade: Pequena, Media, Grande, eXtra Grande.
FAIXAS = {"P": (8, 20), "M": (25, 50), "G": (55, 90), "XG": (100, 130)}

#: Planta padrao de um andar: 4 pequenas, 4 medias, 3 grandes, 1 auditorio.
PLANTA_PADRAO: list[tuple[TipoSala, str]] = [
    (TipoSala.REUNIAO, "P"),
    (TipoSala.REUNIAO, "P"),
    (TipoSala.REUNIAO, "P"),
    (TipoSala.REUNIAO, "P"),
    (TipoSala.PROJETO, "M"),
    (TipoSala.PROJETO, "M"),
    (TipoSala.COLABORATIVO, "M"),
    (TipoSala.TREINAMENTO, "M"),
    (TipoSala.TREINAMENTO, "G"),
    (TipoSala.COLABORATIVO, "G"),
    (TipoSala.COLABORATIVO, "G"),
    (TipoSala.AUDITORIO, "XG"),
]

#: Laboratorios existem so nos andares 8 e 9, dois em cada. Sao escassos de
#: proposito: e o recurso que o cenario de estresse disputa.
ANDARES_COM_LABORATORIO = (8, 9)

RECURSOS_POR_TIPO: dict[TipoSala, list[str]] = {
    TipoSala.REUNIAO: [Recurso.PROJETOR, Recurso.VIDEOCONFERENCIA],
    TipoSala.TREINAMENTO: [Recurso.PROJETOR, Recurso.QUADRO_INTERATIVO],
    TipoSala.AUDITORIO: [Recurso.PROJETOR, Recurso.PALCO, Recurso.VIDEOCONFERENCIA],
    TipoSala.LABORATORIO: [Recurso.BANCADA_TECNICA, Recurso.QUADRO_INTERATIVO],
    TipoSala.PROJETO: [Recurso.QUADRO_INTERATIVO],
    TipoSala.COLABORATIVO: [Recurso.ILHAS_COLABORATIVAS, Recurso.QUADRO_INTERATIVO],
}

#: (nome, coordenador, funcionarios, equipes). Funcionarios somam 7.000 e
#: equipes somam 87.
SETORES: list[tuple[str, str, int, int]] = [
    ("Tecnologia", "Marina Alcantara", 1600, 20),
    ("Operacoes", "Rogerio Bastos", 1400, 16),
    ("Comercial", "Helena Truffi", 1100, 13),
    ("Pesquisa e Desenvolvimento", "Ivo Sampaio", 1000, 12),
    ("Financeiro", "Clara Nakamura", 600, 8),
    ("Marketing", "Diego Ferraz", 500, 7),
    ("Recursos Humanos", "Beatriz Lousada", 500, 6),
    ("Juridico", "Antonio Vilela", 300, 5),
]

#: Sufixos de nome de equipe, usados em ordem fixa por setor.
SUFIXOS = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta",
    "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi",
    "Rho", "Sigma", "Tau", "Upsilon",
]


def _capacidade(rng: random.Random, faixa: str) -> int:
    minimo, maximo = FAIXAS[faixa]
    # Arredonda para multiplo de 2: capacidade de sala e numero redondo na vida real.
    return rng.randrange(minimo, maximo + 1, 2)


def _planta(andar: int) -> list[tuple[TipoSala, str]]:
    planta = list(PLANTA_PADRAO)
    if andar in ANDARES_COM_LABORATORIO:
        # Troca as duas salas de projeto por laboratorios.
        planta[4] = (TipoSala.LABORATORIO, "M")
        planta[5] = (TipoSala.LABORATORIO, "M")
    return planta


def gerar_salas(rng: random.Random) -> list[Sala]:
    salas: list[Sala] = []
    for andar in range(1, ANDARES + 1):
        for indice, (tipo, faixa) in enumerate(_planta(andar), start=1):
            capacidade = _capacidade(rng, faixa)
            recursos = list(RECURSOS_POR_TIPO[tipo])
            # Salas pequenas nem sempre tem todos os recursos do tipo.
            if faixa == "P" and rng.random() < 0.45:
                recursos = recursos[:1]
            salas.append(
                Sala(
                    codigo=f"{andar}{indice:02d}",
                    andar=andar,
                    capacidade=capacidade,
                    tipo=tipo,
                    recursos=[str(r) for r in recursos],
                    # Andares baixos sao mais acessiveis; auditorios sempre sao.
                    acessivel=tipo is TipoSala.AUDITORIO or rng.random() < (0.6 - andar * 0.04),
                    # ~4% do predio em manutencao a qualquer momento.
                    disponivel=rng.random() > 0.04,
                )
            )
    return salas


def gerar_setores() -> list[Setor]:
    return [
        Setor(nome=nome, coordenador=coord, total_funcionarios=funcs)
        for nome, coord, funcs, _ in SETORES
    ]


def _tamanho_equipe(rng: random.Random) -> int:
    """Mistura de tres perfis: 30% pequena, 40% media, 30% grande.

    Media esperada ~46 pessoas, o que da ~4.000 no total das 87 equipes contra
    ~4.800 assentos no predio -- apertado o suficiente para que a otimizacao
    tenha o que otimizar e algumas equipes fiquem de fora.
    """
    sorteio = rng.random()
    if sorteio < 0.30:
        return rng.randint(8, 22)
    if sorteio < 0.70:
        return rng.randint(25, 55)
    return rng.randint(60, 110)


def gerar_equipes(rng: random.Random, setores: list[Setor]) -> list[Equipe]:
    por_nome = {s.nome: s for s in setores}
    equipes: list[Equipe] = []

    for nome_setor, _, _, quantidade in SETORES:
        setor = por_nome[nome_setor]
        for i in range(quantidade):
            tamanho = _tamanho_equipe(rng)
            tipo_trabalho = rng.random()

            recursos: list[str] = []
            if tipo_trabalho < 0.18:
                recursos.append(str(Recurso.PROJETOR))
            if tipo_trabalho > 0.88:
                recursos.append(str(Recurso.VIDEOCONFERENCIA))
            # P&D e Tecnologia sao os setores que puxam laboratorio.
            if nome_setor in ("Pesquisa e Desenvolvimento", "Tecnologia") and rng.random() < 0.15:
                recursos.append(str(Recurso.BANCADA_TECNICA))

            turno_sorteio = rng.random()
            if turno_sorteio < 0.60:
                turno = Turno.INTEGRAL
            elif turno_sorteio < 0.80:
                turno = Turno.MANHA
            else:
                turno = Turno.TARDE

            equipes.append(
                Equipe(
                    setor_id=setor.id,
                    nome=f"{nome_setor.split()[0]} {SUFIXOS[i]}",
                    tamanho=tamanho,
                    turno=turno,
                    recursos_requeridos=recursos,
                    exige_acessibilidade=rng.random() < 0.12,
                    andar_preferido=rng.randint(1, 9) if rng.random() < 0.40 else None,
                    prioridade=rng.choices([1, 2, 3, 4, 5], weights=[1, 2, 4, 2, 1])[0],
                )
            )
    return equipes


def gerar_restricoes(
    rng: random.Random, setores: list[Setor], equipes: list[Equipe]
) -> list[Restricao]:
    """Restricoes do cenario de referencia.

    Poucas e legiveis de proposito: na demo o Coordenador Geral precisa
    conseguir ler cada uma e entender por que ela existe.
    """
    por_nome = {s.nome: s for s in setores}
    restricoes: list[Restricao] = []

    # H7 -- Juridico e Comercial nao dividem andar (confidencialidade contratual).
    restricoes.append(
        Restricao(
            tipo=TipoRestricao.SEPARACAO_SETORES,
            alvo_tipo=AlvoRestricao.GLOBAL,
            parametros={
                "setor_a": por_nome["Juridico"].id,
                "setor_b": por_nome["Comercial"].id,
            },
            rigida=True,
            descricao="Juridico e Comercial nao podem ocupar o mesmo andar.",
        )
    )

    # H5 -- P&D so nos andares dos laboratorios.
    restricoes.append(
        Restricao(
            tipo=TipoRestricao.ANDAR_PERMITIDO,
            alvo_tipo=AlvoRestricao.SETOR,
            alvo_id=por_nome["Pesquisa e Desenvolvimento"].id,
            parametros={"andares": [7, 8, 9]},
            rigida=True,
            descricao="Pesquisa e Desenvolvimento fica nos andares 7 a 9.",
        )
    )

    # H6 -- auditorio do 1o andar reservado a eventos institucionais de RH.
    restricoes.append(
        Restricao(
            tipo=TipoRestricao.SALA_RESERVADA,
            alvo_tipo=AlvoRestricao.SALA,
            parametros={"codigo_sala": "112", "setor_id": por_nome["Recursos Humanos"].id},
            rigida=True,
            descricao="Auditorio 112 reservado a Recursos Humanos.",
        )
    )

    # Flexiveis -- proximidade entre equipes que trabalham juntas.
    tecnologia = [e for e in equipes if e.nome.startswith("Tecnologia")]
    pesquisa = [e for e in equipes if e.nome.startswith("Pesquisa")]
    for a, b in [(tecnologia[0], tecnologia[1]), (tecnologia[2], pesquisa[0])]:
        restricoes.append(
            Restricao(
                tipo=TipoRestricao.PROXIMIDADE,
                alvo_tipo=AlvoRestricao.GLOBAL,
                parametros={"equipe_a": a.id, "equipe_b": b.id},
                rigida=False,
                peso=50,
                descricao=f"{a.nome} e {b.nome} trabalham juntas: manter proximas.",
            )
        )

    return restricoes


def gerar(session: Session, seed: int = 42) -> dict:
    """Popula a sessao com o cenario de referencia. Assume banco vazio."""
    rng = random.Random(seed)

    setores = gerar_setores()
    session.add_all(setores)
    session.commit()
    for s in setores:
        session.refresh(s)

    salas = gerar_salas(rng)
    session.add_all(salas)

    equipes = gerar_equipes(rng, setores)
    session.add_all(equipes)
    session.commit()
    for e in equipes:
        session.refresh(e)
    for s in salas:
        session.refresh(s)

    # A restricao de sala reservada referencia a sala pelo codigo, entao
    # precisa das salas ja persistidas.
    restricoes = gerar_restricoes(rng, setores, equipes)
    session.add_all(restricoes)
    session.commit()

    return resumo(session)


def resumo(session: Session) -> dict:
    salas = list(session.exec(select(Sala)).all())
    equipes = list(session.exec(select(Equipe)).all())
    setores = list(session.exec(select(Setor)).all())
    restricoes = list(session.exec(select(Restricao)).all())

    return {
        "salas": len(salas),
        "setores": len(setores),
        "equipes": len(equipes),
        "restricoes": len(restricoes),
        "capacidade_total": sum(s.capacidade for s in salas if s.disponivel),
        "pessoas_em_equipes": sum(e.tamanho for e in equipes),
        "funcionarios_declarados": sum(s.total_funcionarios for s in setores),
        "salas_indisponiveis": sum(1 for s in salas if not s.disponivel),
        "salas_acessiveis": sum(1 for s in salas if s.acessivel),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o cenario de referencia do predio.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--reset", action="store_true", help="derruba e recria o schema antes de popular"
    )
    args = parser.parse_args()

    if args.reset:
        reset_db()

    with Session(engine) as session:
        dados = gerar(session, seed=args.seed)

    print(f"Cenario de referencia gerado (seed={args.seed}):")
    for chave, valor in dados.items():
        print(f"  {chave:.<28} {valor}")


if __name__ == "__main__":
    main()
