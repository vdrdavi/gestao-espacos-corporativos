"""Relacoes metamorficas MR-1 a MR-6.

O problema da secao 15 do enunciado: para dezenas de equipes, salas e
restricoes, ninguem sabe de antemao qual e a melhor configuracao possivel.
Sem oraculo, nao da para escrever `assert resultado == esperado`.

A saida e testar *relacoes* entre execucoes. Nao se afirma qual e a resposta
certa; afirma-se que, ao transformar a entrada de um jeito conhecido, a saida
tem que se mover numa direcao conhecida.

    MR-1  invariante: nenhuma alocacao excede capacidade                ok
    MR-2  adicionar uma sala => alocadas nao diminui                    ok
    MR-3  remover uma restricao => custo nao aumenta                    ok
    MR-4  renomear e embaralhar => metricas globais identicas           ok
    MR-5  duplicar predio e equipes => taxa de alocacao preservada      D6
    MR-6  diferencial: custo do CP-SAT <= custo do guloso               ok

**A armadilha que derruba estes testes.** MR-2, MR-3 e MR-6 comparam valores de
objetivo entre duas execucoes. Sob limite de tempo, o CP-SAT pode devolver uma
solucao FEASIBLE mas nao otima -- e ai a monotonicidade quebra *por timeout, e
nao por bug*, gerando um teste instavel que a equipe acaba desabilitando. Um
teste desabilitado nao protege nada.

As tres mitigacoes previstas no D1, todas em uso aqui:

  (a) `cenario()` gera problemas pequenos (<= 8 salas, <= 6 equipes), onde o
      solver prova otimalidade em milissegundos;
  (b) `_otimo()` pula o exemplo quando algum dos dois lados nao provou
      otimalidade, em vez de asserir sobre uma solucao truncada;
  (c) `hint=` passa a solucao da execucao original para a execucao transformada:
      ela ja e viavel no problema relaxado, entao o solver nunca comeca de um
      ponto pior que o que se quer comparar.
"""

import random
from dataclasses import replace

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.engine import baseline, solver
from app.engine.types import EquipeDTO, Problema, RestricaoDTO, SalaDTO, Solucao
from app.enums import Recurso, StatusRun, TipoRestricao, TipoSala, Turno

pytestmark = pytest.mark.metamorphic

RECURSOS = [str(r) for r in (Recurso.PROJETOR, Recurso.BANCADA_TECNICA)]
TIPOS = list(TipoSala)

#: Cenarios pequenos e um limite curto: se o solver precisar de mais de 2s aqui,
#: o problema e o modelo, nao a maquina. Ver mitigacao (a).
LIMITE = 2.0

CONFIGURACAO = settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


@st.composite
def cenario(draw, min_salas: int = 2, max_salas: int = 8, max_equipes: int = 6) -> Problema:
    """Gera um problema pequeno, mas com todos os ingredientes que importam.

    Capacidades e tamanhos se sobrepoem de proposito: se toda equipe coubesse em
    toda sala, o modelo nunca seria exercitado e a propriedade passaria por
    vacuidade.
    """
    quantidade_salas = draw(st.integers(min_salas, max_salas))
    salas = tuple(
        SalaDTO(
            id=i,
            codigo=f"S{i}",
            andar=draw(st.integers(1, 4)),
            capacidade=draw(st.integers(10, 60)),
            tipo=draw(st.sampled_from(TIPOS)),
            recursos=frozenset(draw(st.sets(st.sampled_from(RECURSOS), max_size=2))),
            acessivel=draw(st.booleans()),
            disponivel=True,
        )
        for i in range(1, quantidade_salas + 1)
    )
    quantidade_equipes = draw(st.integers(1, max_equipes))
    equipes = tuple(
        EquipeDTO(
            id=i,
            nome=f"Equipe {i}",
            setor_id=draw(st.integers(1, 3)),
            tamanho=draw(st.integers(5, 55)),
            turno=draw(st.sampled_from(list(Turno))),
            recursos_requeridos=frozenset(
                draw(st.sets(st.sampled_from(RECURSOS), max_size=1))
            ),
            exige_acessibilidade=draw(st.booleans()),
            andar_preferido=draw(st.one_of(st.none(), st.integers(1, 4))),
            prioridade=draw(st.integers(1, 5)),
        )
        for i in range(1, quantidade_equipes + 1)
    )
    return Problema(salas=salas, equipes=equipes, limite_segundos=LIMITE)


def _otimo(*solucoes: Solucao) -> None:
    """Mitigacao (b): so se compara custo entre execucoes provadamente otimas."""
    if any(s.status is not StatusRun.OPTIMAL for s in solucoes):
        pytest.skip("solver nao provou otimalidade no limite de tempo -- comparacao invalida")


def _com_restricoes(problema: Problema) -> Problema:
    """Acrescenta tres restricoes ao problema, uma de cada natureza."""
    equipes = problema.equipes
    restricoes = [
        RestricaoDTO(
            id=1,
            tipo=TipoRestricao.ANDAR_PERMITIDO,
            parametros={"andares": [1, 2]},
            rigida=True,
            alvo_id=equipes[0].id,
        )
    ]
    if len(equipes) >= 2:
        restricoes.append(
            RestricaoDTO(
                id=2,
                tipo=TipoRestricao.PROXIMIDADE,
                parametros={"equipe_a": equipes[0].id, "equipe_b": equipes[1].id},
                rigida=False,
                peso=50,
            )
        )
        restricoes.append(
            RestricaoDTO(
                id=3,
                tipo=TipoRestricao.SEPARACAO_SETORES,
                parametros={"setor_a": equipes[0].setor_id, "setor_b": equipes[-1].setor_id},
                rigida=False,
                peso=200,
            )
        )
    return Problema(
        salas=problema.salas,
        equipes=problema.equipes,
        restricoes=tuple(restricoes),
        pesos=problema.pesos,
        limite_segundos=LIMITE,
    )


# --------------------------------------------------------------------------
# MR-1 -- invariante de capacidade
# --------------------------------------------------------------------------


@CONFIGURACAO
@given(problema=cenario())
def test_mr1_capacidade_nunca_e_excedida(problema: Problema):
    """Invariante, verificado com cenarios gerados por Hypothesis.

    Se uma sala tem capacidade para 30, nenhuma recomendacao valida coloca 31
    pessoas nela -- para *qualquer* entrada, nao so para as que escrevemos.
    """
    solucao = solver.alocar(problema)
    salas = {s.id: s for s in problema.salas}
    equipes = {e.id: e for e in problema.equipes}

    for alocacao in solucao.alocacoes:
        assert equipes[alocacao.equipe_id].tamanho <= salas[alocacao.sala_id].capacidade


# --------------------------------------------------------------------------
# MR-2 -- expansao da capacidade
# --------------------------------------------------------------------------


@CONFIGURACAO
@given(problema=cenario(), capacidade=st.integers(20, 80))
def test_mr2_adicionar_sala_nao_reduz_equipes_alocadas(problema: Problema, capacidade: int):
    """Adicionar uma sala sem mudar mais nada so amplia o espaco de solucoes.

    Se o numero de equipes alocadas cair, ha dependencia de ordem ou o solver
    parou cedo demais.
    """
    antes = solver.alocar(problema)

    nova = SalaDTO(
        id=max(s.id for s in problema.salas) + 1,
        codigo="NOVA",
        andar=1,
        capacidade=capacidade,
        tipo=TipoSala.COLABORATIVO,
        recursos=frozenset(RECURSOS),
        acessivel=True,
        disponivel=True,
    )
    ampliado = Problema(
        salas=problema.salas + (nova,),
        equipes=problema.equipes,
        restricoes=problema.restricoes,
        pesos=problema.pesos,
        limite_segundos=LIMITE,
    )
    depois = solver.alocar(ampliado, hint=antes)  # mitigacao (c)

    _otimo(antes, depois)
    assert len(depois.alocacoes) >= len(antes.alocacoes)
    assert depois.custo <= antes.custo, "mais espaco nao pode custar mais caro"


# --------------------------------------------------------------------------
# MR-3 -- remocao de restricao
# --------------------------------------------------------------------------


@CONFIGURACAO
@given(problema=cenario())
def test_mr3_remover_restricao_nao_aumenta_o_custo(problema: Problema):
    """Remover uma restricao relaxa o problema; o otimo nao pode piorar."""
    restrito = _com_restricoes(problema)
    com_todas = solver.alocar(restrito)

    relaxado = Problema(
        salas=restrito.salas,
        equipes=restrito.equipes,
        restricoes=restrito.restricoes[1:],  # sai a rigida de andar permitido
        pesos=restrito.pesos,
        limite_segundos=LIMITE,
    )
    com_uma_a_menos = solver.alocar(relaxado, hint=com_todas)  # mitigacao (c)

    _otimo(com_todas, com_uma_a_menos)
    assert com_uma_a_menos.custo <= com_todas.custo


# --------------------------------------------------------------------------
# MR-4 -- renomear e embaralhar
# --------------------------------------------------------------------------


@CONFIGURACAO
@given(problema=cenario(), semente=st.integers(0, 10_000))
def test_mr4_renomear_e_embaralhar_nao_muda_as_metricas(problema: Problema, semente: int):
    """O teste que mais encontra bug de verdade.

    Duas equipes com exatamente os mesmos requisitos nao podem produzir
    solucoes de qualidade diferente so porque tem nomes diferentes ou chegaram
    em outra ordem. Qualquer dependencia de ordem de iteracao -- um dict
    percorrido sem ordenacao, um desempate por indice -- aparece aqui.

    **O que se pode renomear.** Só o nome da equipe. O *codigo* da sala nao e
    rotulo inerte: a restricao SALA_RESERVADA do cenario de referencia aponta a
    sala por `codigo_sala`, entao renomear salas muda o problema em vez de
    disfarça-lo -- e o teste acusaria uma diferenca que e da transformacao, nao
    do motor. Foi o que aconteceu na primeira versao deste teste.
    """
    rng = random.Random(semente)
    salas = list(problema.salas)
    equipes = list(problema.equipes)
    rng.shuffle(salas)
    rng.shuffle(equipes)

    disfarcado = Problema(
        salas=tuple(replace(s, codigo=f"Sala-{rng.random():.6f}") for s in salas),
        equipes=tuple(replace(e, nome=f"Equipe-{rng.random():.6f}") for e in equipes),
        restricoes=problema.restricoes,
        pesos=problema.pesos,
        limite_segundos=LIMITE,
    )

    original = solver.alocar(problema)
    embaralhado = solver.alocar(disfarcado)

    _otimo(original, embaralhado)
    assert original.custo == embaralhado.custo
    assert original.metricas(problema) == embaralhado.metricas(disfarcado)


def test_mr4_no_cenario_de_referencia(cenario_referencia_montado):
    """O mesmo MR-4 onde ele tem mais chance de encontrar algo.

    Nos cenarios gerados o otimo costuma ser unico, e uma dependencia de ordem
    passaria despercebida por falta de empates. Com 87 equipes e 108 salas os
    empates existem aos montes -- e um desempate que dependa da ordem de chegada
    aparece aqui.
    """
    rng = random.Random(7)
    salas = list(cenario_referencia_montado.salas)
    equipes = list(cenario_referencia_montado.equipes)
    rng.shuffle(salas)
    rng.shuffle(equipes)

    disfarcado = Problema(
        salas=tuple(salas),  # embaralhadas, mas com os codigos intactos: ver acima
        equipes=tuple(replace(e, nome=f"Equipe-{rng.random():.6f}") for e in equipes),
        restricoes=cenario_referencia_montado.restricoes,
        pesos=cenario_referencia_montado.pesos,
        limite_segundos=cenario_referencia_montado.limite_segundos,
    )

    original = solver.alocar(cenario_referencia_montado)
    embaralhado = solver.alocar(disfarcado)

    _otimo(original, embaralhado)
    assert original.custo == embaralhado.custo
    assert original.metricas(cenario_referencia_montado) == embaralhado.metricas(disfarcado)


# --------------------------------------------------------------------------
# MR-5 -- escala
# --------------------------------------------------------------------------


@pytest.mark.skip(reason="D6 -- cenario grande, marcado slow")
def test_mr5_duplicar_o_problema_preserva_a_taxa_de_alocacao():
    """Dobrar predio e equipes mantem taxa de alocacao e ocupacao (+- 2 p.p.)."""


# --------------------------------------------------------------------------
# MR-6 -- diferencial contra o guloso
# --------------------------------------------------------------------------


@CONFIGURACAO
@given(problema=cenario())
def test_mr6_solver_nunca_perde_para_o_guloso(problema: Problema):
    """Teste diferencial: o baseline e o oraculo que o projeto tem.

    Nao se sabe qual e a solucao otima, mas sabe-se que o CP-SAT nao pode ser
    pior que o first-fit ingenuo. Cobre o AC-5 pelo lado do motor.

    A comparacao so e legitima porque o guloso tambem respeita H1-H8: restricao
    violada e restricao que nao custa nada, e um baseline invalido teria custo
    artificialmente menor.
    """
    guloso = baseline.alocar(problema)
    otimizado = solver.alocar(problema, hint=guloso)

    _otimo(otimizado)
    assert otimizado.custo <= guloso.custo
