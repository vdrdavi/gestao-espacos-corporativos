"""Execucao do motor e historico de governanca.

`POST /api/runs` e o "GERAR ALOCACAO OTIMIZADA" do enunciado. No D1 ele monta o
problema, calcula o snapshot e o hash -- e para no motor, devolvendo 501. O
pipeline ate a fronteira do solver ja e real; so a alocacao falta.

As rotas de leitura sao append-only: nao existe PATCH nem DELETE sobre Run.
Corrigir uma recomendacao se faz criando uma Intervencao (ver audit.py).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.engine import EtapaNaoImplementada
from app.engine.types import Pesos
from app.engine.version import ENGINE_VERSION
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
    responses={501: {"description": "Motor ainda em stub (D1)"}},
)
def gerar(dados: RunCreate, session: SessionDep) -> Run:
    from app.engine import solver  # import tardio: o stub levanta na chamada, nao no import

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

    try:
        solver.alocar(problema)
    except EtapaNaoImplementada as exc:
        raise HTTPException(
            501,
            {
                "mensagem": str(exc),
                "etapa": exc.etapa,
                "previsto_para": exc.dia,
                "pipeline_ate_aqui": {
                    "salas": len(problema.salas),
                    "equipes": len(problema.equipes),
                    "restricoes": len(problema.restricoes),
                    "capacidade_total": problema.capacidade_total,
                    "hash_entrada": entrada_hash,
                    "engine_version": ENGINE_VERSION,
                    "pesos": pesos.to_dict(),
                },
            },
        ) from exc

    raise HTTPException(500, "Caminho inalcancavel enquanto o solver for um stub.")


@router.get("", response_model=list[RunRead], summary="Historico de execucoes")
def listar(session: SessionDep, limite: Annotated[int, Query(ge=1, le=200)] = 50) -> list[Run]:
    consulta = select(Run).order_by(Run.criado_em.desc()).limit(limite)
    return list(session.exec(consulta).all())


@router.get("/{run_id}", response_model=RunDetalhe, summary="Detalhe de uma execucao")
def obter(run_id: int, session: SessionDep) -> RunDetalhe:
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(404, f"Execucao {run_id} nao encontrada")

    alocacoes = session.exec(select(Assignment).where(Assignment.run_id == run_id)).all()
    nao_alocadas = session.exec(select(NaoAlocada).where(NaoAlocada.run_id == run_id)).all()

    return RunDetalhe(
        **run.model_dump(),
        alocacoes=list(alocacoes),
        nao_alocadas=list(nao_alocadas),
    )
