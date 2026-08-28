"""Alocador guloso first-fit -- a "situacao inicial".

Percorre as equipes na ordem de chegada e coloca cada uma na primeira sala que
couber. Deliberadamente ingenuo: representa a distribuicao manual que o
enunciado descreve na secao 1, e por isso e ao mesmo tempo

- a coluna "Antes" da tela de comparacao (secao 8),
- a linha de base do AC-5 (a otimizacao nao pode ser pior que ela),
- o oraculo do teste diferencial MR-6.

**O guloso respeita H1-H8.** Ele e ingenuo na *escolha* (primeira sala que
couber, sem olhar o que vem depois), nunca na validade: `validator.violacoes()`
sobre a solucao dele tem que devolver lista vazia. Se pudesse violar restricoes,
seu custo cairia artificialmente -- restricao violada e restricao que nao custa
nada -- e o MR-6 (`custo do CP-SAT <= custo do guloso`) passaria a falhar por
construcao, e nao por bug. O oraculo do projeto se perderia justamente no teste
que existe para proteger o motor.

O que ele nao sabe fazer e *negociar*: quando duas equipes tem que ficar no mesmo
andar e nao ha par de salas livres, ele desiste das duas. E exatamente o que
acontece na planilha que ele representa.
"""

import time

from app.engine.custo import avaliar, custo_local
from app.engine.restricoes import Indice, indexar, rejeicoes, salas_viaveis
from app.engine.types import Alocacao, EquipeDTO, Problema, SalaDTO, Solucao
from app.engine.version import ENGINE_VERSION
from app.enums import StatusRun, Turno


class _Ocupacao:
    """Quem esta em cada sala, em cada slot, e quais setores estao em cada andar."""

    def __init__(self) -> None:
        self.por_slot: dict[tuple[int, str], int] = {}
        self.setores_no_andar: dict[int, set[int]] = {}

    def livre(self, sala: SalaDTO, equipe: EquipeDTO) -> bool:
        """H2 -- nenhum dos slots do turno da equipe pode estar tomado."""
        return all((sala.id, slot) not in self.por_slot for slot in equipe.turno.slots)

    def separacao_ok(self, indice: Indice, sala: SalaDTO, equipe: EquipeDTO) -> bool:
        """H7 -- o setor da equipe nao pode dividir andar com um setor separado."""
        no_andar = self.setores_no_andar.get(sala.andar, set())
        for setor_a, setor_b in indice.separacoes_rigidas:
            if equipe.setor_id == setor_a and setor_b in no_andar:
                return False
            if equipe.setor_id == setor_b and setor_a in no_andar:
                return False
        return True

    def ocupar(self, sala: SalaDTO, equipe: EquipeDTO) -> None:
        for slot in equipe.turno.slots:
            self.por_slot[sala.id, slot] = equipe.id
        self.setores_no_andar.setdefault(sala.andar, set()).add(equipe.setor_id)

    def liberar(self, sala: SalaDTO, equipe: EquipeDTO) -> None:
        for slot in equipe.turno.slots:
            self.por_slot.pop((sala.id, slot), None)
        # O setor pode ter outra equipe no mesmo andar; so sai quando nenhuma sobra.
        self.setores_no_andar.get(sala.andar, set()).discard(equipe.setor_id)


def alocar(problema: Problema) -> Solucao:
    inicio = time.perf_counter()

    indice = indexar(problema)
    # Ordem de chegada: e o que a distribuicao manual faz. Nada de ordenar por
    # tamanho ou prioridade -- isso ja seria uma heuristica, e o baseline
    # deixaria de representar o "antes".
    equipes = sorted(problema.equipes, key=lambda e: e.id)
    por_id = {e.id: e for e in equipes}
    viaveis = {
        e.id: sorted(salas_viaveis(problema, indice, e), key=lambda s: s.id) for e in equipes
    }

    ocupacao = _Ocupacao()
    escolhida: dict[int, SalaDTO] = {}

    # Pares que precisam ficar no mesmo andar sao resolvidos juntos: o guloso nao
    # tem como descobrir isso depois, ja tendo ocupado as salas.
    pares = [
        (a, b)
        for a, b in indice.proximidades_rigidas
        if a in por_id and b in por_id
    ]
    acopladas = {e for par in pares for e in par}

    def primeira_sala(equipe: EquipeDTO, andar: int | None = None) -> SalaDTO | None:
        for sala in viaveis[equipe.id]:
            if andar is not None and sala.andar != andar:
                continue
            if ocupacao.livre(sala, equipe) and ocupacao.separacao_ok(indice, sala, equipe):
                return sala
        return None

    for equipe_a, equipe_b in pares:
        a, b = por_id[equipe_a], por_id[equipe_b]
        for andar in sorted({s.andar for s in viaveis[a.id]}):
            sala_a = primeira_sala(a, andar)
            if sala_a is None:
                continue
            ocupacao.ocupar(sala_a, a)
            sala_b = primeira_sala(b, andar)
            if sala_b is not None:
                ocupacao.ocupar(sala_b, b)
                escolhida[a.id], escolhida[b.id] = sala_a, sala_b
                break
            # Nao fechou o par: desfaz e tenta o proximo andar.
            ocupacao.liberar(sala_a, a)

    for equipe in equipes:
        if equipe.id in acopladas or equipe.id in escolhida:
            continue
        sala = primeira_sala(equipe)
        if sala is not None:
            ocupacao.ocupar(sala, equipe)
            escolhida[equipe.id] = sala

    alocacoes = tuple(
        Alocacao(
            equipe_id=equipe_id,
            sala_id=sala.id,
            turno=Turno(por_id[equipe_id].turno),
            custo=custo_local(problema, equipe_id, sala.id),
            explicacao={},
            alternativas=[],
        )
        for equipe_id, sala in sorted(escolhida.items())
    )

    return Solucao(
        alocacoes=alocacoes,
        nao_alocadas=rejeicoes(problema, indice, alocacoes),
        # Mesma funcao de custo do solver: e isso que torna o MR-6 uma comparacao
        # e nao uma coincidencia de unidades.
        custo=avaliar(problema, alocacoes, indice),
        # FEASIBLE, nunca OPTIMAL: o guloso encontra uma solucao valida e nao tem
        # como afirmar que ela e a melhor. Os testes metamorficos so comparam
        # custos entre execucoes OPTIMAL, e o baseline nao pode se passar por uma.
        status=StatusRun.FEASIBLE,
        duracao_ms=int((time.perf_counter() - inicio) * 1000),
        engine_version=ENGINE_VERSION,
    )
