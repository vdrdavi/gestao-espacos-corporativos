"""Modelo de dados.

Duas familias de tabela, com regras diferentes:

- **Entrada** (Sala, Setor, Equipe, Restricao): mutaveis, CRUD completo.
- **Registro** (Run, Assignment, NaoAlocada, Intervencao): *append-only*.
  Nenhum router expoe PATCH ou DELETE sobre elas. Uma alteracao manual do
  Coordenador Geral cria uma Intervencao nova em vez de editar o Assignment
  original -- e isso que faz a governanca (secao 12 do enunciado) responder
  "quem executou, quando, com quais dados e qual foi o resultado" em vez de
  virar uma tabela de log decorativa.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

from app.enums import (
    AlvoRestricao,
    CodigoMotivo,
    StatusRun,
    TipoIntervencao,
    TipoRestricao,
    TipoSala,
    Turno,
)


def agora() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------
# Entrada
# --------------------------------------------------------------------------


class Setor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nome: str = Field(index=True, unique=True)
    coordenador: str
    total_funcionarios: int

    equipes: list["Equipe"] = Relationship(back_populates="setor")


class Sala(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(index=True, unique=True)
    andar: int = Field(index=True, ge=1, le=9)
    capacidade: int = Field(gt=0)
    tipo: TipoSala
    recursos: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    acessivel: bool = False
    disponivel: bool = True
    #: H6 -- quando preenchido, so equipes deste setor podem ocupar a sala.
    reservada_para_setor_id: int | None = Field(default=None, foreign_key="setor.id")


class Equipe(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    setor_id: int = Field(foreign_key="setor.id", index=True)
    nome: str = Field(index=True)
    tamanho: int = Field(gt=0)
    turno: Turno = Field(default=Turno.INTEGRAL)
    recursos_requeridos: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    exige_acessibilidade: bool = False
    andar_preferido: int | None = Field(default=None, ge=1, le=9)
    #: 1 = menor prioridade, 5 = maior. Multiplica o custo de nao alocar.
    prioridade: int = Field(default=3, ge=1, le=5)

    setor: Setor | None = Relationship(back_populates="equipes")


class Restricao(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    tipo: TipoRestricao
    alvo_tipo: AlvoRestricao
    alvo_id: int | None = Field(default=None)
    #: Payload especifico do tipo. Ex.: {"andares": [7, 8]} para ANDAR_PERMITIDO,
    #: {"equipe_a": 3, "equipe_b": 9} para PROXIMIDADE.
    parametros: dict = Field(default_factory=dict, sa_column=Column(JSON))
    #: Rigida vira restricao do modelo CP-SAT (nunca violavel); flexivel vira
    #: termo ponderado da funcao de custo. Ver docs/objetivo.md.
    rigida: bool = True
    peso: int = Field(default=0, ge=0)
    descricao: str = ""


# --------------------------------------------------------------------------
# Registro (append-only)
# --------------------------------------------------------------------------


class Run(SQLModel, table=True):
    """Uma execucao do motor. Nunca sofre UPDATE."""

    id: int | None = Field(default=None, primary_key=True)
    criado_em: datetime = Field(default_factory=agora, index=True)
    usuario: str
    engine_version: str
    seed: int | None = None
    pesos: dict = Field(default_factory=dict, sa_column=Column(JSON))
    #: sha256 do snapshot -- permite provar que duas execucoes viram a mesma
    #: entrada (base do AC-7, reprodutibilidade).
    hash_entrada: str = Field(index=True)
    snapshot_entrada: dict = Field(default_factory=dict, sa_column=Column(JSON))
    duracao_ms: int = 0
    status: StatusRun = StatusRun.UNKNOWN
    metricas: dict = Field(default_factory=dict, sa_column=Column(JSON))
    #: Metricas da alocacao gulosa sobre a mesma entrada. E a coluna "Antes" da
    #: tela de comparacao e a linha de base do AC-5.
    metricas_baseline: dict = Field(default_factory=dict, sa_column=Column(JSON))
    erro: str | None = None


class Assignment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id", index=True)
    equipe_id: int = Field(foreign_key="equipe.id")
    sala_id: int = Field(foreign_key="sala.id")
    turno: Turno
    custo: int = 0
    #: Decomposicao do custo termo a termo. O AC-3 exige que esteja preenchida
    #: em 100% dos assignments.
    explicacao: dict = Field(default_factory=dict, sa_column=Column(JSON))
    #: Salas descartadas com o respectivo custo -- o "alternativas avaliadas: 5"
    #: da secao 9 do enunciado.
    alternativas: list = Field(default_factory=list, sa_column=Column(JSON))


class NaoAlocada(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id", index=True)
    equipe_id: int = Field(foreign_key="equipe.id")
    codigo_motivo: CodigoMotivo
    causa: str
    encaminhamento: str


class Intervencao(SQLModel, table=True):
    """Registro de decisao humana sobre uma recomendacao (secao 10)."""

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="run.id", index=True)
    criado_em: datetime = Field(default_factory=agora, index=True)
    usuario: str
    tipo: TipoIntervencao
    antes: dict = Field(default_factory=dict, sa_column=Column(JSON))
    depois: dict = Field(default_factory=dict, sa_column=Column(JSON))
    justificativa: str = ""
    #: Preenchido quando uma alteracao manual viola uma restricao rigida. O
    #: sistema avisa e registra, mas nao bloqueia: a decisao final e humana.
    alerta: str | None = None
