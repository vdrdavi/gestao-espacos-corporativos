"""Criterios de aceitacao AC-1 a AC-8.

Este arquivo e o *gate* do CI: e ele que define quando uma recomendacao pode
ser considerada aceitavel. O enunciado pede pelo menos cinco criterios
objetivos (secao 14); sao oito.

Estado no D3: sete dos oito criterios rodam de verdade.
Os que ainda nao existem seguem marcados com o dia em que entram -- aparecem como
*skipped* no relatorio, nao como verdes. Um gate que passa por vacuidade e pior
que nenhum gate.

    AC-1  nenhuma sala recebe mais pessoas que sua capacidade          ok
    AC-2  nenhuma restricao rigida e ignorada                          ok
    AC-3  toda recomendacao tem justificativa                          ok
    AC-4  toda equipe nao alocada tem motivo registrado                ok
    AC-5  a otimizacao nao e pior que o baseline                       ok
    AC-6  recomendacao dentro do limite de tempo (p95 <= 10s)          D6
    AC-7  execucao reproduzivel                                        ok
    AC-8  toda execucao e auditavel                                    ok

AC-1 a AC-5 rodam nos quatro cenarios do catalogo, nao so no de referencia: e
nos tres de estresse que uma implementacao apressada e tentada a esconder o
problema para melhorar o proprio indicador.
"""

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.engine import baseline, diagnostics, explainer, solver, validator
from app.engine.custo import avaliar
from app.engine.types import Pesos, Problema
from app.enums import CodigoMotivo
from app.models import Run
from app.problema import hash_entrada, montar_problema, montar_snapshot
from seed.cenarios import CENARIOS
from seed.generate import gerar

pytestmark = pytest.mark.acceptance

#: Os quatro cenarios do catalogo. Os tres de estresse sao pequenos e rodam em
#: milissegundos -- incluir todos custa pouco e cobre o que interessa.
CENARIOS_DO_GATE = list(CENARIOS)


def _sessao() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _sessao_com_predio(seed: int = 42) -> Session:
    session = _sessao()
    gerar(session, seed=seed)
    return session


def _problema_do_cenario(nome: str) -> Problema:
    with _sessao() as session:
        CENARIOS[nome].aplicar(session)
        return montar_problema(session)


# --------------------------------------------------------------------------
# AC-1 -- capacidade
# --------------------------------------------------------------------------


@pytest.mark.parametrize("cenario", CENARIOS_DO_GATE)
def test_ac1_nenhuma_alocacao_excede_a_capacidade(cenario):
    """Para todo assignment: tamanho(equipe) <= capacidade(sala).

    Verificado nos tres cenarios de estresse alem do de referencia.
    """
    problema = _problema_do_cenario(cenario)
    solucao = solver.alocar(problema)

    salas = {s.id: s for s in problema.salas}
    equipes = {e.id: e for e in problema.equipes}

    for alocacao in solucao.alocacoes:
        equipe, sala = equipes[alocacao.equipe_id], salas[alocacao.sala_id]
        assert equipe.tamanho <= sala.capacidade, (
            f"{cenario}: equipe {equipe.nome} ({equipe.tamanho} pessoas) na sala "
            f"{sala.codigo} de capacidade {sala.capacidade}"
        )


# --------------------------------------------------------------------------
# AC-2 -- restricoes rigidas
# --------------------------------------------------------------------------


@pytest.mark.parametrize("cenario", CENARIOS_DO_GATE)
def test_ac2_nenhuma_restricao_rigida_e_violada(cenario):
    """`validator.violacoes()` devolve lista vazia.

    O validador e codigo independente do solver de proposito: se o mesmo
    codigo que monta as restricoes tambem as verifica, um erro de modelagem
    passa pelos dois lados.
    """
    problema = _problema_do_cenario(cenario)
    achadas = validator.violacoes(problema, solver.alocar(problema))

    assert achadas == [], f"{cenario}: {len(achadas)} violacoes, primeira: {achadas[:1]}"


@pytest.mark.parametrize("cenario", CENARIOS_DO_GATE)
def test_ac2_o_baseline_tambem_passa_no_validador(cenario):
    """A comparacao do AC-5 so vale entre duas solucoes validas.

    Restricao violada e restricao que nao custa nada: um guloso que violasse
    restricoes teria custo artificialmente baixo, e "a otimizacao nao e pior que
    o baseline" deixaria de significar o que diz.
    """
    problema = _problema_do_cenario(cenario)

    assert validator.violacoes(problema, baseline.alocar(problema)) == []


# --------------------------------------------------------------------------
# AC-3 / AC-4 -- explicabilidade e rastreabilidade das falhas
# --------------------------------------------------------------------------


@pytest.mark.parametrize("cenario", CENARIOS_DO_GATE)
def test_ac3_toda_recomendacao_tem_justificativa(cenario):
    """100% dos assignments com `explicacao` preenchida e >= 1 alternativa avaliada.

    "Preenchida" nao e "nao vazia": o criterio cobra os campos que a secao 9 do
    enunciado manda mostrar na tela -- a conta decomposta, o total, as salas
    consideradas e o paragrafo que o Coordenador Geral le.
    """
    problema = _problema_do_cenario(cenario)
    solucao = solver.alocar(problema)
    explicadas = explainer.explicar(problema, solucao)

    assert len(explicadas) == len(solucao.alocacoes), cenario
    for alocacao in explicadas:
        explicacao = alocacao.explicacao
        assert explicacao, f"{cenario}: equipe {alocacao.equipe_id} sem explicacao"
        assert explicacao["resumo"].strip()
        assert explicacao["termos"], "a conta tem que aparecer termo a termo"
        assert explicacao["comparacao"]["detalhe"].strip()
        # Conta a sala escolhida: e o numero de opcoes que o motor pontuou, e por
        # isso nunca e zero numa recomendacao que existe.
        assert explicacao["alternativas_avaliadas"] >= 1


@pytest.mark.parametrize("cenario", CENARIOS_DO_GATE)
def test_ac3_o_custo_da_explicacao_e_o_custo_que_o_solver_minimizou(cenario):
    """A justificativa tem que somar a mesma conta do modelo, nao uma parecida.

    Cada termo mostrado e a diferenca que aquela equipe naquela sala faz no custo
    total (`custo.custo_marginal`). Aqui isso e cobrado contra `custo.avaliar` --
    a formula de docs/objetivo.md -- removendo a equipe da solucao e medindo o
    que sobra. Sem este teste a tela poderia exibir numeros plausiveis que nao
    sao a razao da decisao, e nada no sistema perceberia.
    """
    problema = _problema_do_cenario(cenario)
    solucao = solver.alocar(problema)
    total = avaliar(problema, solucao.alocacoes)
    equipes = {e.id: e for e in problema.equipes}

    for alocacao in explainer.explicar(problema, solucao):
        sem_ela = tuple(a for a in solucao.alocacoes if a.equipe_id != alocacao.equipe_id)
        # Tirar a equipe da solucao troca o custo dela pelo W_NA de nao aloca-la.
        marginal = (
            total
            - avaliar(problema, sem_ela)
            + problema.pesos.nao_alocada * equipes[alocacao.equipe_id].prioridade
        )

        assert alocacao.explicacao["custo_total"] == marginal, (
            f"{cenario}: a explicacao da equipe {alocacao.equipe_id} nao bate com "
            f"a funcao de custo"
        )
        assert sum(t["valor"] for t in alocacao.explicacao["termos"]) == marginal


def test_ac3_a_alternativa_descartada_e_uma_sala_real_e_mais_cara():
    """Nao vale listar qualquer sala: a alternativa tem que ser comparavel.

    Sem isto, "5 alternativas avaliadas" passaria no AC-3 listando salas onde a
    equipe nem caberia -- e a explicacao viraria enfeite. O cenario de referencia
    e o da demonstracao, e e nele que a pergunta e feita.
    """
    problema = _problema_do_cenario("referencia")
    solucao = solver.alocar(problema)
    salas = {s.id: s for s in problema.salas}
    equipes = {e.id: e for e in problema.equipes}

    com_alternativa = 0
    for alocacao in explainer.explicar(problema, solucao):
        equipe = equipes[alocacao.equipe_id]
        for alternativa in alocacao.alternativas:
            sala = salas[alternativa["sala_id"]]
            assert equipe.tamanho <= sala.capacidade, "alternativa onde a equipe nao cabe"
            assert equipe.recursos_requeridos <= sala.recursos
            assert alternativa["por_que_nao"].strip()

        # Da mais barata para a mais cara: e assim que a tela e lida.
        custos = [a["custo"] for a in alocacao.alternativas]
        assert custos == sorted(custos)
        com_alternativa += bool(alocacao.alternativas)

    assert com_alternativa > 0, "nenhuma recomendacao mostrou o que foi descartado"


def test_ac3_a_explicacao_admite_quando_a_sala_escolhida_nao_e_a_mais_barata():
    """O CP-SAT otimiza o predio, nao esta equipe -- e a explicacao tem que dizer.

    As vezes uma equipe paga mais caro para que outra caiba melhor. Afirmar
    "esta e a melhor sala" nesse caso seria mentir num campo que existe
    justamente para tornar a decisao auditavel. Este teste cobra que, sempre que
    uma alternativa livre custa menos, a comparacao assuma o trade-off em vez de
    reivindicar otimalidade local.
    """
    problema = _problema_do_cenario("referencia")
    solucao = solver.alocar(problema)

    for alocacao in explainer.explicar(problema, solucao):
        livres = [a for a in alocacao.alternativas if a["disponivel"]]
        mais_barata = min((a["delta"] for a in livres), default=0)
        tipo = alocacao.explicacao["comparacao"]["tipo"]

        if mais_barata < 0:
            assert tipo == "trade_off_global", (
                f"equipe {alocacao.equipe_id}: existe sala livre {mais_barata} mais "
                f"barata, mas a explicacao se declarou '{tipo}'"
            )
        else:
            assert tipo in ("melhor_local", "sem_alternativa")


@pytest.mark.parametrize("cenario", CENARIOS_DO_GATE)
def test_ac4_toda_equipe_nao_alocada_tem_motivo(cenario):
    """100% das nao alocadas com codigo_motivo, causa e encaminhamento."""
    problema = _problema_do_cenario(cenario)
    solucao = solver.alocar(problema)
    rejeitadas = diagnostics.diagnosticar(problema, solucao)

    sem_sala = {e.id for e in problema.equipes} - {a.equipe_id for a in solucao.alocacoes}
    assert {r.equipe_id for r in rejeitadas} == sem_sala, cenario

    for rejeicao in rejeitadas:
        assert rejeicao.codigo_motivo in CodigoMotivo
        assert rejeicao.causa.strip(), f"{cenario}: equipe {rejeicao.equipe_id} sem causa"
        assert rejeicao.encaminhamento.strip()


def test_ac4_o_diagnostico_aponta_a_regra_que_resolveria():
    """O criterio nao se satisfaz com "nao coube".

    O cenario `estresse-recurso-escasso` tem salas grandes de sobra e a causa
    real e a bancada tecnica que elas nao tem. Um diagnostico que respondesse
    "capacidade" estaria formalmente completo e materialmente errado -- e o AC-4
    passaria mesmo assim. Este teste cobra a resposta certa e acionavel: qual
    regra, removida, resolveria.
    """
    problema = _problema_do_cenario("estresse-recurso-escasso")
    rejeitadas = diagnostics.diagnosticar(problema, solver.alocar(problema))

    assert rejeitadas, "o cenario de estresse deveria deixar equipes de fora"
    for rejeicao in rejeitadas:
        assert rejeicao.codigo_motivo is CodigoMotivo.RECURSO_INDISPONIVEL
        # A frase do relaxamento cita a sala concreta que abriria; a classificacao
        # estatica do solver nao tem como citar sala nenhuma.
        assert "caberia na sala" in rejeicao.causa
        assert "Concretamente" in rejeicao.encaminhamento


# --------------------------------------------------------------------------
# AC-5 -- ganho sobre a linha de base
# --------------------------------------------------------------------------


@pytest.mark.parametrize("cenario", CENARIOS_DO_GATE)
def test_ac5_otimizacao_nao_e_pior_que_o_baseline(cenario):
    """Ocupacao >= baseline E assentos ociosos <= baseline E alocadas >= baseline.

    E a resposta para "como voces sabem que uma nova versao nao piorou a
    solucao?" -- nenhuma versao passa no gate se ficar abaixo do guloso.
    """
    problema = _problema_do_cenario(cenario)
    guloso = baseline.alocar(problema).metricas(problema)
    otimizado = solver.alocar(problema).metricas(problema)

    assert otimizado["equipes_alocadas"] >= guloso["equipes_alocadas"], cenario
    assert otimizado["assentos_ociosos"] <= guloso["assentos_ociosos"], cenario
    assert otimizado["ocupacao_media_pct"] >= guloso["ocupacao_media_pct"], cenario


def test_ac5_no_cenario_de_referencia_o_ganho_e_visivel():
    """A tela de comparacao precisa ter o que mostrar.

    Empatar com o guloso satisfaz a desigualdade acima e ainda assim significaria
    que a otimizacao nao serviu para nada. Este teste cobra ganho real no cenario
    da demo -- e e ele que quebra se uma mudanca futura degradar a solucao sem
    chegar a piora-la.
    """
    problema = _problema_do_cenario("referencia")
    guloso = baseline.alocar(problema).metricas(problema)
    otimizado = solver.alocar(problema).metricas(problema)

    assert otimizado["equipes_alocadas"] > guloso["equipes_alocadas"]
    assert otimizado["assentos_ociosos"] < guloso["assentos_ociosos"] * 0.75


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


def test_ac7_mesma_entrada_produz_as_mesmas_metricas():
    """Mesmo hash + mesma seed + mesmos pesos => metricas globais identicas.

    Duas sessoes independentes com a mesma seed: se o motor dependesse de ordem
    de dicionario, de id de objeto ou do numero de workers do CP-SAT, e aqui que
    apareceria.
    """
    with _sessao_com_predio(seed=42) as a, _sessao_com_predio(seed=42) as b:
        problema_a, problema_b = montar_problema(a), montar_problema(b)
        assert hash_entrada(montar_snapshot(a)) == hash_entrada(montar_snapshot(b))

        primeira = solver.alocar(problema_a)
        segunda = solver.alocar(problema_b)

    assert primeira.custo == segunda.custo
    assert primeira.metricas(problema_a) == segunda.metricas(problema_b)
    assert primeira.alocacoes == segunda.alocacoes


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
