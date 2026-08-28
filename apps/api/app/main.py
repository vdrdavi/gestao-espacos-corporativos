"""Aplicacao FastAPI.

Sistema Inteligente de Gestao e Otimizacao de Espacos Corporativos.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.engine.version import ENGINE_VERSION
from app.routers import audit, cenarios, equipes, metrics, restricoes, runs, salas, setores

DESCRICAO = """
Protótipo de alocação de equipes em espaços corporativos.

O motor não decide sozinho: cada recomendação carrega sua justificativa, cada
execução vira um registro de auditoria imutável, e o Coordenador Geral pode
aceitar, rejeitar ou alterar qualquer sugestão — com a intervenção registrada.

**Estado atual (D1):** modelo de dados, endpoints e CI prontos.
`POST /api/runs` responde **501** — a lógica de alocação entra no D2.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Gestão de Espaços Corporativos",
    description=DESCRICAO,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for modulo in (salas, setores, equipes, restricoes, runs, metrics, audit, cenarios):
    app.include_router(modulo.router)


@app.get("/health", tags=["infra"], summary="Healthcheck")
def health() -> dict:
    return {"status": "ok", "engine_version": ENGINE_VERSION}
