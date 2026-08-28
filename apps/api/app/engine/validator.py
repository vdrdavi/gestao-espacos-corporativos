"""Validador independente das restricoes rigidas (AC-2).

Reavalia H1-H8 sobre uma solucao pronta, **sem** usar o codigo que construiu o
modelo CP-SAT. A independencia e o ponto: se o mesmo codigo que monta as
restricoes tambem as verifica, um erro de modelagem passa pelos dois lados.

Por isso este arquivo deve ser escrito por quem *nao* escreveu solver.py.
Tambem e o que roda quando o Coordenador Geral altera uma alocacao a mao -- o
sistema avisa que a alteracao viola uma restricao, registra o alerta, e nao
bloqueia: a decisao final e humana (secao 10).

STUB -- implementacao no D2.
"""

from app.engine import EtapaNaoImplementada
from app.engine.types import Problema, Solucao


def violacoes(problema: Problema, solucao: Solucao) -> list[dict]:
    """Lista de violacoes de restricao rigida. Vazia = solucao valida."""
    raise EtapaNaoImplementada("O validador independente de restricoes", "D2")
