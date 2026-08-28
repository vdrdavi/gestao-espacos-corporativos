"""Explicabilidade (secao 9 do enunciado).

O CP-SAT devolve o otimo global, nao a razao de uma alocacao individual. Esta
camada reavalia, para cada equipe, as salas viaveis com a **mesma** funcao de
custo do solver e devolve as N melhores com o custo decomposto termo a termo.

E o que transforma "o algoritmo decidiu" em "esta sala custa 4 e a segunda
melhor custa 34, porque desperdica 14 assentos e ignora o andar preferido".

STUB -- implementacao no D3.
"""

from app.engine import EtapaNaoImplementada
from app.engine.types import Alocacao, Problema, Solucao

TOP_N_ALTERNATIVAS = 5


def explicar(problema: Problema, solucao: Solucao) -> tuple[Alocacao, ...]:
    raise EtapaNaoImplementada("A geracao de justificativas (explainer)", "D3")
