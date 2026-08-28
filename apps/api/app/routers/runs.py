"""Execucao do motor e historico de governanca.

`POST /api/runs` e o "GERAR ALOCACAO OTIMIZADA" do enunciado. Uma chamada faz
cinco coisas, nessa ordem:

1. monta o problema a partir do banco, com snapshot e hash da entrada;
2. roda o **baseline** guloso -- a coluna "Antes" da tela de comparacao e a
   linha de base do AC-5;
3. roda o **solver** CP-SAT;
4. roda o **explainer** e o **diagnostics** sobre o resultado, que respondem
   "por que esta sala?" (AC-3) e "por que esta equipe ficou de fora?" (AC-4);
5. roda o **validador independente** sobre o resultado e grava tudo.

O passo 4 vive aqui, e nao dentro de `solver.alocar`, de proposito: o solver roda
dezenas de vezes nos testes metamorficos, onde a explicacao nao interessa e o
pos-processamento so custaria tempo. Quem precisa de justificativa e o registro
gravado, e ele nasce nesta rota.

O passo 5 e o que sustenta a resposta a pergunta central do desafio. Se o
validador -- que nao compartilha uma linha de codigo com o solver -- acusar
violacao de restricao rigida, a execucao e gravada como ERRO, com as alocacoes
que o motor produziu preservadas. O sistema nao esconde o proprio defeito: e a
mesma regra que a secao 11 aplica as equipes sem sala.

As rotas de leitura sao append-only: nao existe PATCH nem DELETE sobre Run.
Corrigir uma recomendacao se faz criando uma Intervencao (ver audit.py).
"""

import time
from dataclasses import replace
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.engine import baseline, diagnostics, explainer, solver, validator
from app.engine.types import Pesos, Problema, Solucao
from app.engine.version import ENGINE_VERSION
from app.enums import StatusRun
from app.models import Assignment, NaoAlocada, Run
from app.problema import hash_entrada, montar_problema, montar_snapshot
from app.schemas import RunCreate, RunDetalhe, RunRead

router = APIRouter(prefix="/api/runs", tags=["runs"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "",
    response_model=RunDetalhe,
    status_code=201,
    summary="Gerar alocacao otimizada",
)
def gerar(dados: RunCreate, session: SessionDep) -> RunDetalhe:
    pesos = Pesos(**dados.pesos.model_dump())
    snapshot = montar_snapshot(session)
    entrada_hash = hash_entrada(snapshot)

    problema = montar_problema(
        session, pesos=pesos, seed=dados.seed, limite_segundos=dados.limite_segundos
    )

    if not problema.equipes:
        raise HTTPException(422, "Nao ha equipes cadastradas. Carregue um cenario primeiro.")

    if not pesos.dominancia_ok(problema.capacidade_total):
        raise HTTPException(
            422,
            "Pesos violam a regra de dominancia: com W_NA * prioridade_minima <= "
            f"W_OC * {problema.capacidade_total}, deixar uma equipe de fora fica mais "
            "barato que aloca-la e o motor passaria a esconder equipes. "
            "Ver docs/objetivo.md.",
        )

    run = Run(
        usuario=dados.usuario,
        engine_version=ENGINE_VERSION,
        seed=dados.seed,
        pesos=pesos.to_dict(),
        hash_entrada=entrada_hash,
        snapshot_entrada=snapshot,
    )

    try:
        solucao_baseline = baseline.alocar(problema)
        solucao = solver.alocar(problema)
        solucao, duracao_pos_ms = _justificar(problema, solucao)
    except Exception as exc:  # noqa: BLE001 -- a falha vira registro, nao stacktrace perdido
        # Uma execucao que estourou tambem e uma execucao: sem este registro o
        # painel de observabilidade ficaria cego justamente para o que importa.
        run.status = StatusRun.ERRO
        run.erro = f"{type(exc).__name__}: {exc}"
        session.add(run)
        session.commit()
        raise HTTPException(500, f"O motor falhou nesta execucao (run {run.id}): {exc}") from exc

    violacoes = validator.violacoes(problema, solucao)

    # O tempo do AC-6 e o que o Coordenador Geral espera pela recomendacao: o
    # solver mais a justificativa que vai junto dela. O baseline fica de fora
    # porque nao e a recomendacao, e a coluna de comparacao. A separacao fica
    # gravada em `metricas` para que a medicao do D6 saiba de onde veio cada ms.
    run.duracao_ms = solucao.duracao_ms + duracao_pos_ms
    run.status = StatusRun.ERRO if violacoes else solucao.status
    run.metricas = solucao.metricas(problema) | {
        "violacoes": len(violacoes),
        "duracao_solver_ms": solucao.duracao_ms,
        "duracao_justificativa_ms": duracao_pos_ms,
    }
    run.metricas_baseline = solucao_baseline.metricas(problema) | {
        "violacoes": len(validator.violacoes(problema, solucao_baseline))
    }
    if violacoes:
        # O validador e independente do solver justamente para poder discordar
        # dele. Quando discorda, quem esta errado e o solver -- e a execucao
        # inteira fica marcada, nao apenas anotada num log.
        run.erro = _resumo_das_violacoes(violacoes)

    session.add(run)
    session.commit()
    session.refresh(run)

    _persistir_resultado(session, run, solucao)
    session.commit()

    return _detalhar(session, run)


def _justificar(problema: Problema, solucao: Solucao) -> tuple[Solucao, int]:
    """Enriquece a solucao com o *porque* de cada linha que ela vai gravar.

    Os dois passos leem a mesma solucao pronta e nao mexem em quem foi para onde:
    o `explainer` reconstroi a conta de cada recomendacao (AC-3) e o
    `diagnostics` refina o motivo de cada equipe sem sala relaxando uma regra por
    vez (AC-4). Trocar a decisao aqui tornaria o custo gravado uma ficcao.

    Os dois partem de `solucao`, e nao um do resultado do outro: sao respostas
    independentes sobre o mesmo fato.
    """
    inicio = time.perf_counter()
    enriquecida = replace(
        solucao,
        alocacoes=explainer.explicar(problema, solucao),
        nao_alocadas=diagnostics.diagnosticar(problema, solucao),
    )
    return enriquecida, int((time.perf_counter() - inicio) * 1000)


def _resumo_das_violacoes(violacoes: list[dict]) -> str:
    regras = sorted({v["regra"] for v in violacoes})
    return (
        f"O validador independente acusou {len(violacoes)} violacao(oes) de restricao "
        f"rigida ({', '.join(regras)}). Primeira: {violacoes[0]['detalhe']}"
    )


def _persistir_resultado(session: Session, run: Run, solucao: Solucao) -> None:
    """Grava alocacoes e nao alocadas. Append-only: nunca sao editadas depois."""
    session.add_all(
        Assignment(
            run_id=run.id,
            equipe_id=alocacao.equipe_id,
            sala_id=alocacao.sala_id,
            turno=alocacao.turno,
            custo=alocacao.custo,
            # A conta decomposta e as salas descartadas, como o explainer as
            # produziu. Gravadas junto da recomendacao, e nao recalculadas na
            # leitura: a entrada muda, o registro e append-only, e a explicacao
            # tem que continuar sendo a de *quando a decisao foi tomada*.
            explicacao=alocacao.explicacao,
            alternativas=alocacao.alternativas,
        )
        for alocacao in solucao.alocacoes
    )
    session.add_all(
        NaoAlocada(
            run_id=run.id,
            equipe_id=rejeicao.equipe_id,
            codigo_motivo=rejeicao.codigo_motivo,
            causa=rejeicao.causa,
            encaminhamento=rejeicao.encaminhamento,
        )
        for rejeicao in solucao.nao_alocadas
    )


def _detalhar(session: Session, run: Run) -> RunDetalhe:
    alocacoes = session.exec(select(Assignment).where(Assignment.run_id == run.id)).all()
    nao_alocadas = session.exec(select(NaoAlocada).where(NaoAlocada.run_id == run.id)).all()
    return RunDetalhe(
        **run.model_dump(),
        alocacoes=list(alocacoes),
        nao_alocadas=list(nao_alocadas),
    )


@router.get("", response_model=list[RunRead], summary="Historico de execucoes")
def listar(session: SessionDep, limite: Annotated[int, Query(ge=1, le=200)] = 50) -> list[Run]:
    consulta = select(Run).order_by(Run.criado_em.desc()).limit(limite)
    return list(session.exec(consulta).all())


@router.get("/{run_id}", response_model=RunDetalhe, summary="Detalhe de uma execucao")
def obter(run_id: int, session: SessionDep) -> RunDetalhe:
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(404, f"Execucao {run_id} nao encontrada")

    return _detalhar(session, run)
