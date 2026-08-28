"""CRUD de setores."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Equipe, Setor
from app.schemas import SetorCreate, SetorRead, SetorUpdate

router = APIRouter(prefix="/api/setores", tags=["setores"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[SetorRead], summary="Listar setores")
def listar(session: SessionDep) -> list[Setor]:
    return list(session.exec(select(Setor).order_by(Setor.nome)).all())


@router.get("/{setor_id}", response_model=SetorRead, summary="Obter um setor")
def obter(setor_id: int, session: SessionDep) -> Setor:
    setor = session.get(Setor, setor_id)
    if setor is None:
        raise HTTPException(404, f"Setor {setor_id} nao encontrado")
    return setor


@router.post("", response_model=SetorRead, status_code=201, summary="Cadastrar setor")
def criar(dados: SetorCreate, session: SessionDep) -> Setor:
    if session.exec(select(Setor).where(Setor.nome == dados.nome)).first():
        raise HTTPException(409, f"Ja existe um setor chamado {dados.nome}")
    setor = Setor(**dados.model_dump())
    session.add(setor)
    session.commit()
    session.refresh(setor)
    return setor


@router.patch("/{setor_id}", response_model=SetorRead, summary="Alterar setor")
def atualizar(setor_id: int, dados: SetorUpdate, session: SessionDep) -> Setor:
    setor = session.get(Setor, setor_id)
    if setor is None:
        raise HTTPException(404, f"Setor {setor_id} nao encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(setor, campo, valor)
    session.add(setor)
    session.commit()
    session.refresh(setor)
    return setor


@router.delete("/{setor_id}", status_code=204, summary="Remover setor")
def remover(setor_id: int, session: SessionDep) -> None:
    setor = session.get(Setor, setor_id)
    if setor is None:
        raise HTTPException(404, f"Setor {setor_id} nao encontrado")
    equipes = session.exec(select(Equipe).where(Equipe.setor_id == setor_id)).all()
    if equipes:
        raise HTTPException(
            409, f"Setor {setor.nome} ainda tem {len(equipes)} equipe(s). Remova-as primeiro."
        )
    session.delete(setor)
    session.commit()
