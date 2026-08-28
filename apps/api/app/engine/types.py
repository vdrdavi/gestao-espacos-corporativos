"""Contrato interno do motor.

O motor nao conhece SQLModel. Recebe um `Problema` de dataclasses puras e
devolve uma `Solucao`. Duas razoes praticas:

1. baseline.py e solver.py implementam a *mesma* assinatura, o que torna o
   teste diferencial MR-6 (custo do CP-SAT <= custo do guloso) trivial.
2. Os testes metamorficos precisam transformar a entrada (adicionar sala,
   remover restricao, embaralhar ordem) sem passar por banco de dados.
"""

from dataclasses import dataclass, field

from app.enums import CodigoMotivo, StatusRun, TipoRestricao, TipoSala, Turno


@dataclass(frozen=True, slots=True)
class Pesos:
    """Pesos da funcao de custo. Ver docs/objetivo.md.

    Sao dados de entrada, nao constantes: o Coordenador Geral pode ajusta-los
    pela UI e reexecutar, e cada Run grava os pesos que usou.
    """

    nao_alocada: int = 10_000  # W_NA
    ociosidade: int = 1  # W_OC
    proximidade: int = 50  # W_PR
    andar_preferido: int = 20  # W_AP
    restricao_flexivel: int = 200  # W_RS

    def dominancia_ok(self, capacidade_total: int, prioridade_minima: int = 1) -> bool:
        """Verifica a regra de dominancia.

        Minimizar assentos ociosos, sozinho, ensina o solver a **deixar equipes
        de fora**: uma equipe nao alocada contribui com zero ociosidade, entao
        esconder equipes "melhora" o custo. Para que isso nunca compense,
        alocar qualquer equipe na pior sala possivel tem que custar menos do
        que nao aloca-la:

            W_NA * prioridade_minima > W_OC * capacidade_total

        Violar isto nao gera erro de execucao -- gera uma solucao silenciosamente
        errada. Por isso vira teste automatizado (AC-5 / test_weight_dominance).
        """
        return self.nao_alocada * prioridade_minima > self.ociosidade * capacidade_total

    def to_dict(self) -> dict[str, int]:
        return {
            "W_NA": self.nao_alocada,
            "W_OC": self.ociosidade,
            "W_PR": self.proximidade,
            "W_AP": self.andar_preferido,
            "W_RS": self.restricao_flexivel,
        }


@dataclass(frozen=True, slots=True)
class SalaDTO:
    id: int
    codigo: str
    andar: int
    capacidade: int
    tipo: TipoSala
    recursos: frozenset[str] = frozenset()
    acessivel: bool = False
    disponivel: bool = True
    reservada_para_setor_id: int | None = None


@dataclass(frozen=True, slots=True)
class EquipeDTO:
    id: int
    nome: str
    setor_id: int
    tamanho: int
    turno: Turno = Turno.INTEGRAL
    recursos_requeridos: frozenset[str] = frozenset()
    exige_acessibilidade: bool = False
    andar_preferido: int | None = None
    prioridade: int = 3


@dataclass(frozen=True, slots=True)
class RestricaoDTO:
    id: int
    tipo: TipoRestricao
    parametros: dict
    rigida: bool = True
    peso: int = 0
    alvo_id: int | None = None


@dataclass(frozen=True, slots=True)
class Problema:
    salas: tuple[SalaDTO, ...]
    equipes: tuple[EquipeDTO, ...]
    restricoes: tuple[RestricaoDTO, ...] = ()
    pesos: Pesos = field(default_factory=Pesos)
    limite_segundos: float = 10.0
    seed: int = 42

    @property
    def capacidade_total(self) -> int:
        return sum(s.capacidade for s in self.salas if s.disponivel)


@dataclass(frozen=True, slots=True)
class Alocacao:
    equipe_id: int
    sala_id: int
    turno: Turno
    custo: int = 0
    explicacao: dict = field(default_factory=dict)
    alternativas: list = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Rejeicao:
    equipe_id: int
    codigo_motivo: CodigoMotivo
    causa: str
    encaminhamento: str


@dataclass(frozen=True, slots=True)
class Solucao:
    alocacoes: tuple[Alocacao, ...]
    nao_alocadas: tuple[Rejeicao, ...]
    custo: int
    status: StatusRun
    duracao_ms: int
    engine_version: str

    def metricas(self, problema: Problema) -> dict:
        """Indicadores do dashboard (secao 7) calculados sobre esta solucao."""
        salas_por_id = {s.id: s for s in problema.salas}
        equipes_por_id = {e.id: e for e in problema.equipes}

        capacidade_usada = sum(salas_por_id[a.sala_id].capacidade for a in self.alocacoes)
        pessoas_alocadas = sum(equipes_por_id[a.equipe_id].tamanho for a in self.alocacoes)
        ociosos = capacidade_usada - pessoas_alocadas
        ocupacao = (pessoas_alocadas / capacidade_usada * 100) if capacidade_usada else 0.0

        salas_disponiveis = [s for s in problema.salas if s.disponivel]
        ocupadas = {a.sala_id for a in self.alocacoes}

        return {
            "equipes_total": len(problema.equipes),
            "equipes_alocadas": len(self.alocacoes),
            "equipes_nao_alocadas": len(self.nao_alocadas),
            "pessoas_alocadas": pessoas_alocadas,
            "pessoas_nao_alocadas": sum(
                equipes_por_id[r.equipe_id].tamanho for r in self.nao_alocadas
            ),
            "assentos_ociosos": ociosos,
            "ocupacao_media_pct": round(ocupacao, 1),
            "salas_total": len(salas_disponiveis),
            "salas_ocupadas": len(ocupadas),
            "salas_livres": len(salas_disponiveis) - len(ocupadas),
            "utilizacao_salas_pct": round(
                len(ocupadas) / len(salas_disponiveis) * 100 if salas_disponiveis else 0.0, 1
            ),
            "capacidade_total": problema.capacidade_total,
            "custo": self.custo,
        }
