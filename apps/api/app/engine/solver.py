"""Modelo CP-SAT.

Variaveis booleanas x[equipe, sala] com as restricoes rigidas H1-H8 e a funcao
de custo de docs/objetivo.md. A escolha por programacao por restricoes em vez
de uma heuristica artesanal e o que faz AC-1 e AC-2 valerem **por construcao**:
uma alocacao acima da capacidade nao e um bug improvavel, e um estado que o
modelo nao consegue representar.

Como cada restricao rigida entra:

    H1  capacidade            a variavel x[e,s] nem e criada
    H2  exclusividade/turno   soma <= 1 por sala e por slot elementar
    H3  recursos              x[e,s] nao e criada
    H4  acessibilidade        x[e,s] nao e criada
    H5  andar permitido       x[e,s] nao e criada
    H6  sala reservada        x[e,s] nao e criada
    H7  separacao de setores  ocupa[setor,andar]: um dos dois por andar
    H8  uma sala por equipe   soma_s x[e,s] <= 1  (<=, nao ==: ver docs/objetivo.md)

H1 e H3-H6 dependem so do par (equipe, sala) e viram *ausencia de variavel* --
o modelo fica menor e o estado invalido deixa de existir. H2, H7 e proximidade
dependem de quem mais esta na sala ou no andar, e por isso viram restricoes.

**O modelo nunca e infactivel.** Com H8 em `<=`, deixar todas as equipes de fora
e sempre uma solucao viavel -- caríssima, mas viavel. E deliberado: a secao 11 do
enunciado pede que o sistema *mostre* o que nao conseguiu resolver, e "2 equipes
sem sala, motivo CONFLITO_RESTRICOES" informa muito mais que um INFEASIBLE seco.
"""

import time

from ortools.sat.python import cp_model

from app.engine.custo import DISTANCIA_MAXIMA, custo_local
from app.engine.restricoes import indexar, rejeicoes, salas_viaveis
from app.engine.types import Alocacao, EquipeDTO, Problema, SalaDTO, Solucao
from app.engine.version import ENGINE_VERSION
from app.enums import StatusRun, Turno

SLOTS = ("manha", "tarde")

STATUS_CP_SAT = {
    cp_model.OPTIMAL: StatusRun.OPTIMAL,
    cp_model.FEASIBLE: StatusRun.FEASIBLE,
    cp_model.INFEASIBLE: StatusRun.INFEASIBLE,
    cp_model.UNKNOWN: StatusRun.UNKNOWN,
    cp_model.MODEL_INVALID: StatusRun.ERRO,
}


def _chave_equipe(equipe: EquipeDTO) -> tuple:
    """Ordem canonica das equipes -- por conteudo, nunca por nome.

    Dois problemas identicos a menos de nome e ordem de chegada produzem, assim,
    exatamente o mesmo modelo: a entrada do CP-SAT deixa de depender de como as
    linhas sairam do banco.

    Medido: hoje o CP-SAT ja devolve as mesmas metricas no cenario de referencia
    mesmo ordenando por nome -- o presolve normaliza o modelo. A ordem canonica e
    defesa em profundidade, nao a unica coisa que sustenta o MR-4; ela protege o
    dia em que o solver parar antes de provar otimalidade, quando o desempate
    passa a depender de onde a busca comecou.
    """
    return (
        equipe.tamanho,
        equipe.turno.value,
        equipe.prioridade,
        tuple(sorted(equipe.recursos_requeridos)),
        equipe.exige_acessibilidade,
        equipe.andar_preferido if equipe.andar_preferido is not None else 0,
        equipe.setor_id,
        equipe.id,
    )


def _chave_sala(sala: SalaDTO) -> tuple:
    return (
        sala.andar,
        sala.capacidade,
        sala.tipo.value,
        tuple(sorted(sala.recursos)),
        sala.acessivel,
        sala.disponivel,
        sala.reservada_para_setor_id or 0,
        sala.id,
    )


def alocar(problema: Problema, hint: Solucao | None = None) -> Solucao:
    """Resolve o problema de alocacao e devolve a melhor solucao encontrada.

    `hint` alimenta `AddHint` com uma solucao ja conhecida. E a mitigacao (c) dos
    testes metamorficos: numa entrada relaxada (uma sala a mais, uma restricao a
    menos) a solucao original continua viavel, entao partir dela garante que o
    solver nunca devolva algo pior por ter parado cedo -- o que faria MR-2 e MR-3
    falharem por timeout em vez de por bug.
    """
    inicio = time.perf_counter()

    indice = indexar(problema)
    equipes = sorted(problema.equipes, key=_chave_equipe)
    salas = sorted((s for s in problema.salas if s.disponivel), key=_chave_sala)
    andares = sorted({s.andar for s in salas})

    modelo = cp_model.CpModel()

    # ---------------------------------------------------------------- H1, H3-H6
    # A variavel so existe para pares viaveis: o estado invalido nao e proibido,
    # ele nao e representavel.
    x: dict[tuple[int, int], cp_model.IntVar] = {}
    viaveis_por_equipe: dict[int, list[SalaDTO]] = {}
    for equipe in equipes:
        viaveis = [s for s in salas_viaveis(problema, indice, equipe) if s.disponivel]
        viaveis.sort(key=_chave_sala)
        viaveis_por_equipe[equipe.id] = viaveis
        for sala in viaveis:
            x[equipe.id, sala.id] = modelo.new_bool_var(f"x_{equipe.id}_{sala.id}")

    # ---------------------------------------------------------------------- H8
    alocada: dict[int, cp_model.IntVar] = {}
    for equipe in equipes:
        variavel = modelo.new_bool_var(f"alocada_{equipe.id}")
        modelo.add(
            sum(x[equipe.id, s.id] for s in viaveis_por_equipe[equipe.id]) == variavel
        )
        alocada[equipe.id] = variavel

    # ---------------------------------------------------------------------- H2
    # Uma sala serve duas equipes em turnos diferentes, mas nunca duas no mesmo
    # slot. INTEGRAL consome os dois slots (Turno.slots).
    for sala in salas:
        for slot in SLOTS:
            concorrentes = [
                x[e.id, sala.id]
                for e in equipes
                if (e.id, sala.id) in x and slot in e.turno.slots
            ]
            if len(concorrentes) > 1:
                modelo.add(sum(concorrentes) <= 1)

    # ---------------------------------------------------------------------- H7
    setores_separados = {
        setor
        for par in indice.separacoes_rigidas
        for setor in par
    } | {
        setor
        for a, b, _ in indice.separacoes_flexiveis
        for setor in (a, b)
    }
    ocupa: dict[tuple[int, int], cp_model.IntVar] = {}
    if setores_separados:
        for setor in sorted(setores_separados):
            for andar in andares:
                ocupa[setor, andar] = modelo.new_bool_var(f"ocupa_{setor}_{andar}")
        for equipe in equipes:
            if equipe.setor_id not in setores_separados:
                continue
            for sala in viaveis_por_equipe[equipe.id]:
                modelo.add_implication(
                    x[equipe.id, sala.id], ocupa[equipe.setor_id, sala.andar]
                )
        for setor_a, setor_b in indice.separacoes_rigidas:
            for andar in andares:
                modelo.add(ocupa[setor_a, andar] + ocupa[setor_b, andar] <= 1)

    # ------------------------------------------------- proximidade (andar por equipe)
    # A intersecao com as equipes do problema nao e defensiva: uma restricao pode
    # referenciar equipe que nao esta aqui -- porque foi removida do cadastro, ou
    # porque este e um recorte (o `diagnostics` monta subproblemas). Sem ela,
    # criava-se variavel de andar para uma equipe sem variavel `alocada`.
    presentes = {e.id for e in equipes}
    equipes_com_andar = (
        {e for par in indice.proximidades_rigidas for e in par}
        | {e for a, b, _ in indice.proximidades_flexiveis for e in (a, b)}
    ) & presentes

    z: dict[tuple[int, int], cp_model.IntVar] = {}
    andar_da_equipe: dict[int, cp_model.IntVar] = {}
    for equipe_id in sorted(equipes_com_andar):
        viaveis = viaveis_por_equipe.get(equipe_id, [])
        for andar in andares:
            variavel = modelo.new_bool_var(f"z_{equipe_id}_{andar}")
            modelo.add(
                sum(x[equipe_id, s.id] for s in viaveis if s.andar == andar) == variavel
            )
            z[equipe_id, andar] = variavel
        # 0 quando a equipe nao e alocada -- por isso o termo de proximidade so
        # vale quando as duas equipes tem sala.
        posicao = modelo.new_int_var(0, max(andares, default=0), f"andar_{equipe_id}")
        modelo.add(posicao == sum(andar * z[equipe_id, andar] for andar in andares))
        andar_da_equipe[equipe_id] = posicao

    # Proximidade rigida: mesmo andar, ou as duas de fora. Nao ha terceira opcao
    # -- e o que torna o cenario estresse-conflito-restricoes legivel.
    for equipe_a, equipe_b in indice.proximidades_rigidas:
        if equipe_a in andar_da_equipe and equipe_b in andar_da_equipe:
            for andar in andares:
                modelo.add(z[equipe_a, andar] == z[equipe_b, andar])

    # ------------------------------------------------------------------- custo
    pesos = problema.pesos
    termos = []

    # W_NA -- domina todos os outros: ver a regra de dominancia em docs/objetivo.md.
    termos += [
        pesos.nao_alocada * equipe.prioridade * (1 - alocada[equipe.id]) for equipe in equipes
    ]

    # W_OC -- assentos ociosos.
    termos += [
        pesos.ociosidade * (sala.capacidade - equipe.tamanho) * x[equipe.id, sala.id]
        for equipe in equipes
        for sala in viaveis_por_equipe[equipe.id]
    ]

    # W_AP -- andar preferido nao atendido.
    termos += [
        pesos.andar_preferido * x[equipe.id, sala.id]
        for equipe in equipes
        if equipe.andar_preferido is not None
        for sala in viaveis_por_equipe[equipe.id]
        if sala.andar != equipe.andar_preferido
    ]

    # W_PR -- distancia entre equipes relacionadas, so quando as duas foram
    # alocadas. Sem o "so quando", uma equipe sem sala (andar 0) apareceria a 7
    # andares da parceira e o solver pagaria duas vezes pelo mesmo problema.
    for equipe_a, equipe_b, peso in indice.proximidades_flexiveis:
        if equipe_a not in andar_da_equipe or equipe_b not in andar_da_equipe:
            continue
        diferenca = modelo.new_int_var(-DISTANCIA_MAXIMA - 1, DISTANCIA_MAXIMA + 1,
                                       f"dif_{equipe_a}_{equipe_b}")
        modelo.add(diferenca == andar_da_equipe[equipe_a] - andar_da_equipe[equipe_b])
        distancia = modelo.new_int_var(0, DISTANCIA_MAXIMA + 1, f"dist_{equipe_a}_{equipe_b}")
        modelo.add_abs_equality(distancia, diferenca)

        ambas = modelo.new_bool_var(f"ambas_{equipe_a}_{equipe_b}")
        modelo.add(ambas <= alocada[equipe_a])
        modelo.add(ambas <= alocada[equipe_b])
        modelo.add(ambas >= alocada[equipe_a] + alocada[equipe_b] - 1)

        penalidade = modelo.new_int_var(0, DISTANCIA_MAXIMA + 1, f"pen_{equipe_a}_{equipe_b}")
        modelo.add(penalidade >= distancia - (DISTANCIA_MAXIMA + 1) * (1 - ambas))
        termos.append(peso * penalidade)

    # W_RS -- restricoes flexiveis violadas. Separacao de setores marcada como
    # flexivel: cada andar compartilhado custa uma violacao.
    for setor_a, setor_b, peso in indice.separacoes_flexiveis:
        for andar in andares:
            violacao = modelo.new_bool_var(f"viol_sep_{setor_a}_{setor_b}_{andar}")
            modelo.add(violacao >= ocupa[setor_a, andar] + ocupa[setor_b, andar] - 1)
            termos.append(peso * violacao)

    modelo.minimize(sum(termos))

    # -------------------------------------------------------------------- hint
    if hint is not None:
        for alocacao in hint.alocacoes:
            chave = (alocacao.equipe_id, alocacao.sala_id)
            if chave in x:
                modelo.add_hint(x[chave], 1)

    # ------------------------------------------------------------------- solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = problema.limite_segundos
    # Determinismo (AC-7). Medido no cenario de referencia: com 8 workers o
    # resultado tambem e estavel, e roda em ~260ms contra ~600ms. O worker unico
    # e mantido porque essa estabilidade so vale enquanto o solver chega ao otimo:
    # quando ele para no limite de tempo, a solucao devolvida e a do worker que
    # estava na frente -- e isso depende da carga da maquina, nao da entrada.
    # 600ms dentro de um orcamento de 10s (AC-6) e um preco barato por
    # reprodutibilidade que nao depende de sorte.
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = problema.seed

    status = solver.solve(modelo)
    duracao_ms = int((time.perf_counter() - inicio) * 1000)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Nao houve solucao dentro do limite. Nao se inventa alocacao: todas as
        # equipes saem como nao alocadas, com o motivo que a entrada permite dizer.
        return Solucao(
            alocacoes=(),
            nao_alocadas=rejeicoes(problema, indice, ()),
            custo=pesos.nao_alocada * sum(e.prioridade for e in problema.equipes),
            status=STATUS_CP_SAT.get(status, StatusRun.UNKNOWN),
            duracao_ms=duracao_ms,
            engine_version=ENGINE_VERSION,
        )

    alocacoes = tuple(
        Alocacao(
            equipe_id=equipe.id,
            sala_id=sala.id,
            turno=Turno(equipe.turno),
            custo=custo_local(problema, equipe.id, sala.id),
            # Vazios de proposito: a decomposicao termo a termo e as alternativas
            # descartadas sao pos-processamento (`explainer`), e o solver roda
            # dezenas de vezes nos testes metamorficos sem precisar delas. Quem
            # chama o explainer e `routers/runs.py`, antes de gravar.
            explicacao={},
            alternativas=[],
        )
        for equipe in sorted(equipes, key=lambda e: e.id)
        for sala in viaveis_por_equipe[equipe.id]
        if solver.value(x[equipe.id, sala.id])
    )

    return Solucao(
        alocacoes=alocacoes,
        nao_alocadas=rejeicoes(problema, indice, alocacoes),
        # `round`, nunca `int`: o objetivo e inteiro por construcao, mas
        # `objective_value` chega como float e o CP-SAT devolve 14.999999... para
        # um custo de 15. Truncar produzia um custo *menor* que o real, e
        # `avaliar(problema, alocacoes) == solucao.custo` -- o contrato de que a
        # explicacao mostrada e a conta que o solver minimizou -- quebrava por um.
        custo=round(solver.objective_value),
        status=STATUS_CP_SAT[status],
        duracao_ms=duracao_ms,
        engine_version=ENGINE_VERSION,
    )
