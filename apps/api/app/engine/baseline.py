"""Alocador guloso first-fit -- a "situacao inicial".

Percorre as equipes na ordem de chegada e coloca cada uma na primeira sala que
couber. Deliberadamente ingenuo: representa a distribuicao manual que o
enunciado descreve na secao 1, e por isso e ao mesmo tempo

- a coluna "Antes" da tela de comparacao (secao 8),
- a linha de base do AC-5 (a otimizacao nao pode ser pior que ela),
- o oraculo do teste diferencial MR-6.

STUB -- implementacao no D2.
"""

from app.engine import EtapaNaoImplementada
from app.engine.types import Problema, Solucao


def alocar(problema: Problema) -> Solucao:
    raise EtapaNaoImplementada("O alocador guloso (baseline)", "D2")
