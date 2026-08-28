"""Explicabilidade (secao 9 do enunciado).

O CP-SAT devolve o otimo global, nao a razao de uma alocacao individual. Esta
camada reavalia, para cada equipe, as salas viaveis com a **mesma** funcao de
custo do solver e devolve as N melhores com o custo decomposto termo a termo.

E o que transforma "o algoritmo decidiu" em "esta sala custa 4 e a segunda
melhor custa 34, porque desperdica 14 assentos e ignora o andar preferido".

**O numero mostrado e o custo marginal**: quanto a equipe naquela sala acrescenta
ao custo com as demais alocacoes fixas (`custo.custo_marginal`). E o unico numero
que torna duas salas comparaveis entre si -- uma reparticao do custo total nao
seria, porque os termos de par nao pertencem a uma equipe so.

**As alternativas sao reais.** So entram salas que a equipe poderia de fato
ocupar naquela solucao: viaveis por H1/H3-H6 (via `restricoes.salas_viaveis`, o
mesmo filtro que solver e baseline usam), livres no turno dela (H2) e sem quebrar
H7 nem a proximidade rigida. Oferecer como alternativa uma sala ocupada por outra
equipe seria explicar a decisao com uma opcao que nunca existiu.

Executado pelo router *depois* do solver, nunca dentro dele: `solver.alocar` roda
dezenas de vezes nos testes metamorficos e nao pode carregar pos-processamento.
"""

from dataclasses import replace

from app.engine.custo import Contexto, Termo, contexto, custo_marginal
from app.engine.restricoes import Indice, indexar, salas_viaveis
from app.engine.types import Alocacao, EquipeDTO, Problema, SalaDTO, Solucao

#: Quantas salas descartadas acompanham cada recomendacao (docs/objetivo.md).
TOP_N_ALTERNATIVAS = 5


def explicar(problema: Problema, solucao: Solucao) -> tuple[Alocacao, ...]:
    """Devolve as alocacoes com `explicacao` e `alternativas` preenchidas.

    Nao altera sala nem custo: a decisao ja foi tomada pelo solver, aqui so se
    reconstroi o porque dela.
    """
    indice = indexar(problema)
    ctx = contexto(problema, solucao.alocacoes)
    equipes = {e.id: e for e in problema.equipes}
    salas = {s.id: s for s in problema.salas}

    explicadas: list[Alocacao] = []
    for alocacao in solucao.alocacoes:
        equipe = equipes.get(alocacao.equipe_id)
        sala = salas.get(alocacao.sala_id)
        if equipe is None or sala is None:
            # Alocacao orfa: o validador ja a acusa como H0. Nao se inventa
            # explicacao para uma linha que nao deveria existir.
            explicadas.append(alocacao)
            continue

        termos = custo_marginal(problema, indice, equipe, sala, ctx)
        viaveis = salas_viaveis(problema, indice, equipe)
        alternativas = _alternativas(problema, indice, equipe, sala, ctx, viaveis, termos)

        explicadas.append(
            replace(
                alocacao,
                explicacao=_explicacao(
                    problema, indice, equipe, sala, termos, viaveis, alternativas
                ),
                alternativas=alternativas,
            )
        )
    return tuple(explicadas)


# --------------------------------------------------------------------------
# Alternativas
# --------------------------------------------------------------------------


def _bloqueio(
    indice: Indice, equipe: EquipeDTO, sala: SalaDTO, ctx: Contexto
) -> str | None:
    """O que impede esta equipe de se mudar para esta sala. `None` = nada impede.

    Complementa `salas_viaveis` com o que depende do *estado* da solucao e nao do
    par (equipe, sala): H2, H7 e a proximidade rigida. O motivo importa mais que
    o booleano -- "esta ocupada pela equipe 12" e uma resposta ao Coordenador
    Geral; "indisponivel" nao e.
    """
    for slot in equipe.turno.slots:  # H2
        ocupante = ctx.ocupacao.get((sala.id, slot))
        if ocupante is not None and ocupante != equipe.id:
            return f"ocupada pela equipe {ocupante} no turno da {slot}"

    # H7 -- o setor da equipe nao pode passar a dividir andar com um setor
    # separado por restricao rigida.
    no_andar = ctx.setores_no_andar.get(sala.andar)
    if no_andar:
        for setor_a, setor_b in indice.separacoes_rigidas:
            outro = (
                setor_b if equipe.setor_id == setor_a
                else setor_a if equipe.setor_id == setor_b
                else None
            )
            if outro is not None and no_andar.get(outro):
                return f"o setor {outro} ocupa o {sala.andar}o andar e nao divide andar com este"

    # Proximidade rigida: mover so uma das duas quebra o par, entao as unicas
    # salas alternativas sao as do andar onde a parceira ja esta.
    for equipe_a, equipe_b in indice.proximidades_rigidas:
        if equipe.id not in (equipe_a, equipe_b):
            continue
        parceira = equipe_b if equipe.id == equipe_a else equipe_a
        andar_parceira = ctx.andar_de.get(parceira)
        if andar_parceira is not None and sala.andar != andar_parceira:
            return f"a equipe {parceira} exige mesmo andar e esta no {andar_parceira}o"

    return None


def _por_que_nao(escolhida: tuple[Termo, ...], candidata: tuple[Termo, ...]) -> str:
    """O que esta alternativa piora em relacao a sala recomendada."""
    piores = [
        c.detalhe
        for c, e in zip(candidata, escolhida, strict=True)
        if c.valor > e.valor
    ]
    return "; ".join(piores) or "empata com a sala recomendada"


def _alternativas(
    problema: Problema,
    indice: Indice,
    equipe: EquipeDTO,
    escolhida: SalaDTO,
    ctx: Contexto,
    viaveis: tuple[SalaDTO, ...],
    termos: tuple[Termo, ...],
) -> list[dict]:
    """As TOP_N salas descartadas, da mais barata para a mais cara.

    Entram tambem as salas viaveis que estavam **ocupadas**, marcadas com o que
    as bloqueou. Num predio quase cheio elas sao a maior parte da resposta: dizer
    "a sala 812 seria melhor, mas esta com a equipe 12" explica a decisao muito
    melhor que uma lista vazia -- e e a verdade que o Coordenador Geral precisa
    para decidir se intervem.
    """
    custo_escolhida = sum(t.valor for t in termos)

    avaliadas = []
    for sala in viaveis:
        if sala.id == escolhida.id:
            continue
        candidata = custo_marginal(problema, indice, equipe, sala, ctx)
        bloqueio = _bloqueio(indice, equipe, sala, ctx)
        avaliadas.append((sum(t.valor for t in candidata), sala.id, sala, candidata, bloqueio))

    # Desempate por id: duas execucoes da mesma entrada tem que gravar a mesma
    # lista, byte a byte (AC-7).
    avaliadas.sort(key=lambda item: (item[0], item[1]))

    return [
        {
            "sala_id": sala.id,
            "codigo": sala.codigo,
            "andar": sala.andar,
            "capacidade": sala.capacidade,
            "custo": custo,
            "delta": custo - custo_escolhida,
            "disponivel": bloqueio is None,
            "por_que_nao": bloqueio or _por_que_nao(termos, candidata),
        }
        for custo, _, sala, candidata, bloqueio in avaliadas[:TOP_N_ALTERNATIVAS]
    ]


# --------------------------------------------------------------------------
# Montagem da explicacao
# --------------------------------------------------------------------------


def _comparacao(custo_escolhida: int, alternativas: list[dict]) -> dict:
    """Honestidade sobre o lugar da sala escolhida no ranking local.

    O CP-SAT otimiza o predio inteiro, nao esta equipe: as vezes ela paga mais
    caro para que outra caiba melhor. Quando isso acontece a explicacao **diz**,
    em vez de afirmar que a escolha foi a melhor -- afirmar seria mentir num
    campo que existe justamente para tornar a decisao auditavel.
    """
    livres = [a for a in alternativas if a["disponivel"]]
    if not livres:
        return {
            "tipo": "sem_alternativa",
            "detalhe": (
                "Nenhuma outra sala compativel estava livre nesta execucao: a escolha era "
                "esta sala ou deixar a equipe sem espaco."
            ),
        }

    melhor = livres[0]
    if melhor["custo"] >= custo_escolhida:
        return {
            "tipo": "melhor_local",
            "detalhe": (
                f"Nenhuma alternativa livre custa menos: a melhor descartada e a sala "
                f"{melhor['codigo']}, com custo {melhor['custo']} contra {custo_escolhida}."
            ),
        }
    return {
        "tipo": "trade_off_global",
        "detalhe": (
            f"Isoladamente a sala {melhor['codigo']} custaria "
            f"{custo_escolhida - melhor['custo']} a menos. O solver otimiza o predio "
            f"inteiro, e nesta solucao a troca sairia mais cara para o conjunto."
        ),
    }


def _resumo(
    equipe: EquipeDTO, sala: SalaDTO, custo: int, ocupacao_pct: float, avaliadas: int
) -> str:
    """O paragrafo da secao 9 do enunciado, com os numeros deste caso."""
    return (
        f"Sala {sala.codigo} recomendada para {equipe.nome}. "
        f"Capacidade {sala.capacidade}, equipe de {equipe.tamanho} pessoas, "
        f"ocupacao prevista {ocupacao_pct}%. "
        f"Entre as {avaliadas} salas avaliadas, esta e a que custa {custo} na funcao "
        f"objetivo -- o melhor equilibrio entre capacidade, localizacao e restricoes."
    )


def _explicacao(
    problema: Problema,
    indice: Indice,
    equipe: EquipeDTO,
    sala: SalaDTO,
    termos: tuple[Termo, ...],
    viaveis: tuple[SalaDTO, ...],
    alternativas: list[dict],
) -> dict:
    custo = sum(t.valor for t in termos)
    ocupacao_pct = round(equipe.tamanho / sala.capacidade * 100, 1)
    exigidos = sorted(
        equipe.recursos_requeridos | indice.recursos_extras.get(equipe.id, frozenset())
    )
    exige_acessibilidade = (
        equipe.exige_acessibilidade or equipe.id in indice.exige_acessibilidade
    )
    permitidos = indice.andares_permitidos.get(equipe.id)

    return {
        "equipe": {
            "id": equipe.id,
            "nome": equipe.nome,
            "tamanho": equipe.tamanho,
            "turno": str(equipe.turno),
            "prioridade": equipe.prioridade,
        },
        "sala": {
            "id": sala.id,
            "codigo": sala.codigo,
            "andar": sala.andar,
            "capacidade": sala.capacidade,
        },
        "ocupacao_pct": ocupacao_pct,
        "recursos_exigidos": exigidos,
        # Sempre verdadeiro numa solucao valida -- e o ponto: a secao 9 pede que
        # a tela mostre "recursos atendidos: sim", e o valor vem da verificacao,
        # nao de um literal.
        "recursos_atendidos": set(exigidos) <= set(sala.recursos),
        "acessibilidade_atendida": sala.acessivel if exige_acessibilidade else None,
        "andar_preferido": equipe.andar_preferido,
        "andar_preferido_atendido": (
            None if equipe.andar_preferido is None else sala.andar == equipe.andar_preferido
        ),
        "andares_permitidos": sorted(permitidos) if permitidos else [],
        "termos": [t.to_dict() for t in termos],
        "custo_total": custo,
        # Conta a escolhida: e o numero de opcoes que o motor pontuou, e por isso
        # nunca e zero. `alternativas` traz so as descartadas que estavam livres.
        "alternativas_avaliadas": len(viaveis),
        "comparacao": _comparacao(custo, alternativas),
        "resumo": _resumo(equipe, sala, custo, ocupacao_pct, len(viaveis)),
    }
