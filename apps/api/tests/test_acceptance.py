"""Criterios de aceitacao AC-1 a AC-8.

Este arquivo e o *gate* do CI: e ele que define quando uma recomendacao pode
ser considerada aceitavel. O enunciado pede pelo menos cinco criterios
objetivos (secao 14); sao oito.

Estado no D1: AC-7 (reprodutibilidade da entrada) e AC-8 (auditabilidade) ja
rodam de verdade, porque nao dependem do motor. Os demais estao marcados com o
dia em que entram -- aparecem como *skipped* no relatorio, nao como verdes.
Um gate que passa por vacuidade e pior que nenhum gate.

    AC-1  nenhuma sala recebe mais pessoas que sua capacidade          D2
    AC-2  nenhuma restricao rigida e ignorada                          D2
    AC-3  toda recomendacao tem justificativa                          D3
    AC-4  toda equipe nao alocada tem motivo registrado                D3
    AC-5  a otimizacao nao e pior que o baseline                       D2
    AC-6  recomendacao dentro do limite de tempo (p95 <= 10s)          D6
    AC-7  execucao reproduzivel                                        D1 (parcial) / D2
    AC-8  toda execucao e auditavel                                    D1
"""

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.engine.types import Pesos
from app.models import Run
from app.problema import hash_entrada, montar_problema, montar_snapshot
from seed.generate import gerar

pytestmark = pytest.mark.acceptance


def _sessao_com_predio(seed: int = 42) -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    gerar(session, seed=seed)
    return session


# --------------------------------------------------------------------------
# AC-1 -- capacidade
# --------------------------------------------------------------------------


@pytest.mark.skip(reason="D2 -- depende do solver")
def test_ac1_nenhuma_alocacao_excede_a_capacidade():
    """Para todo assignment: tamanho(equipe) <= capacidade(sala).

    Verificado nos tres cenarios de estresse alem do de referencia.
    """


# --------------------------------------------------------------------------
# AC-2 -- restricoes rigidas
# --------------------------------------------------------------------------


@pytest.mark.skip(reason="D2 -- depende do validator independente")
def test_ac2_nenhuma_restricao_rigida_e_violada():
    """`validator.violacoes()` devolve lista vazia.

    O validador e codigo independente do solver de proposito: se o mesmo
    codigo que monta as restricoes tambem as verifica, um erro de modelagem
    passa pelos dois lados.
    """


# --------------------------------------------------------------------------
# AC-3 / AC-4 -- explicabilidade e rastreabilidade das falhas
# --------------------------------------------------------------------------


@pytest.mark.skip(reason="D3 -- depende do explainer")
def test_ac3_toda_recomendacao_tem_justificativa():
    """100% dos assignments com `explicacao` preenchida e >= 1 alternativa."""


@pytest.mark.skip(reason="D3 -- depende do diagnostics")
def test_ac4_toda_equipe_nao_alocada_tem_motivo():
    """100% das nao alocadas com codigo_motivo, causa e encaminhamento."""


# --------------------------------------------------------------------------
# AC-5 -- ganho sobre a linha de base
# --------------------------------------------------------------------------


@pytest.mark.skip(reason="D2 -- depende de baseline + solver")
def test_ac5_otimizacao_nao_e_pior_que_o_baseline():
    """Ocupacao >= baseline E assentos ociosos <= baseline E alocadas >= baseline.

    E a resposta para "como voces sabem que uma nova versao nao piorou a
    solucao?" -- nenhuma versao passa no gate se ficar abaixo do guloso.
    """


def test_ac5_pesos_padrao_respeitam_a_dominancia():
    """Pre-condicao do AC-5, verificavel sem o motor.

    Se `W_NA * prioridade_minima <= W_OC * capacidade_total`, deixar uma equipe
    de fora fica mais barato que aloca-la e o solver aprende a esconder
    equipes -- melhorando o custo e piorando a solucao. Este teste existe para
    que mexer nos pesos padrao sem pensar quebre o CI.
    """
    with _sessao_com_predio() as session:
        problema = montar_problema(session)

    assert Pesos().dominancia_ok(problema.capacidade_total), (
        f"pesos padrao nao dominam a capacidade total de {problema.capacidade_total} "
        "assentos -- ver docs/objetivo.md"
    )


# --------------------------------------------------------------------------
# AC-6 -- tempo
# --------------------------------------------------------------------------


@pytest.mark.skip(reason="D6 -- exige o motor estavel para medir p95")
def test_ac6_recomendacao_dentro_do_limite_de_tempo():
    """p95 <= 10s no cenario de referencia (108 salas / 87 equipes)."""


# --------------------------------------------------------------------------
# AC-7 -- reprodutibilidade
# --------------------------------------------------------------------------


def test_ac7_mesma_seed_produz_a_mesma_entrada():
    """Metade verificavel do AC-7 no D1.

    Se a entrada nao for reproduzivel, comparar duas execucoes -- na tela de
    "Antes x Depois" ou num teste metamorfico -- nao significa nada.
    """
    with _sessao_com_predio(seed=42) as a, _sessao_com_predio(seed=42) as b:
        assert hash_entrada(montar_snapshot(a)) == hash_entrada(montar_snapshot(b))


def test_ac7_o_hash_reage_a_qualquer_mudanca_na_entrada():
    """Um hash que nunca muda tambem passaria no teste acima."""
    from app.models import Sala

    with _sessao_com_predio(seed=42) as session:
        antes = hash_entrada(montar_snapshot(session))

        sala = session.get(Sala, 1)
        sala.capacidade += 1
        session.add(sala)
        session.commit()

        assert hash_entrada(montar_snapshot(session)) != antes


@pytest.mark.skip(reason="D2 -- exige metricas de uma execucao real")
def test_ac7_mesma_entrada_produz_as_mesmas_metricas():
    """Mesmo hash + mesma seed + mesmos pesos => metricas globais identicas."""


# --------------------------------------------------------------------------
# AC-8 -- auditabilidade
# --------------------------------------------------------------------------


def test_ac8_o_registro_de_execucao_responde_as_perguntas_da_governanca():
    """Secao 12: quem executou, quando, com quais dados, qual versao, qual resultado.

    Teste estrutural: cada pergunta tem que ter um campo obrigatorio que a
    responda. Remover um deles quebra o gate antes de chegar na demo.
    """
    campos = Run.model_fields

    for pergunta, campo in [
        ("quem executou", "usuario"),
        ("quando", "criado_em"),
        ("com quais dados", "hash_entrada"),
        ("com quais dados (integra)", "snapshot_entrada"),
        ("qual versao do mecanismo", "engine_version"),
        ("qual foi o resultado", "metricas"),
        ("quanto demorou", "duracao_ms"),
        ("com quais pesos", "pesos"),
    ]:
        assert campo in campos, f"Run nao consegue responder '{pergunta}': falta {campo}"


def test_ac8_execucoes_nao_podem_ser_editadas(client):
    """A trilha e append-only: nao existe rota de UPDATE nem DELETE sobre Run."""
    assert client.patch("/api/runs/1").status_code == 405
    assert client.delete("/api/runs/1").status_code == 405
