"""Tratamento de excecoes (secao 11 do enunciado).

Para cada equipe nao alocada, relaxa uma restricao por vez e reexecuta um
subproblema pequeno. A primeira restricao cuja remocao torna a equipe alocavel
e a *causa*; o encaminhamento sai de ENCAMINHAMENTO_PADRAO refinado com os
numeros do caso concreto.

O enunciado e explicito: o sistema nao deve esconder o problema nem produzir
uma alocacao invalida para inflar o indicador de sucesso.

STUB -- implementacao no D3.
"""

from app.engine import EtapaNaoImplementada
from app.engine.types import Problema, Rejeicao, Solucao


def diagnosticar(problema: Problema, solucao: Solucao) -> tuple[Rejeicao, ...]:
    raise EtapaNaoImplementada("O diagnostico de equipes nao alocadas", "D3")
