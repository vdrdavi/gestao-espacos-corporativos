"""CRUD de restricoes.

`rigida=True` vira restricao do modelo CP-SAT (nunca violavel); `rigida=False`
vira termo ponderado da funcao de custo. Ver docs/objetivo.md.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.enums import TipoRestricao
from app.models import Restricao
from app.schemas import RestricaoCreate, RestricaoRead, RestricaoUpdate

router = APIRouter(prefix="/api/restricoes", tags=["restricoes"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[RestricaoRead], summary="Listar restricoes")
def listar(
    session: SessionDep,
    rigida: bool | None = None,
    tipo: TipoRestricao | None = None,
) -> list[Restricao]:
    consulta = select(Restricao)
    if rigida is not None:
        consulta = consulta.where(Restricao.rigida == rigida)
    if tipo is not None:
        consulta = consulta.where(Restricao.tipo == tipo)
    return list(session.exec(consulta.order_by(Restricao.id)).all())


@router.get("/{restricao_id}", response_model=RestricaoRead, summary="Obter uma restricao")
def obter(restricao_id: int, session: SessionDep) -> Restricao:
    restricao = session.get(Restricao, restricao_id)
    if restricao is None:
        raise HTTPException(404, f"Restricao {restricao_id} nao encontrada")
    return restricao


@router.post("", response_model=RestricaoRead, status_code=201, summary="Criar restricao")
def criar(dados: RestricaoCreate, session: SessionDep) -> Restricao:
    restricao = Restricao(**dados.model_dump())
    session.add(restricao)
    session.commit()
    session.refresh(restricao)
    return restricao


@router.patch("/{restricao_id}", response_model=RestricaoRead, summary="Alterar restricao")
def atualizar(restricao_id: int, dados: RestricaoUpdate, session: SessionDep) -> Restricao:
    restricao = session.get(Restricao, restricao_id)
    if restricao is None:
        raise HTTPException(404, f"Restricao {restricao_id} nao encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(restricao, campo, valor)
    session.add(restricao)
    session.commit()
    session.refresh(restricao)
    return restricao


@router.delete("/{restricao_id}", status_code=204, summary="Remover restricao")
def remover(restricao_id: int, session: SessionDep) -> None:
    restricao = session.get(Restricao, restricao_id)
    if restricao is None:
        raise HTTPException(404, f"Restricao {restricao_id} nao encontrada")
    session.delete(restricao)
    session.commit()
