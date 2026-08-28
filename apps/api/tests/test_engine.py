"""Testes de unidade do motor.

Os criterios de aceitacao (test_acceptance.py) e as relacoes metamorficas
(test_metamorphic.py) tratam o motor como caixa-preta e falam do resultado. Aqui
se verifica cada restricao isoladamente, em micro-cenarios escritos a mao onde a
resposta certa e obvia por inspecao -- e por isso um teste que falha aponta a
linha do modelo, e nao "a solucao piorou".

O par de cada teste e a tabela de H1-H8 em docs/objetivo.md.
"""

import pytest

from app.engine import baseline, diagnostics, explainer, solver, validator
from app.engine.custo import avaliar
from app.engine.types import EquipeDTO, Pesos, Problema, RestricaoDTO, SalaDTO
from app.enums import CodigoMotivo, StatusRun, TipoRestricao, TipoSala, Turno


def sala(id_: int, capacidade: int, **kwargs) -> SalaDTO:
    padrao = {
        "codigo": f"{id_:03d}",
        "andar": kwargs.pop("andar", 1),
        "tipo": TipoSala.REUNIAO,
    }
    return SalaDTO(id=id_, capacidade=capacidade, **padrao, **kwargs)


def equipe(id_: int, tamanho: int, **kwargs) -> EquipeDTO:
    return EquipeDTO(
        id=id_,
        nome=kwargs.pop("nome", f"Equipe {id_}"),
        setor_id=kwargs.pop("setor_id", 1),
        tamanho=tamanho,
        **kwargs,
    )


def problema(salas, equipes, restricoes=(), **kwargs) -> Problema:
    return Problema(
        salas=tuple(salas), equipes=tuple(equipes), restricoes=tuple(restricoes), **kwargs
    )


def sala_de(solucao, equipe_id: int) -> int | None:
    return next((a.sala_id for a in solucao.alocacoes if a.equipe_id == equipe_id), None)


# --------------------------------------------------------------------------
# H1-H8, uma restricao por vez
# --------------------------------------------------------------------------


def test_h1_equipe_nao_entra_em_sala_menor():
    """O exemplo da secao 4: 60 pessoas nao cabem numa sala de 40."""
    p = problema([sala(1, 40), sala(2, 80)], [equipe(1, 60)])
    resultado = solver.alocar(p)

    assert sala_de(resultado, 1) == 2


def test_h1_equipe_maior_que_tudo_fica_de_fora_com_motivo():
    """Secao 11: o sistema mostra o problema, nao inventa uma alocacao invalida."""
    p = problema([sala(1, 40), sala(2, 80)], [equipe(1, 92)])
    resultado = solver.alocar(p)

    assert resultado.alocacoes == ()
    assert resultado.nao_alocadas[0].codigo_motivo is CodigoMotivo.SEM_SALA_COMPATIVEL


def test_h2_mesma_sala_serve_dois_turnos_diferentes():
    """Turno e dimensao desde o D1: sem isso o predio pareceria mais cheio do que esta."""
    p = problema(
        [sala(1, 30)],
        [equipe(1, 28, turno=Turno.MANHA), equipe(2, 28, turno=Turno.TARDE)],
    )
    resultado = solver.alocar(p)

    assert len(resultado.alocacoes) == 2
    assert sala_de(resultado, 1) == sala_de(resultado, 2) == 1


def test_h2_integral_bloqueia_a_sala_nos_dois_turnos():
    p = problema(
        [sala(1, 30)],
        [equipe(1, 28, turno=Turno.INTEGRAL), equipe(2, 28, turno=Turno.MANHA)],
    )
    resultado = solver.alocar(p)

    assert len(resultado.alocacoes) == 1


def test_h3_recurso_obrigatorio_descarta_a_sala_maior():
    p = problema(
        [sala(1, 90), sala(2, 30, recursos=frozenset({"bancada_tecnica"}))],
        [equipe(1, 20, recursos_requeridos=frozenset({"bancada_tecnica"}))],
    )
    resultado = solver.alocar(p)

    assert sala_de(resultado, 1) == 2


def test_h4_acessibilidade_e_obrigatoria_quando_exigida():
    p = problema(
        [sala(1, 50), sala(2, 50, acessivel=True)],
        [equipe(1, 40, exige_acessibilidade=True)],
    )
    resultado = solver.alocar(p)

    assert sala_de(resultado, 1) == 2


def test_h5_andar_permitido_limita_a_escolha():
    p = problema(
        [sala(1, 50, andar=3), sala(2, 50, andar=7)],
        [equipe(1, 40)],
        [
            RestricaoDTO(
                id=1,
                tipo=TipoRestricao.ANDAR_PERMITIDO,
                parametros={"andares": [7]},
                alvo_id=1,
            )
        ],
    )
    resultado = solver.alocar(p)

    assert sala_de(resultado, 1) == 2


def test_h6_sala_reservada_so_aceita_o_setor_dono():
    p = problema(
        [sala(1, 50, reservada_para_setor_id=9), sala(2, 80)],
        [equipe(1, 40, setor_id=1)],
    )
    resultado = solver.alocar(p)

    assert sala_de(resultado, 1) == 2


def test_h7_setores_separados_nao_dividem_andar():
    """Juridico e Comercial do cenario de referencia, em miniatura."""
    p = problema(
        [sala(1, 50, andar=3), sala(2, 50, andar=3), sala(3, 50, andar=7)],
        [equipe(1, 40, setor_id=1), equipe(2, 40, setor_id=2)],
        [
            RestricaoDTO(
                id=1,
                tipo=TipoRestricao.SEPARACAO_SETORES,
                parametros={"setor_a": 1, "setor_b": 2},
            )
        ],
    )
    resultado = solver.alocar(p)

    andares = {
        next(s.andar for s in p.salas if s.id == a.sala_id) for a in resultado.alocacoes
    }
    assert len(resultado.alocacoes) == 2
    assert len(andares) == 2, "os dois setores acabaram no mesmo andar"


def test_h8_uma_equipe_ocupa_no_maximo_uma_sala():
    p = problema([sala(1, 50), sala(2, 50)], [equipe(1, 40)])
    resultado = solver.alocar(p)

    assert len(resultado.alocacoes) == 1


def test_equipe_pode_ficar_sem_sala_em_vez_de_o_modelo_ficar_inviavel():
    """H8 usa `<= 1` de proposito -- ver docs/objetivo.md.

    Com `== 1` este cenario seria INFEASIBLE e o sistema nao teria o que mostrar.
    """
    p = problema([sala(1, 50)], [equipe(1, 40), equipe(2, 40)])
    resultado = solver.alocar(p)

    assert resultado.status is StatusRun.OPTIMAL
    assert len(resultado.alocacoes) == 1
    assert len(resultado.nao_alocadas) == 1


# --------------------------------------------------------------------------
# Funcao de custo
# --------------------------------------------------------------------------


def test_o_solver_prefere_a_sala_que_desperdica_menos_assentos():
    """O exemplo da secao 4: 12 pessoas vao para a sala de 15, nao para a de 80."""
    p = problema([sala(1, 80), sala(2, 15)], [equipe(1, 12)])

    assert sala_de(solver.alocar(p), 1) == 2


def test_alocar_na_pior_sala_custa_menos_que_nao_alocar():
    """A regra de dominancia, verificada pelo comportamento e nao pela aritmetica.

    Com W_NA dominando, o solver aceita 68 assentos ociosos em vez de deixar a
    equipe de fora. Se algum dia isso se inverter, este teste quebra antes da demo.
    """
    p = problema([sala(1, 80)], [equipe(1, 12)])
    resultado = solver.alocar(p)

    assert len(resultado.alocacoes) == 1
    assert resultado.custo == 68


def test_o_custo_do_solver_bate_com_a_formula_documentada():
    """Trava o contrato entre o objetivo do modelo e docs/objetivo.md.

    Se as duas expressoes divergirem, a explicacao mostrada ao Coordenador Geral
    deixa de ser a razao real da decisao -- e nada mais no sistema perceberia.
    """
    p = problema(
        [sala(1, 50, andar=1), sala(2, 60, andar=4), sala(3, 30, andar=4)],
        [
            equipe(1, 45, andar_preferido=4),
            equipe(2, 28, andar_preferido=4),
            equipe(3, 40),
        ],
        [
            RestricaoDTO(
                id=1,
                tipo=TipoRestricao.PROXIMIDADE,
                parametros={"equipe_a": 1, "equipe_b": 2},
                rigida=False,
                peso=50,
            )
        ],
    )
    resultado = solver.alocar(p)

    assert avaliar(p, resultado.alocacoes) == resultado.custo


def test_proximidade_aproxima_equipes_relacionadas():
    p = problema(
        [sala(1, 30, andar=1), sala(2, 30, andar=2), sala(3, 30, andar=9)],
        [equipe(1, 25), equipe(2, 25)],
        [
            RestricaoDTO(
                id=1,
                tipo=TipoRestricao.PROXIMIDADE,
                parametros={"equipe_a": 1, "equipe_b": 2},
                rigida=False,
                peso=50,
            )
        ],
    )
    resultado = solver.alocar(p)
    andares = sorted(
        next(s.andar for s in p.salas if s.id == a.sala_id) for a in resultado.alocacoes
    )

    assert andares == [1, 2], "as duas deveriam ficar nos andares vizinhos"


def test_andar_preferido_cede_diante_da_ociosidade_quando_custa_menos():
    """Restricao flexivel e negociavel por definicao: 30 assentos ociosos (W_OC 1
    cada) nao valem os 20 do andar preferido, mas 10 valem."""
    p = problema(
        [sala(1, 25, andar=1), sala(2, 60, andar=5)],
        [equipe(1, 22, andar_preferido=5)],
    )

    assert sala_de(solver.alocar(p), 1) == 1


# --------------------------------------------------------------------------
# Baseline
# --------------------------------------------------------------------------


def test_o_guloso_pega_a_primeira_sala_que_couber():
    """Ingenuo na escolha: nao olha que a sala 2 desperdicaria menos."""
    p = problema([sala(1, 80), sala(2, 15)], [equipe(1, 12)])

    assert sala_de(baseline.alocar(p), 1) == 1


def test_o_guloso_nunca_viola_uma_restricao_rigida():
    """Se pudesse violar, seu custo cairia artificialmente e o MR-6 perderia o sentido."""
    p = problema(
        [sala(1, 50, andar=3), sala(2, 50, andar=3), sala(3, 50, andar=7)],
        [equipe(1, 40, setor_id=1), equipe(2, 40, setor_id=2), equipe(3, 45, setor_id=1)],
        [
            RestricaoDTO(
                id=1,
                tipo=TipoRestricao.SEPARACAO_SETORES,
                parametros={"setor_a": 1, "setor_b": 2},
            )
        ],
    )

    assert validator.violacoes(p, baseline.alocar(p)) == []


def test_o_guloso_nunca_se_declara_otimo():
    """Status FEASIBLE: os testes metamorficos so comparam execucoes OPTIMAL."""
    p = problema([sala(1, 50)], [equipe(1, 40)])

    assert baseline.alocar(p).status is StatusRun.FEASIBLE


# --------------------------------------------------------------------------
# Validador independente (AC-2)
# --------------------------------------------------------------------------


def test_o_validador_acusa_uma_solucao_fabricada_acima_da_capacidade():
    """O validador tem que reprovar o que o solver nao conseguiria produzir.

    Sem este teste, um validador que sempre devolvesse `[]` passaria no AC-2 --
    e o criterio inteiro seria decorativo.
    """
    from app.engine.types import Alocacao, Solucao

    p = problema([sala(1, 10)], [equipe(1, 40)])
    fabricada = Solucao(
        alocacoes=(Alocacao(equipe_id=1, sala_id=1, turno=Turno.INTEGRAL),),
        nao_alocadas=(),
        custo=0,
        status=StatusRun.OPTIMAL,
        duracao_ms=0,
        engine_version="teste",
    )

    achadas = validator.violacoes(p, fabricada)
    assert [v["regra"] for v in achadas] == ["H1"]


def test_o_validador_acusa_duas_equipes_na_mesma_sala_no_mesmo_turno():
    from app.engine.types import Alocacao, Solucao

    # A equipe 1 e integral e a 2 e da manha: colidem no slot da manha, e so nele.
    p = problema([sala(1, 50)], [equipe(1, 20), equipe(2, 20, turno=Turno.MANHA)])
    fabricada = Solucao(
        alocacoes=(
            Alocacao(equipe_id=1, sala_id=1, turno=Turno.INTEGRAL),
            Alocacao(equipe_id=2, sala_id=1, turno=Turno.MANHA),
        ),
        nao_alocadas=(),
        custo=0,
        status=StatusRun.OPTIMAL,
        duracao_ms=0,
        engine_version="teste",
    )

    achadas = validator.violacoes(p, fabricada)
    assert [v["regra"] for v in achadas] == ["H2"]
    assert "manha" in achadas[0]["detalhe"]


def test_o_validador_aprova_o_que_o_solver_produz():
    p = problema(
        [sala(1, 50, andar=1), sala(2, 30, andar=4, acessivel=True)],
        [equipe(1, 45), equipe(2, 28, exige_acessibilidade=True)],
    )

    assert validator.violacoes(p, solver.alocar(p)) == []


# --------------------------------------------------------------------------
# Determinismo (base do AC-7)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("execucao", range(3))
def test_a_mesma_entrada_produz_sempre_a_mesma_solucao(execucao):
    p = problema(
        [sala(i, 20 + i * 5, andar=1 + i % 9) for i in range(1, 13)],
        [equipe(i, 15 + i * 3, andar_preferido=1 + i % 9) for i in range(1, 9)],
        pesos=Pesos(),
    )
    primeira, segunda = solver.alocar(p), solver.alocar(p)

    assert primeira.custo == segunda.custo
    assert primeira.alocacoes == segunda.alocacoes


# --------------------------------------------------------------------------
# Explainer -- a conta por tras de uma recomendacao (AC-3)
# --------------------------------------------------------------------------


def explicar(p):
    """Explica a solucao otima e devolve as alocacoes indexadas por equipe."""
    return {a.equipe_id: a for a in explainer.explicar(p, solver.alocar(p))}


def test_a_explicacao_mostra_a_ociosidade_que_decidiu_a_escolha():
    """O mesmo caso de `test_o_solver_prefere_a_sala_que_desperdica_menos_assentos`,
    agora cobrando que o motor saiba *dizer* por que escolheu."""
    p = problema([sala(1, 80), sala(2, 15)], [equipe(1, 12)])
    alocacao = explicar(p)[1]

    termos = {t["nome"]: t["valor"] for t in alocacao.explicacao["termos"]}
    assert termos["ociosidade"] == 3  # 15 lugares para 12 pessoas
    assert alocacao.explicacao["custo_total"] == 3
    assert alocacao.explicacao["ocupacao_pct"] == 80.0

    descartada = alocacao.alternativas[0]
    assert descartada["sala_id"] == 1
    assert descartada["custo"] == 68 and descartada["delta"] == 65
    assert "68 assentos ociosos" in descartada["por_que_nao"]


def test_a_explicacao_nao_mexe_na_decisao():
    """Pos-processamento: reconstroi o porque, nunca troca a sala nem o custo."""
    p = problema([sala(1, 80), sala(2, 15)], [equipe(1, 12)])
    solucao = solver.alocar(p)
    explicadas = explainer.explicar(p, solucao)

    for antes, depois in zip(solucao.alocacoes, explicadas, strict=True):
        assert (antes.equipe_id, antes.sala_id, antes.turno, antes.custo) == (
            depois.equipe_id,
            depois.sala_id,
            depois.turno,
            depois.custo,
        )


def test_a_alternativa_ocupada_diz_quem_a_ocupa():
    """Num predio cheio, a resposta util e "a 001 seria melhor, mas esta com a
    equipe 1" -- e nao uma lista vazia de alternativas."""
    p = problema([sala(1, 15), sala(2, 80)], [equipe(1, 12), equipe(2, 12)])
    alocacoes = explicar(p)

    # Quem ficou com a sala grande tinha a pequena como melhor opcao.
    perdedora = next(a for a in alocacoes.values() if a.sala_id == 2)
    descartada = perdedora.alternativas[0]

    assert descartada["sala_id"] == 1
    assert descartada["disponivel"] is False
    assert "ocupada pela equipe" in descartada["por_que_nao"]
    assert perdedora.explicacao["comparacao"]["tipo"] == "sem_alternativa"


def test_o_termo_de_proximidade_cita_a_parceira_e_a_distancia():
    p = problema(
        [sala(1, 30, andar=1), sala(2, 30, andar=2), sala(3, 30, andar=9)],
        [equipe(1, 25), equipe(2, 25)],
        [
            RestricaoDTO(
                id=1,
                tipo=TipoRestricao.PROXIMIDADE,
                parametros={"equipe_a": 1, "equipe_b": 2},
                rigida=False,
                peso=50,
            )
        ],
    )
    termos = {t["nome"]: t for t in explicar(p)[1].explicacao["termos"]}

    assert termos["proximidade"]["valor"] == 50  # um andar de distancia x W_PR
    assert "equipe 2" in termos["proximidade"]["detalhe"]


def test_a_proximidade_rigida_bloqueia_as_salas_dos_outros_andares():
    """Mudar so uma das duas quebraria o par: a alternativa nao e real, e a
    explicacao diz isso em vez de oferece-la."""
    p = problema(
        [sala(1, 30, andar=1), sala(2, 30, andar=1), sala(3, 30, andar=9)],
        [equipe(1, 25), equipe(2, 25)],
        [
            RestricaoDTO(
                id=1,
                tipo=TipoRestricao.PROXIMIDADE,
                parametros={"equipe_a": 1, "equipe_b": 2},
                rigida=True,
            )
        ],
    )
    do_nono = [a for a in explicar(p)[1].alternativas if a["andar"] == 9]

    assert do_nono, "a sala do 9o andar deveria aparecer como descartada"
    assert do_nono[0]["disponivel"] is False
    assert "exige mesmo andar" in do_nono[0]["por_que_nao"]


@pytest.mark.parametrize("execucao", range(2))
def test_a_mesma_entrada_produz_sempre_a_mesma_explicacao(execucao):
    """A explicacao virou registro append-only: ela tambem entra no AC-7."""
    p = problema(
        [sala(i, 20 + i * 5, andar=1 + i % 9) for i in range(1, 13)],
        [equipe(i, 15 + i * 3, andar_preferido=1 + i % 9) for i in range(1, 9)],
    )

    assert explainer.explicar(p, solver.alocar(p)) == explainer.explicar(p, solver.alocar(p))


# --------------------------------------------------------------------------
# Diagnostics -- por que a equipe ficou de fora (AC-4)
# --------------------------------------------------------------------------


def test_o_diagnostico_corrige_a_classificacao_estatica_e_nomeia_a_sala():
    """A sala grande existe e esta livre -- falta so o recurso.

    A classificacao estatica responde "sem sala compativel", porque foi a
    capacidade que esvaziou o conjunto depois do filtro de recurso. Correto e
    inutil: nao diz o que mudar. Relaxar e reexecutar responde "sem a exigencia
    de bancada, caberia na sala 001".
    """
    p = problema(
        [sala(1, 90), sala(2, 20, recursos=frozenset({"bancada_tecnica"}))],
        [equipe(1, 30, recursos_requeridos=frozenset({"bancada_tecnica"}))],
    )
    solucao = solver.alocar(p)
    base = solucao.nao_alocadas[0]
    refinada = diagnostics.diagnosticar(p, solucao)[0]

    assert base.codigo_motivo is CodigoMotivo.SEM_SALA_COMPATIVEL
    assert refinada.codigo_motivo is CodigoMotivo.RECURSO_INDISPONIVEL
    assert "caberia na sala 001" in refinada.causa
    assert "libera a sala 001" in refinada.encaminhamento


def test_o_relaxamento_que_nao_resolve_e_reportado_como_disputa():
    """Relaxar existe, mas nao basta: a sala compativel segue ocupada.

    A causa entao e a disputa, e nao uma regra -- e o diagnostico diz quantos
    relaxamentos foram testados em vez de escolher um deles como culpado.
    """
    p = problema(
        [sala(1, 50, recursos=frozenset({"bancada_tecnica"}))],
        [equipe(1, 45), equipe(2, 40, recursos_requeridos=frozenset({"bancada_tecnica"}))],
    )
    solucao = solver.alocar(p)
    refinada = diagnostics.diagnosticar(p, solucao)[0]

    assert refinada.equipe_id == 2
    assert "caberia na sala" not in refinada.causa
    assert "Nenhum dos 1 relaxamentos testados resolveria" in refinada.causa


def test_o_diagnostico_nao_promete_uma_sala_que_desalojaria_outra_equipe():
    """"Resolver" tirando outra equipe do lugar nao resolveu nada, so mudou quem
    fica de fora -- e apresentar isso como encaminhamento enganaria quem le.

    Aqui o sub-solve *conseguiria* alocar a equipe 2: com prioridade 5 contra 1,
    o custo de deixa-la de fora domina, e o CP-SAT do recorte prefere tirar a
    equipe 1 da unica sala. E uma solucao valida do subproblema e uma resposta
    falsa a pergunta que foi feita.
    """
    p = problema(
        [sala(1, 50)],
        [
            equipe(1, 45, prioridade=1),
            equipe(2, 45, prioridade=5, recursos_requeridos=frozenset({"bancada_tecnica"})),
        ],
    )
    solucao = solver.alocar(p)
    refinada = diagnostics.diagnosticar(p, solucao)[0]

    assert refinada.equipe_id == 2
    assert "caberia na sala" not in refinada.causa
    assert "Nenhum dos 1 relaxamentos testados resolveria" in refinada.causa


def test_sem_regra_para_relaxar_o_diagnostico_mantem_a_causa_base():
    """Duas equipes, uma sala, nenhuma restricao: a causa e a disputa, e nao ha
    o que recomendar remover. O motor diz isso em vez de inventar uma regra."""
    p = problema([sala(1, 50)], [equipe(1, 40), equipe(2, 40)])
    solucao = solver.alocar(p)
    refinada = diagnostics.diagnosticar(p, solucao)[0]

    assert refinada == solucao.nao_alocadas[0]
    assert refinada.codigo_motivo is CodigoMotivo.CAPACIDADE_ESGOTADA


def test_o_diagnostico_aponta_a_acessibilidade_quando_e_ela_que_bloqueia():
    p = problema(
        [sala(1, 60), sala(2, 20, acessivel=True)],
        [equipe(1, 40, exige_acessibilidade=True)],
    )
    refinada = diagnostics.diagnosticar(p, solver.alocar(p))[0]

    assert refinada.codigo_motivo is CodigoMotivo.ACESSIBILIDADE_INDISPONIVEL
    assert "acessibilidade" in refinada.causa


def test_nao_ha_equipe_de_fora_nao_ha_diagnostico():
    p = problema([sala(1, 50)], [equipe(1, 40)])

    assert diagnostics.diagnosticar(p, solver.alocar(p)) == ()
