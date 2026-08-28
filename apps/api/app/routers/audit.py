"""Intervencao humana (secao 10) e trilha de auditoria (secao 12).

A recomendacao do sistema nao e uma decisao absoluta. O Coordenador Geral pode
aceitar, rejeitar, alterar a mao ou pedir nova otimizacao -- e toda acao fica
registrada. Nenhuma dessas operacoes edita o Assignment original: a trilha e
append-only, entao o historico continua mostrando o que o motor recomendou *e*
o que o humano decidiu.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models import Intervencao, Run
from app.schemas import IntervencaoCreate, IntervencaoRead

router = APIRouter(prefix="/api", tags=["auditoria"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.post(
    "/runs/{run_id}/intervencoes",
    response_model=IntervencaoRead,
    status_code=201,
    summary="Registrar decisao humana sobre uma recomendacao",
)
def registrar(run_id: int, dados: IntervencaoCreate, session: SessionDep) -> Intervencao:
    if session.get(Run, run_id) is None:
        raise HTTPException(404, f"Execucao {run_id} nao encontrada")

    intervencao = Intervencao(run_id=run_id, **dados.model_dump())

    # No D2 o validator independente entra aqui: uma alteracao manual que viole
    # uma restricao rigida preenche `alerta` -- o sistema avisa e registra, mas
    # nao bloqueia. A decisao final pertence ao responsavel humano.

    session.add(intervencao)
    session.commit()
    session.refresh(intervencao)
    return intervencao


@router.get("/audit", response_model=list[IntervencaoRead], summary="Trilha de auditoria")
def listar(
    session: SessionDep,
    run_id: int | None = None,
    limite: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[Intervencao]:
    consulta = select(Intervencao)
    if run_id is not None:
        consulta = consulta.where(Intervencao.run_id == run_id)
    consulta = consulta.order_by(Intervencao.criado_em.desc()).limit(limite)
    return list(session.exec(consulta).all())
