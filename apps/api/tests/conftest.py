"""Fixtures de teste.

Banco em memoria com StaticPool: sem StaticPool cada conexao SQLite ":memory:"
abre um banco *novo*, e as tabelas criadas na fixture desapareceriam antes do
teste rodar.

O TestClient e criado sem `with`, de proposito: o context manager dispara o
lifespan da aplicacao, que chamaria `init_db()` no banco real e criaria um
espacos.db no meio da suite.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app


@pytest.fixture(name="engine_teste")
def engine_teste_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine_teste):
    with Session(engine_teste) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(name="cenario_referencia")
def cenario_referencia_fixture(session):
    """Predio completo carregado: 108 salas, 8 setores, 87 equipes."""
    from seed.generate import gerar

    return gerar(session, seed=42)


@pytest.fixture(name="cenario_referencia_montado")
def cenario_referencia_montado_fixture():
    """O `Problema` do predio completo, pronto para o motor.

    Sessao propria (nao a do TestClient) porque os testes metamorficos
    transformam a entrada em memoria e nunca tocam no banco.
    """
    from app.problema import montar_problema
    from seed.generate import gerar

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        gerar(session, seed=42)
        return montar_problema(session)
