"""Schemas de entrada e saida da API.

Separados dos models porque a forma que entra pelo HTTP nao e a forma que vai
para o banco: os schemas de escrita nao aceitam `id`, e os de atualizacao tem
todos os campos opcionais.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import (
    AlvoRestricao,
    CodigoMotivo,
    StatusRun,
    TipoIntervencao,
    TipoRestricao,
    TipoSala,
    Turno,
)

# --------------------------------------------------------------------------
# Setor
# --------------------------------------------------------------------------


class SetorCreate(BaseModel):
    nome: str
    coordenador: str
    total_funcionarios: int = Field(ge=0)


class SetorUpdate(BaseModel):
    nome: str | None = None
    coordenador: str | None = None
    total_funcionarios: int | None = Field(default=None, ge=0)


class SetorRead(SetorCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --------------------------------------------------------------------------
# Sala
# --------------------------------------------------------------------------


class SalaCreate(BaseModel):
    codigo: str
    andar: int = Field(ge=1, le=9)
    capacidade: int = Field(gt=0)
    tipo: TipoSala
    recursos: list[str] = []
    acessivel: bool = False
    disponivel: bool = True
    reservada_para_setor_id: int | None = None


class SalaUpdate(BaseModel):
    codigo: str | None = None
    andar: int | None = Field(default=None, ge=1, le=9)
    capacidade: int | None = Field(default=None, gt=0)
    tipo: TipoSala | None = None
    recursos: list[str] | None = None
    acessivel: bool | None = None
    disponivel: bool | None = None
    reservada_para_setor_id: int | None = None


class SalaRead(SalaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --------------------------------------------------------------------------
# Equipe
# --------------------------------------------------------------------------


class EquipeCreate(BaseModel):
    setor_id: int
    nome: str
    tamanho: int = Field(gt=0)
    turno: Turno = Turno.INTEGRAL
    recursos_requeridos: list[str] = []
    exige_acessibilidade: bool = False
    andar_preferido: int | None = Field(default=None, ge=1, le=9)
    prioridade: int = Field(default=3, ge=1, le=5)


class EquipeUpdate(BaseModel):
    setor_id: int | None = None
    nome: str | None = None
    tamanho: int | None = Field(default=None, gt=0)
    turno: Turno | None = None
    recursos_requeridos: list[str] | None = None
    exige_acessibilidade: bool | None = None
    andar_preferido: int | None = Field(default=None, ge=1, le=9)
    prioridade: int | None = Field(default=None, ge=1, le=5)


class EquipeRead(EquipeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --------------------------------------------------------------------------
# Restricao
# --------------------------------------------------------------------------


class RestricaoCreate(BaseModel):
    tipo: TipoRestricao
    alvo_tipo: AlvoRestricao
    alvo_id: int | None = None
    parametros: dict = {}
    rigida: bool = True
    peso: int = Field(default=0, ge=0)
    descricao: str = ""


class RestricaoUpdate(BaseModel):
    tipo: TipoRestricao | None = None
    alvo_tipo: AlvoRestricao | None = None
    alvo_id: int | None = None
    parametros: dict | None = None
    rigida: bool | None = None
    peso: int | None = Field(default=None, ge=0)
    descricao: str | None = None


class RestricaoRead(RestricaoCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --------------------------------------------------------------------------
# Execucao do motor
# --------------------------------------------------------------------------


class PesosInput(BaseModel):
    """Pesos da funcao de custo. Ver docs/objetivo.md."""

    nao_alocada: int = Field(default=10_000, ge=0, description="W_NA")
    ociosidade: int = Field(default=1, ge=0, description="W_OC")
    proximidade: int = Field(default=50, ge=0, description="W_PR")
    andar_preferido: int = Field(default=20, ge=0, description="W_AP")
    restricao_flexivel: int = Field(default=200, ge=0, description="W_RS")


class RunCreate(BaseModel):
    usuario: str = "coordenador-geral"
    pesos: PesosInput = PesosInput()
    seed: int = 42
    limite_segundos: float = Field(default=10.0, gt=0, le=300)


class AssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    equipe_id: int
    sala_id: int
    turno: Turno
    custo: int
    explicacao: dict
    alternativas: list


class NaoAlocadaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    equipe_id: int
    codigo_motivo: CodigoMotivo
    causa: str
    encaminhamento: str


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    criado_em: datetime
    usuario: str
    engine_version: str
    seed: int | None
    pesos: dict
    hash_entrada: str
    duracao_ms: int
    status: StatusRun
    metricas: dict
    metricas_baseline: dict
    erro: str | None


class RunDetalhe(RunRead):
    snapshot_entrada: dict
    alocacoes: list[AssignmentRead] = []
    nao_alocadas: list[NaoAlocadaRead] = []


# --------------------------------------------------------------------------
# Intervencao humana e auditoria
# --------------------------------------------------------------------------


class IntervencaoCreate(BaseModel):
    usuario: str
    tipo: TipoIntervencao
    antes: dict = {}
    depois: dict = {}
    justificativa: str = ""


class IntervencaoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    run_id: int
    criado_em: datetime
    usuario: str
    tipo: TipoIntervencao
    antes: dict
    depois: dict
    justificativa: str
    alerta: str | None


# --------------------------------------------------------------------------
# Observabilidade
# --------------------------------------------------------------------------


class MetricasRead(BaseModel):
    """Painel "Monitoramento do Motor de Alocacao" (secao 13)."""

    execucoes_total: int
    execucoes_com_erro: int
    duracao_ultima_ms: int | None
    duracao_p50_ms: int | None
    duracao_p95_ms: int | None
    ocupacao_media_pct: float | None
    taxa_alocacao_pct: float | None
    equipes_nao_alocadas: int | None
    violacoes: int | None
    intervencoes_total: int
    intervencoes_por_execucao: float | None
    engine_version: str


class CenarioRead(BaseModel):
    nome: str
    titulo: str
    descricao: str
