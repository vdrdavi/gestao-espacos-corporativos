"""Carga de cenarios.

Carregar um cenario **reseta o banco** e aplica um conjunto conhecido de dados.
E o que torna a demo reproduzivel: o cenario de referencia sempre gera os
mesmos 108 salas / 87 equipes, e os tres cenarios de estresse existem para
demonstrar a secao 11 (tratamento de excecoes) ao vivo.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.schemas import CenarioRead
from seed.cenarios import CENARIOS

router = APIRouter(prefix="/api/cenarios", tags=["cenarios"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("", response_model=list[CenarioRead], summary="Listar cenarios disponiveis")
def listar() -> list[CenarioRead]:
    return [
        CenarioRead(nome=c.nome, titulo=c.titulo, descricao=c.descricao)
        for c in CENARIOS.values()
    ]


@router.post(
    "/{nome}/carregar",
    response_model=dict,
    summary="Resetar o banco e carregar um cenario",
)
def carregar(nome: str, session: SessionDep, seed: int = 42) -> dict:
    cenario = CENARIOS.get(nome)
    if cenario is None:
        raise HTTPException(
            404, f"Cenario '{nome}' nao existe. Disponiveis: {sorted(CENARIOS)}"
        )
    return cenario.aplicar(session, seed=seed)
