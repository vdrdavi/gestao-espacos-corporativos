"""Modelo CP-SAT.

Variaveis booleanas x[equipe, sala] com as restricoes rigidas H1-H8 e a funcao
de custo de docs/objetivo.md. A escolha por programacao por restricoes em vez
de uma heuristica artesanal e o que faz AC-1 e AC-2 valerem **por construcao**:
uma alocacao acima da capacidade nao e um bug improvavel, e um estado que o
modelo nao consegue representar.

STUB -- implementacao no D2.
"""

from app.engine import EtapaNaoImplementada
from app.engine.types import Problema, Solucao


def alocar(problema: Problema) -> Solucao:
    raise EtapaNaoImplementada("O solver CP-SAT", "D2")
