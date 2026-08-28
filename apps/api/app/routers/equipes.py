"""CRUD de equipes -- e por aqui que o Coordenador de Setor informa demanda."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Equipe, Setor
from app.schemas import EquipeCreate, EquipeRead, EquipeUpdate

router = APIRouter(prefix="/api/equipes", tags=["equipes"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[EquipeRead], summary="Listar equipes")
def listar(session: SessionDep, setor_id: int | None = None) -> list[Equipe]:
    consulta = select(Equipe)
    if setor_id is not None:
        consulta = consulta.where(Equipe.setor_id == setor_id)
    return list(session.exec(consulta.order_by(Equipe.setor_id, Equipe.nome)).all())


@router.get("/{equipe_id}", response_model=EquipeRead, summary="Obter uma equipe")
def obter(equipe_id: int, session: SessionDep) -> Equipe:
    equipe = session.get(Equipe, equipe_id)
    if equipe is None:
        raise HTTPException(404, f"Equipe {equipe_id} nao encontrada")
    return equipe


@router.post("", response_model=EquipeRead, status_code=201, summary="Cadastrar equipe")
def criar(dados: EquipeCreate, session: SessionDep) -> Equipe:
    if session.get(Setor, dados.setor_id) is None:
        raise HTTPException(422, f"Setor {dados.setor_id} nao existe")
    equipe = Equipe(**dados.model_dump())
    session.add(equipe)
    session.commit()
    session.refresh(equipe)
    return equipe


@router.patch("/{equipe_id}", response_model=EquipeRead, summary="Alterar equipe")
def atualizar(equipe_id: int, dados: EquipeUpdate, session: SessionDep) -> Equipe:
    equipe = session.get(Equipe, equipe_id)
    if equipe is None:
        raise HTTPException(404, f"Equipe {equipe_id} nao encontrada")
    campos = dados.model_dump(exclude_unset=True)
    if "setor_id" in campos and session.get(Setor, campos["setor_id"]) is None:
        raise HTTPException(422, f"Setor {campos['setor_id']} nao existe")
    for campo, valor in campos.items():
        setattr(equipe, campo, valor)
    session.add(equipe)
    session.commit()
    session.refresh(equipe)
    return equipe


@router.delete("/{equipe_id}", status_code=204, summary="Remover equipe")
def remover(equipe_id: int, session: SessionDep) -> None:
    equipe = session.get(Equipe, equipe_id)
    if equipe is None:
        raise HTTPException(404, f"Equipe {equipe_id} nao encontrada")
    session.delete(equipe)
    session.commit()
