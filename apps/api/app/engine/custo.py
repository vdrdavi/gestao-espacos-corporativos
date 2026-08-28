"""A funcao de custo de docs/objetivo.md, aplicada a uma solucao pronta.

O solver constroi esta mesma expressao como objetivo do modelo CP-SAT; aqui ela
existe em Python puro porque quatro consumidores precisam dela fora do solver:

- o `baseline`, que tem que devolver um custo comparavel ao do CP-SAT para o
  teste diferencial MR-6 significar alguma coisa;
- o custo individual de cada `Alocacao` (a parte da conta que aquela equipe
  paga), gravado em `Assignment.custo`;
- o `explainer`, que compara salas pelo **custo marginal** (`custo_marginal`) --
  a mesma expressao, medida com as demais alocacoes fixas;
- o teste que trava o contrato: `avaliar(problema, solucao.alocacoes)` tem que
  bater com `solucao.custo` devolvido pelo solver. Sem ele, a expressao do
  modelo e a formula documentada podem divergir em silencio -- e a explicacao
  mostrada ao Coordenador Geral deixaria de ser a razao real da decisao.

Nao confundir com `validator.py`: aqui se mede *quanto custa*, la se verifica
*se e valida*. Sao perguntas diferentes e codigos deliberadamente separados.
"""

from dataclasses import dataclass

from app.engine.restricoes import Indice, indexar
from app.engine.types import Alocacao, EquipeDTO, Problema, SalaDTO

#: Distancia maxima entre andares no predio de 9 andares. So aparece como
#: constante de desativacao ("big M") do termo de proximidade.
DISTANCIA_MAXIMA = 8


def custo_local(problema: Problema, equipe_id: int, sala_id: int) -> int:
    """O que esta alocacao especifica custa: ociosidade + andar preferido.

    Os termos que dependem de *pares* de equipes (proximidade, separacao) nao
    cabem numa alocacao isolada e ficam de fora -- por isso a soma dos custos
    locais nao e o custo total, e `avaliar()` existe separado.
    """
    pesos = problema.pesos
    sala = next(s for s in problema.salas if s.id == sala_id)
    equipe = next(e for e in problema.equipes if e.id == equipe_id)

    custo = pesos.ociosidade * (sala.capacidade - equipe.tamanho)
    if equipe.andar_preferido is not None and sala.andar != equipe.andar_preferido:
        custo += pesos.andar_preferido
    return custo


def avaliar(
    problema: Problema, alocacoes: tuple[Alocacao, ...], indice: Indice | None = None
) -> int:
    """Custo total dos cinco termos de docs/objetivo.md."""
    pesos = problema.pesos
    indice = indice or indexar(problema)

    salas = {s.id: s for s in problema.salas}
    equipes = {e.id: e for e in problema.equipes}
    sala_da_equipe = {a.equipe_id: salas[a.sala_id] for a in alocacoes}

    # W_NA -- por pessoa-prioridade deixada sem sala. E o termo que domina:
    # sem ele, esconder equipes zeraria a ociosidade e "melhoraria" o custo.
    total = pesos.nao_alocada * sum(
        e.prioridade for e in problema.equipes if e.id not in sala_da_equipe
    )

    # W_OC -- assentos vazios numa sala ocupada.
    total += pesos.ociosidade * sum(
        sala_da_equipe[e_id].capacidade - equipes[e_id].tamanho for e_id in sala_da_equipe
    )

    # W_AP -- preferencia de andar nao atendida.
    total += pesos.andar_preferido * sum(
        1
        for e_id, sala in sala_da_equipe.items()
        if equipes[e_id].andar_preferido is not None
        and sala.andar != equipes[e_id].andar_preferido
    )

    # W_PR -- distancia entre equipes relacionadas. So conta quando as duas
    # foram alocadas: cobrar distancia de uma equipe que nem sala tem seria
    # cobrar duas vezes pelo mesmo problema (ela ja paga W_NA).
    for equipe_a, equipe_b, peso in indice.proximidades_flexiveis:
        if equipe_a in sala_da_equipe and equipe_b in sala_da_equipe:
            total += peso * abs(sala_da_equipe[equipe_a].andar - sala_da_equipe[equipe_b].andar)

    # W_RS -- restricoes flexiveis violadas.
    for setor_a, setor_b, peso in indice.separacoes_flexiveis:
        andares_a = {sala.andar for e_id, sala in sala_da_equipe.items()
                     if equipes[e_id].setor_id == setor_a}
        andares_b = {sala.andar for e_id, sala in sala_da_equipe.items()
                     if equipes[e_id].setor_id == setor_b}
        total += peso * len(andares_a & andares_b)

    return total


# --------------------------------------------------------------------------
# Custo marginal -- a conta por tras de uma recomendacao (AC-3)
# --------------------------------------------------------------------------
#
# `avaliar` mede a solucao inteira; `custo_local` mede o que cabe numa alocacao
# isolada. Nenhum dos dois responde a pergunta da secao 9 do enunciado -- *por
# que esta sala e nao aquela?* -- porque a resposta depende de onde as outras
# equipes ficaram: a mesma sala custa mais ou menos conforme a equipe parceira
# esteja perto ou longe.
#
# O custo marginal e a diferenca que esta equipe nesta sala faz no custo total,
# com as demais alocacoes fixas. E o unico numero que torna duas salas
# comparaveis entre si; uma reparticao do custo total nao seria, porque os
# termos de par (proximidade, separacao) nao pertencem a uma equipe so.


@dataclass(frozen=True, slots=True)
class Termo:
    """Uma parcela do custo com o numero e a frase que o explica.

    `detalhe` e escrito para ser lido de dois jeitos: sozinho, na decomposicao
    termo a termo da sala recomendada, e em lista, quando o explainer diz o que
    uma alternativa piora ("14 assentos ociosos; andar preferido nao atendido").
    """

    nome: str
    valor: int
    detalhe: str

    def to_dict(self) -> dict:
        return {"nome": self.nome, "valor": self.valor, "detalhe": self.detalhe}


@dataclass(frozen=True, slots=True)
class Contexto:
    """A solucao vista como "o que ja esta ocupado", que e o que o custo marginal
    precisa saber sobre as outras equipes.

    Montado uma vez por execucao e reusado para todas as equipes e todas as
    alternativas: sem isso, explicar 84 recomendacoes com ~100 salas viaveis cada
    seria varrer a solucao inteira milhares de vezes.
    """

    #: (sala_id, slot) -> equipe que o ocupa. Base de H2 e do "esta ocupada por".
    ocupacao: dict[tuple[int, str], int]
    #: equipe_id -> andar onde ela ficou. Ausente = equipe sem sala.
    andar_de: dict[int, int]
    #: andar -> {setor_id: quantas equipes daquele setor estao nele}. A contagem
    #: (e nao um booleano) e o que permite perguntar "e se esta equipe sair?".
    setores_no_andar: dict[int, dict[int, int]]


def contexto(problema: Problema, alocacoes: tuple[Alocacao, ...]) -> Contexto:
    salas = {s.id: s for s in problema.salas}
    equipes = {e.id: e for e in problema.equipes}

    ocupacao: dict[tuple[int, str], int] = {}
    andar_de: dict[int, int] = {}
    setores_no_andar: dict[int, dict[int, int]] = {}

    for alocacao in alocacoes:
        equipe = equipes.get(alocacao.equipe_id)
        sala = salas.get(alocacao.sala_id)
        if equipe is None or sala is None:
            continue  # alocacao orfa: o validador ja a acusa como H0
        for slot in equipe.turno.slots:
            ocupacao[sala.id, slot] = equipe.id
        andar_de[equipe.id] = sala.andar
        no_andar = setores_no_andar.setdefault(sala.andar, {})
        no_andar[equipe.setor_id] = no_andar.get(equipe.setor_id, 0) + 1

    return Contexto(ocupacao=ocupacao, andar_de=andar_de, setores_no_andar=setores_no_andar)


def _plural(quantidade: int, singular: str, plural: str) -> str:
    """A explicacao vai para a tela do Coordenador Geral, nao para um log."""
    return f"{quantidade} {singular if quantidade == 1 else plural}"


def _termo_ociosidade(problema: Problema, equipe: EquipeDTO, sala: SalaDTO) -> Termo:
    ociosos = sala.capacidade - equipe.tamanho
    return Termo(
        nome="ociosidade",
        valor=problema.pesos.ociosidade * ociosos,
        detalhe=(
            f"{_plural(ociosos, 'assento ocioso', 'assentos ociosos')} "
            f"({sala.capacidade} lugares para {equipe.tamanho} pessoas)"
            if ociosos
            else f"nenhum assento ocioso ({sala.capacidade} lugares ocupados)"
        ),
    )


def _termo_andar_preferido(problema: Problema, equipe: EquipeDTO, sala: SalaDTO) -> Termo:
    if equipe.andar_preferido is None:
        return Termo("andar_preferido", 0, "a equipe nao declarou andar preferido")
    if sala.andar == equipe.andar_preferido:
        return Termo("andar_preferido", 0, f"andar preferido ({sala.andar}o) atendido")
    return Termo(
        nome="andar_preferido",
        valor=problema.pesos.andar_preferido,
        detalhe=(
            f"andar preferido nao atendido (prefere o {equipe.andar_preferido}o, "
            f"sala no {sala.andar}o)"
        ),
    )


def _termo_proximidade(
    indice: Indice, equipe: EquipeDTO, sala: SalaDTO, ctx: Contexto
) -> Termo:
    """W_PR contra as parceiras *ja alocadas*.

    Uma parceira sem sala nao entra: ela ja paga W_NA, e cobrar tambem a
    distancia seria cobrar duas vezes pelo mesmo problema (docs/objetivo.md).
    """
    total = 0
    frases: list[str] = []
    pendentes: list[int] = []

    for equipe_a, equipe_b, peso in indice.proximidades_flexiveis:
        if equipe.id not in (equipe_a, equipe_b):
            continue
        parceira = equipe_b if equipe.id == equipe_a else equipe_a
        andar_parceira = ctx.andar_de.get(parceira)
        if andar_parceira is None:
            pendentes.append(parceira)
            continue
        distancia = abs(sala.andar - andar_parceira)
        total += peso * distancia
        frases.append(
            f"equipe {parceira} no mesmo andar"
            if distancia == 0
            else (
                f"equipe {parceira} a {_plural(distancia, 'andar', 'andares')} de "
                f"distancia (no {andar_parceira}o)"
            )
        )

    if not frases and not pendentes:
        return Termo("proximidade", 0, "a equipe nao tem par de proximidade")
    if not frases:
        parceiras = ", ".join(str(p) for p in sorted(set(pendentes)))
        return Termo(
            "proximidade", 0, f"a(s) equipe(s) parceira(s) {parceiras} nao foram alocadas"
        )
    return Termo("proximidade", total, "; ".join(frases))


def _termo_flexiveis(
    indice: Indice, equipe: EquipeDTO, sala: SalaDTO, ctx: Contexto
) -> Termo:
    """W_RS -- separacoes de setor flexiveis que *esta* colocacao passaria a violar.

    Marginal de verdade: se outra equipe do mesmo setor ja esta no andar, a
    violacao ja existe e nao e cobrada de novo. `avaliar` conta andares
    compartilhados, nao equipes -- e a explicacao tem que somar a mesma coisa.
    """
    ocupantes = ctx.setores_no_andar.get(sala.andar, {})
    # Quantas equipes do setor desta equipe ficariam no andar se ela saisse dele.
    ja_no_andar = ocupantes.get(equipe.setor_id, 0) - (
        1 if ctx.andar_de.get(equipe.id) == sala.andar else 0
    )

    total = 0
    frases: list[str] = []
    for setor_a, setor_b, peso in indice.separacoes_flexiveis:
        if setor_a == setor_b or equipe.setor_id not in (setor_a, setor_b):
            continue
        outro = setor_b if equipe.setor_id == setor_a else setor_a
        if ja_no_andar > 0 or not ocupantes.get(outro):
            continue
        total += peso
        frases.append(
            f"passa a dividir o {sala.andar}o andar com o setor {outro}, que a "
            f"execucao pediu para separar"
        )

    return Termo(
        nome="restricao_flexivel",
        valor=total,
        detalhe="; ".join(frases) or "nenhuma restricao flexivel violada",
    )


def custo_marginal(
    problema: Problema,
    indice: Indice,
    equipe: EquipeDTO,
    sala: SalaDTO,
    ctx: Contexto,
) -> tuple[Termo, ...]:
    """Quanto esta equipe nesta sala acrescenta ao custo, com o resto fixo.

    Sempre os mesmos quatro termos, na mesma ordem, mesmo quando valem zero: e o
    que permite comparar duas salas termo a termo (`explainer._por_que_nao` faz
    exatamente isso) e o que faz um zero explicito -- "andar preferido atendido"
    -- valer tanto quanto um custo. W_NA nao aparece porque ele e o custo de
    *nao* alocar: quem esta sendo explicado aqui e uma equipe que tem sala.
    """
    return (
        _termo_ociosidade(problema, equipe, sala),
        _termo_andar_preferido(problema, equipe, sala),
        _termo_proximidade(indice, equipe, sala, ctx),
        _termo_flexiveis(indice, equipe, sala, ctx),
    )
