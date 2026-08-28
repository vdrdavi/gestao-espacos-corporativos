"""Conexao com o banco.

SQLite via SQLModel, com `create_all` no lifespan e sem Alembic: num prototipo
de uma semana o custo de manter migrations nao se paga, e o seed recria o banco
do zero. O preco e conhecido -- mudar o schema apaga os dados locais.
"""

import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  -- registra as tabelas no metadata

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./espacos.db")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def reset_db() -> None:
    """Derruba e recria o schema. Usado pelo seed e pelos cenarios."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session
