"""Motor de alocacao.

Quatro camadas, separadas de proposito (ver docs/arquitetura.md):

- ``baseline``    guloso first-fit. E a "situacao inicial" da tela de comparacao,
                  a linha de base do AC-5 e o oraculo diferencial do MR-6.
- ``solver``      modelo CP-SAT. Restricoes rigidas viram restricoes do modelo,
                  restricoes flexiveis viram termos ponderados da funcao de custo.
- ``explainer``   pos-processamento. O CP-SAT devolve o otimo global, nao a razao
                  de uma alocacao individual -- sem esta camada o motor e caixa-preta.
- ``diagnostics`` por que cada equipe ficou de fora (AC-4).
- ``validator``   reavalia H1-H8 sobre o resultado, independente do solver (AC-2).

No D1 todas sao stubs. A implementacao entra no D2 (baseline, solver) e no D3
(explainer, diagnostics).
"""

from app.engine.types import (
    Alocacao,
    EquipeDTO,
    Pesos,
    Problema,
    Rejeicao,
    RestricaoDTO,
    SalaDTO,
    Solucao,
)
from app.engine.version import ENGINE_VERSION


class EtapaNaoImplementada(NotImplementedError):
    """Levantada pelos stubs do motor.

    Existe para que a API responda 501 com uma mensagem que diz *qual* etapa
    falta e *em que dia* ela entra, em vez de estourar um erro generico.
    """

    def __init__(self, etapa: str, dia: str) -> None:
        self.etapa = etapa
        self.dia = dia
        super().__init__(
            f"{etapa} ainda nao foi implementado (previsto para o {dia}). "
            f"O esqueleto do D1 entrega o modelo de dados, os endpoints e o CI; "
            f"a logica de alocacao entra em seguida."
        )


__all__ = [
    "ENGINE_VERSION",
    "Alocacao",
    "EquipeDTO",
    "EtapaNaoImplementada",
    "Pesos",
    "Problema",
    "Rejeicao",
    "RestricaoDTO",
    "SalaDTO",
    "Solucao",
]
