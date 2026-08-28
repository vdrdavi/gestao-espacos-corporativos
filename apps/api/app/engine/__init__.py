"""Motor de alocacao.

Camadas separadas de proposito (ver docs/arquitetura.md):

- ``restricoes``  le as RestricaoDTO e responde quais salas servem a uma equipe.
                  Compartilhado por baseline e solver -- nunca pelo validator.
- ``custo``       a funcao objetivo de docs/objetivo.md em Python puro, para
                  medir uma solucao pronta (o solver a constroi como objetivo).
- ``baseline``    guloso first-fit. E a "situacao inicial" da tela de comparacao,
                  a linha de base do AC-5 e o oraculo diferencial do MR-6.
- ``solver``      modelo CP-SAT. Restricoes rigidas viram restricoes do modelo,
                  restricoes flexiveis viram termos ponderados da funcao de custo.
- ``explainer``   pos-processamento. O CP-SAT devolve o otimo global, nao a razao
                  de uma alocacao individual -- sem esta camada o motor e caixa-preta.
- ``diagnostics`` por que cada equipe ficou de fora (AC-4).
- ``validator``   reavalia H1-H8 sobre o resultado, independente do solver (AC-2).

Todas as camadas estao implementadas. As duas do D3 -- ``explainer`` e
``diagnostics`` -- sao **pos-processamento**: rodam a partir de uma solucao
pronta, chamadas por ``routers/runs.py``, nunca de dentro de ``solver.alocar``.
Nao mudam quem foi para onde; so respondem por que.

``restricoes.rejeicoes()`` continua sendo o piso do motivo de uma equipe sem
sala: e a classificacao estatica que o solver ja produz, e o ``diagnostics`` so
a substitui quando tem algo melhor a dizer. `NaoAlocada` e append-only -- linha
gravada incompleta nunca mais e corrigida.
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

    Diz *qual* etapa falta e *em que dia* ela entra, em vez de estourar um erro
    generico -- e `POST /api/runs` transforma isso num registro de execucao com
    status ERRO, guardando a mensagem.

    **Hoje nenhuma camada do motor a levanta**: as sete estao implementadas. Fica
    como a convencao para os stubs do D5 e do D7, que e a regra 4 do CLAUDE.md.
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
