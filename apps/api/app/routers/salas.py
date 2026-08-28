"""CRUD de salas -- o Coordenador Geral administra os espacos fisicos."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.enums import TipoSala
from app.models import Sala
from app.schemas import SalaCreate, SalaRead, SalaUpdate

router = APIRouter(prefix="/api/salas", tags=["salas"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[SalaRead], summary="Listar salas")
def listar(
    session: SessionDep,
    andar: Annotated[int | None, Query(ge=1, le=9)] = None,
    tipo: TipoSala | None = None,
    disponivel: bool | None = None,
) -> list[Sala]:
    consulta = select(Sala)
    if andar is not None:
        consulta = consulta.where(Sala.andar == andar)
    if tipo is not None:
        consulta = consulta.where(Sala.tipo == tipo)
    if disponivel is not None:
        consulta = consulta.where(Sala.disponivel == disponivel)
    return list(session.exec(consulta.order_by(Sala.andar, Sala.codigo)).all())


@router.get("/{sala_id}", response_model=SalaRead, summary="Obter uma sala")
def obter(sala_id: int, session: SessionDep) -> Sala:
    sala = session.get(Sala, sala_id)
    if sala is None:
        raise HTTPException(404, f"Sala {sala_id} nao encontrada")
    return sala


@router.post("", response_model=SalaRead, status_code=201, summary="Cadastrar sala")
def criar(dados: SalaCreate, session: SessionDep) -> Sala:
    if session.exec(select(Sala).where(Sala.codigo == dados.codigo)).first():
        raise HTTPException(409, f"Ja existe uma sala com o codigo {dados.codigo}")
    sala = Sala(**dados.model_dump())
    session.add(sala)
    session.commit()
    session.refresh(sala)
    return sala


@router.patch("/{sala_id}", response_model=SalaRead, summary="Alterar sala")
def atualizar(sala_id: int, dados: SalaUpdate, session: SessionDep) -> Sala:
    sala = session.get(Sala, sala_id)
    if sala is None:
        raise HTTPException(404, f"Sala {sala_id} nao encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(sala, campo, valor)
    session.add(sala)
    session.commit()
    session.refresh(sala)
    return sala


@router.delete("/{sala_id}", status_code=204, summary="Remover sala")
def remover(sala_id: int, session: SessionDep) -> None:
    sala = session.get(Sala, sala_id)
    if sala is None:
        raise HTTPException(404, f"Sala {sala_id} nao encontrada")
    session.delete(sala)
    session.commit()
