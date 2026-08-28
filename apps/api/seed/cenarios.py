"""Catalogo de cenarios.

Alem do cenario de referencia, tres cenarios de estresse pequenos e legiveis.
Eles nao existem para testar carga -- existem porque a secao 11 do enunciado
(tratamento de excecoes) e avaliada, e demonstrar "o que acontece quando nao ha
solucao possivel" ao vivo exige um caso onde a resposta certa e conhecida de
antemao.

Cada um cabe em uma tela: poucas salas, poucas equipes, uma unica causa de
falha. Na demo da para ler o cenario inteiro em voz alta antes de rodar.
"""

from collections.abc import Callable
from dataclasses import dataclass

from sqlmodel import Session, delete

from app.enums import AlvoRestricao, Recurso, TipoRestricao, TipoSala, Turno
from app.models import (
    Assignment,
    Equipe,
    Intervencao,
    NaoAlocada,
    Restricao,
    Run,
    Sala,
    Setor,
)
from seed.generate import gerar, resumo


def limpar(session: Session) -> None:
    """Apaga todas as linhas na ordem segura para as chaves estrangeiras.

    Deleta linhas em vez de derrubar tabelas (DDL) de proposito: a sessao do
    request esta aberta, e drop_all/create_all no meio dela e uma boa forma de
    ganhar um lock do SQLite em producao local.
    """
    for modelo in (Intervencao, Assignment, NaoAlocada, Run, Restricao, Equipe, Sala, Setor):
        session.execute(delete(modelo))
    session.commit()


# --------------------------------------------------------------------------
# Cenario de referencia
# --------------------------------------------------------------------------


def aplicar_referencia(session: Session, seed: int = 42) -> dict:
    limpar(session)
    return gerar(session, seed=seed)


# --------------------------------------------------------------------------
# Estresse 1 -- equipe maior que a maior sala
# --------------------------------------------------------------------------


def aplicar_superdimensionada(session: Session, seed: int = 42) -> dict:
    """Reproduz literalmente o exemplo da secao 11.

    Equipe Delta tem 92 funcionarios; a maior sala do predio comporta 80.
    Resultado esperado: ALERTA com codigo SEM_SALA_COMPATIVEL.
    """
    limpar(session)

    setor = Setor(nome="Operacoes", coordenador="Rogerio Bastos", total_funcionarios=200)
    session.add(setor)
    session.commit()
    session.refresh(setor)

    session.add_all(
        [
            Sala(codigo="401", andar=4, capacidade=80, tipo=TipoSala.TREINAMENTO, acessivel=True),
            Sala(codigo="402", andar=4, capacidade=60, tipo=TipoSala.TREINAMENTO),
            Sala(codigo="403", andar=4, capacidade=40, tipo=TipoSala.REUNIAO),
            Sala(codigo="404", andar=4, capacidade=20, tipo=TipoSala.REUNIAO),
        ]
    )
    session.add_all(
        [
            Equipe(setor_id=setor.id, nome="Operacoes Delta", tamanho=92, prioridade=5),
            Equipe(setor_id=setor.id, nome="Operacoes Alpha", tamanho=55, prioridade=3),
            Equipe(setor_id=setor.id, nome="Operacoes Beta", tamanho=38, prioridade=3),
            Equipe(setor_id=setor.id, nome="Operacoes Gamma", tamanho=18, prioridade=2),
        ]
    )
    session.commit()

    return resumo(session) | {
        "esperado": "Operacoes Delta (92) nao alocada -- maior sala comporta 80."
    }


# --------------------------------------------------------------------------
# Estresse 2 -- mais demanda por laboratorio do que laboratorios
# --------------------------------------------------------------------------


def aplicar_recurso_escasso(session: Session, seed: int = 42) -> dict:
    """Cinco equipes exigem bancada tecnica; existem tres laboratorios.

    As salas comuns tem capacidade de sobra, entao a causa da falha nao pode
    ser capacidade -- tem que sair RECURSO_INDISPONIVEL. E o teste de que o
    diagnostico aponta a restricao certa, e nao a primeira que encontrar.
    """
    limpar(session)

    setor = Setor(
        nome="Pesquisa e Desenvolvimento", coordenador="Ivo Sampaio", total_funcionarios=150
    )
    session.add(setor)
    session.commit()
    session.refresh(setor)

    bancada = [str(Recurso.BANCADA_TECNICA)]
    session.add_all(
        [
            Sala(codigo="801", andar=8, capacidade=40, tipo=TipoSala.LABORATORIO, recursos=bancada),
            Sala(codigo="802", andar=8, capacidade=40, tipo=TipoSala.LABORATORIO, recursos=bancada),
            Sala(codigo="901", andar=9, capacidade=40, tipo=TipoSala.LABORATORIO, recursos=bancada),
            # Capacidade de sobra, mas sem o recurso exigido.
            Sala(codigo="803", andar=8, capacidade=90, tipo=TipoSala.COLABORATIVO),
            Sala(codigo="804", andar=8, capacidade=90, tipo=TipoSala.COLABORATIVO),
        ]
    )
    session.add_all(
        [
            Equipe(
                setor_id=setor.id,
                nome=f"Pesquisa {sufixo}",
                tamanho=30,
                recursos_requeridos=bancada,
                prioridade=4,
            )
            for sufixo in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon")
        ]
    )
    session.commit()

    return resumo(session) | {
        "esperado": "2 das 5 equipes sem sala -- motivo RECURSO_INDISPONIVEL, nao capacidade."
    }


# --------------------------------------------------------------------------
# Estresse 3 -- restricoes mutuamente insatisfazeis
# --------------------------------------------------------------------------


def aplicar_conflito_restricoes(session: Session, seed: int = 42) -> dict:
    """Duas restricoes rigidas que nao podem valer ao mesmo tempo.

    A equipe Alpha so pode ficar no andar 3, a Beta so no andar 7, e uma
    restricao de proximidade *rigida* exige que fiquem no mesmo andar.
    Nao ha solucao -- e o sistema tem que dizer isso apontando o conflito, em
    vez de simplesmente devolver menos alocacoes sem explicacao.
    """
    limpar(session)

    setor = Setor(nome="Tecnologia", coordenador="Marina Alcantara", total_funcionarios=120)
    session.add(setor)
    session.commit()
    session.refresh(setor)

    session.add_all(
        [
            Sala(codigo="301", andar=3, capacidade=40, tipo=TipoSala.PROJETO),
            Sala(codigo="302", andar=3, capacidade=35, tipo=TipoSala.PROJETO),
            Sala(codigo="701", andar=7, capacidade=40, tipo=TipoSala.PROJETO),
            Sala(codigo="702", andar=7, capacidade=35, tipo=TipoSala.PROJETO),
        ]
    )

    alpha = Equipe(
        setor_id=setor.id, nome="Tecnologia Alpha", tamanho=30, turno=Turno.INTEGRAL, prioridade=4
    )
    beta = Equipe(
        setor_id=setor.id, nome="Tecnologia Beta", tamanho=30, turno=Turno.INTEGRAL, prioridade=4
    )
    session.add_all([alpha, beta])
    session.commit()
    session.refresh(alpha)
    session.refresh(beta)

    session.add_all(
        [
            Restricao(
                tipo=TipoRestricao.ANDAR_PERMITIDO,
                alvo_tipo=AlvoRestricao.EQUIPE,
                alvo_id=alpha.id,
                parametros={"andares": [3]},
                rigida=True,
                descricao="Tecnologia Alpha so pode ocupar o andar 3.",
            ),
            Restricao(
                tipo=TipoRestricao.ANDAR_PERMITIDO,
                alvo_tipo=AlvoRestricao.EQUIPE,
                alvo_id=beta.id,
                parametros={"andares": [7]},
                rigida=True,
                descricao="Tecnologia Beta so pode ocupar o andar 7.",
            ),
            Restricao(
                tipo=TipoRestricao.PROXIMIDADE,
                alvo_tipo=AlvoRestricao.GLOBAL,
                parametros={"equipe_a": alpha.id, "equipe_b": beta.id, "mesmo_andar": True},
                rigida=True,
                descricao="Alpha e Beta devem ficar no mesmo andar (rigida).",
            ),
        ]
    )
    session.commit()

    return resumo(session) | {
        "esperado": "Insatisfazivel -- motivo CONFLITO_RESTRICOES apontando andar x proximidade."
    }


# --------------------------------------------------------------------------
# Catalogo
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Cenario:
    nome: str
    titulo: str
    descricao: str
    aplicar: Callable[..., dict]


CENARIOS: dict[str, Cenario] = {
    c.nome: c
    for c in (
        Cenario(
            nome="referencia",
            titulo="Predio completo",
            descricao="108 salas em 9 andares, 8 setores, 87 equipes. O cenario da demo.",
            aplicar=aplicar_referencia,
        ),
        Cenario(
            nome="estresse-superdimensionada",
            titulo="Equipe maior que a maior sala",
            descricao="Equipe de 92 pessoas contra uma sala maxima de 80. Espera-se ALERTA.",
            aplicar=aplicar_superdimensionada,
        ),
        Cenario(
            nome="estresse-recurso-escasso",
            titulo="Laboratorios insuficientes",
            descricao="Cinco equipes exigem bancada tecnica e existem tres laboratorios.",
            aplicar=aplicar_recurso_escasso,
        ),
        Cenario(
            nome="estresse-conflito-restricoes",
            titulo="Restricoes contraditorias",
            descricao="Andar permitido e proximidade rigida mutuamente insatisfazeis.",
            aplicar=aplicar_conflito_restricoes,
        ),
    )
}
