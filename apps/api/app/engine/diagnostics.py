"""Tratamento de excecoes (secao 11 do enunciado).

Para cada equipe nao alocada, relaxa uma restricao por vez e reexecuta um
subproblema pequeno. A primeira restricao cuja remocao torna a equipe alocavel
**sem desalojar ninguem** e a *causa*; o encaminhamento sai de
ENCAMINHAMENTO_PADRAO refinado com os numeros do caso concreto.

O enunciado e explicito: o sistema nao deve esconder o problema nem produzir
uma alocacao invalida para inflar o indicador de sucesso.

**Por que relaxar e reexecutar, e nao so classificar.** A classificacao estatica
de `restricoes.rejeicoes()` responde *qual filtro esvaziou o conjunto de salas*.
E factual, mas nao responde a pergunta que o Coordenador Geral faz: *o que eu
mudo para resolver?* Reexecutar responde -- "sem a exigencia de bancada tecnica
esta equipe caberia na sala 803" e uma frase acionavel; "recurso indisponivel"
nao e.

**Cada relaxamento e uma transformacao da entrada**, nunca uma segunda
modelagem: monta-se um `Problema` menor com a equipe alterada e as restricoes
filtradas, e chama-se o `solver.alocar` de sempre. Se o diagnostico tivesse
modelo proprio, ele poderia discordar do solver por bug de traducao e apontar a
restricao errada com toda a confianca.

**Degradacao honesta.** Sub-solve que nao prova otimalidade, orcamento estourado
ou equipes demais na fila => o resultado e *inconclusivo* e a rejeicao mantem a
classificacao base. Nunca uma causa que muda conforme a carga da maquina: o
registro e append-only e AC-7 cobra reprodutibilidade.
"""

import time
from dataclasses import dataclass, replace

from app.engine import solver
from app.engine.restricoes import Indice, indexar, salas_viaveis
from app.engine.types import (
    Alocacao,
    EquipeDTO,
    Problema,
    Rejeicao,
    RestricaoDTO,
    SalaDTO,
    Solucao,
)
from app.engine.version import ENGINE_VERSION
from app.enums import ENCAMINHAMENTO_PADRAO, CodigoMotivo, StatusRun, TipoRestricao

#: Orcamento do diagnostico inteiro. O AC-6 da 10s para a execucao completa e o
#: solver ja consome ~0,6s no cenario de referencia; o pos-processamento nao pode
#: comer o resto.
ORCAMENTO_SEGUNDOS = 2.0

#: Limite de cada sub-solve. Os subproblemas tem poucas dezenas de variaveis e
#: provam otimalidade em milissegundos -- se um estourar isto, algo esta errado
#: com o recorte, e o resultado e descartado em vez de usado.
LIMITE_POR_RESOLVE = 0.5

#: Acima disto o diagnostico nao roda: um cenario com dezenas de equipes de fora
#: e um problema de dimensionamento, e a classificacao base ja o descreve.
MAX_EQUIPES_DIAGNOSTICADAS = 12

#: Tamanho maximo do recorte. Mantem cada sub-solve trivial para o CP-SAT.
MAX_EQUIPES_SUBPROBLEMA = 20


@dataclass(frozen=True, slots=True)
class Relaxamento:
    """Uma pergunta do tipo "e se esta regra nao valesse para esta equipe?"."""

    nome: str
    motivo: CodigoMotivo
    equipe: EquipeDTO
    salas: tuple[SalaDTO, ...]
    restricoes: tuple[RestricaoDTO, ...]


# --------------------------------------------------------------------------
# A escada de relaxamentos
# --------------------------------------------------------------------------


def _alcanca(restricao: RestricaoDTO, equipe: EquipeDTO) -> bool:
    """A restricao atinge esta equipe? Mesma convencao de `restricoes.indexar`."""
    return restricao.alvo_id in (None, equipe.id, equipe.setor_id)


def _sem_a_equipe(
    problema: Problema, restricoes: tuple[RestricaoDTO, ...], equipe: EquipeDTO, tipo
) -> tuple[RestricaoDTO, ...]:
    """Tira `equipe` do alcance das restricoes de `tipo`, preservando as demais.

    Uma restricao de setor vira copias por equipe, menos a que se quer isentar.
    Relaxar a regra para o predio inteiro responderia a pergunta errada: o
    diagnostico e sobre *esta* equipe, nao sobre afrouxar a politica.
    """
    resultado: list[RestricaoDTO] = []
    for restricao in restricoes:
        if restricao.tipo is not tipo or not restricao.rigida or not _alcanca(restricao, equipe):
            resultado.append(restricao)
            continue
        if restricao.alvo_id == equipe.id:
            continue  # era so dela: some
        # Global ou de setor: reexpande para as outras equipes atingidas.
        resultado += [
            replace(restricao, alvo_id=outra.id)
            for outra in problema.equipes
            if outra.id != equipe.id and _alcanca(restricao, outra)
        ]
    return tuple(resultado)


def _sem_as_de_par(
    restricoes: tuple[RestricaoDTO, ...], equipe: EquipeDTO, tipo, chaves: tuple[str, str]
) -> tuple[RestricaoDTO, ...]:
    """Remove as restricoes de par (setor a x setor b, equipe a x equipe b) que
    envolvem esta equipe. Par nao se reexpande: a regra e sobre a relacao."""
    proprios = {equipe.id} if tipo is TipoRestricao.PROXIMIDADE else {equipe.setor_id}

    def envolve(restricao: RestricaoDTO) -> bool:
        parametros = restricao.parametros or {}
        lados = {parametros.get(chaves[0]), parametros.get(chaves[1])}
        return restricao.tipo is tipo and restricao.rigida and bool(lados & proprios)

    return tuple(r for r in restricoes if not envolve(r))


def escada(problema: Problema, indice: Indice, equipe: EquipeDTO) -> list[Relaxamento]:
    """Os relaxamentos a testar, em ordem, para esta equipe.

    **A ordem nao e arbitraria** -- e a mesma de `restricoes._filtro_que_esvaziou`,
    pela mesma razao: recurso antes de capacidade e o que faz o cenario
    `estresse-recurso-escasso` responder a verdade. La sobram salas grandes e a
    causa real e a bancada tecnica que elas nao tem.

    Relaxamento que nao muda nada para esta equipe nao entra: gastaria um
    sub-solve para provar o obvio.
    """
    salas, restricoes = problema.salas, problema.restricoes
    passos: list[Relaxamento] = []

    def passo(nome, motivo, *, equipe_r=equipe, salas_r=salas, restricoes_r=restricoes):
        passos.append(Relaxamento(nome, motivo, equipe_r, salas_r, restricoes_r))

    if equipe.recursos_requeridos or indice.recursos_extras.get(equipe.id):
        passo(
            "a exigencia de recursos",
            CodigoMotivo.RECURSO_INDISPONIVEL,
            equipe_r=replace(equipe, recursos_requeridos=frozenset()),
            restricoes_r=_sem_a_equipe(
                problema, restricoes, equipe, TipoRestricao.RECURSO_OBRIGATORIO
            ),
        )

    if equipe.exige_acessibilidade or equipe.id in indice.exige_acessibilidade:
        passo(
            "a exigencia de acessibilidade",
            CodigoMotivo.ACESSIBILIDADE_INDISPONIVEL,
            equipe_r=replace(equipe, exige_acessibilidade=False),
            restricoes_r=_sem_a_equipe(
                problema, restricoes, equipe, TipoRestricao.ACESSIBILIDADE_OBRIGATORIA
            ),
        )

    if indice.andares_permitidos.get(equipe.id):
        passo(
            "a restricao de andar permitido",
            CodigoMotivo.ANDAR_SEM_VAGA,
            restricoes_r=_sem_a_equipe(
                problema, restricoes, equipe, TipoRestricao.ANDAR_PERMITIDO
            ),
        )

    if indice.capacidade_minima.get(equipe.id):
        passo(
            "a capacidade minima exigida",
            CodigoMotivo.SEM_SALA_COMPATIVEL,
            restricoes_r=_sem_a_equipe(
                problema, restricoes, equipe, TipoRestricao.CAPACIDADE_MINIMA
            ),
        )

    # H6 mora em dois lugares: no campo da sala e na restricao SALA_RESERVADA.
    # Relaxar so um dos dois deixaria a resposta pela metade.
    reservadas_a_terceiros = any(
        setor != equipe.setor_id for setor in indice.sala_reservada.values()
    )
    if reservadas_a_terceiros:
        passo(
            "a reserva de salas a outros setores",
            CodigoMotivo.SEM_SALA_COMPATIVEL,
            salas_r=tuple(replace(s, reservada_para_setor_id=None) for s in salas),
            restricoes_r=tuple(
                r for r in restricoes if r.tipo is not TipoRestricao.SALA_RESERVADA
            ),
        )

    if any(equipe.setor_id in par for par in indice.separacoes_rigidas):
        passo(
            "a separacao entre setores",
            CodigoMotivo.CONFLITO_RESTRICOES,
            restricoes_r=_sem_as_de_par(
                restricoes, equipe, TipoRestricao.SEPARACAO_SETORES, ("setor_a", "setor_b")
            ),
        )

    if any(equipe.id in par for par in indice.proximidades_rigidas):
        passo(
            "a proximidade rigida com a equipe parceira",
            CodigoMotivo.CONFLITO_RESTRICOES,
            restricoes_r=_sem_as_de_par(
                restricoes, equipe, TipoRestricao.PROXIMIDADE, ("equipe_a", "equipe_b")
            ),
        )

    return passos


# --------------------------------------------------------------------------
# O subproblema
# --------------------------------------------------------------------------


def _recorte(
    problema: Problema, relaxamento: Relaxamento, sala_de: dict[int, int]
) -> tuple[Problema, tuple[SalaDTO, ...]]:
    """O menor problema capaz de responder "esta equipe caberia?".

    So a equipe diagnosticada, as salas que o relaxamento abriria para ela e as
    equipes que hoje ocupam essas salas -- as unicas que teriam de sair do lugar.
    Devolve tambem as salas-alvo, que a causa cita pelo codigo.
    """
    equipe = relaxamento.equipe
    equipes_por_id = {e.id: e for e in problema.equipes}

    relaxado = Problema(
        salas=relaxamento.salas,
        equipes=tuple(
            relaxamento.equipe if e.id == equipe.id else e for e in problema.equipes
        ),
        restricoes=relaxamento.restricoes,
        pesos=problema.pesos,
        seed=problema.seed,
    )
    alvos = salas_viaveis(relaxado, indexar(relaxado), equipe)
    ids_alvo = {s.id for s in alvos}

    concorrentes = sorted(
        {
            outra_id
            for outra_id, sala_id in sala_de.items()
            if sala_id in ids_alvo
            and outra_id != equipe.id
            and equipes_por_id[outra_id].turno.conflita_com(equipe.turno)
        }
    )[: MAX_EQUIPES_SUBPROBLEMA - 1]

    salas_dos_concorrentes = {sala_de[o] for o in concorrentes}
    salas_sub = tuple(
        s for s in relaxamento.salas if s.id in ids_alvo | salas_dos_concorrentes
    )
    equipes_sub = (equipe,) + tuple(equipes_por_id[o] for o in concorrentes)

    return (
        Problema(
            salas=salas_sub,
            equipes=equipes_sub,
            restricoes=relaxamento.restricoes,
            pesos=problema.pesos,
            limite_segundos=LIMITE_POR_RESOLVE,
            seed=problema.seed,
        ),
        alvos,
    )


def _resolve(sub: Problema, sala_de: dict[int, int]) -> Solucao | None:
    """Roda o subproblema partindo da colocacao atual. `None` = inconclusivo."""
    hint = Solucao(
        alocacoes=tuple(
            Alocacao(equipe_id=e.id, sala_id=sala_de[e.id], turno=e.turno)
            for e in sub.equipes
            if e.id in sala_de and any(s.id == sala_de[e.id] for s in sub.salas)
        ),
        nao_alocadas=(),
        custo=0,
        status=StatusRun.FEASIBLE,
        duracao_ms=0,
        engine_version=ENGINE_VERSION,
    )
    resultado = solver.alocar(sub, hint=hint)
    # Sub-solve truncado nao vira resposta: preferimos a classificacao base a uma
    # causa que depende de quanto a maquina estava ocupada.
    return resultado if resultado.status is StatusRun.OPTIMAL else None


def _resolveria(
    problema: Problema, relaxamento: Relaxamento, sala_de: dict[int, int]
) -> SalaDTO | None:
    """A sala que este relaxamento abriria, ou `None` se ele nao resolve.

    Exige que **ninguem seja desalojado**: uma "solucao" que aloca esta equipe
    tirando outra do lugar nao resolveu nada, so mudou quem fica de fora -- e
    apresenta-la como encaminhamento seria enganar quem le.
    """
    sub, alvos = _recorte(problema, relaxamento, sala_de)
    if not alvos:
        return None

    resultado = _resolve(sub, sala_de)
    if resultado is None:
        return None

    novo_sala_de = {a.equipe_id: a.sala_id for a in resultado.alocacoes}
    if relaxamento.equipe.id not in novo_sala_de:
        return None
    if any(
        outra.id not in novo_sala_de
        for outra in sub.equipes
        if outra.id != relaxamento.equipe.id and outra.id in sala_de
    ):
        return None

    escolhida = novo_sala_de[relaxamento.equipe.id]
    return next(s for s in sub.salas if s.id == escolhida)


# --------------------------------------------------------------------------
# Diagnostico
# --------------------------------------------------------------------------


def _refinar(equipe: EquipeDTO, relaxamento: Relaxamento, sala: SalaDTO) -> Rejeicao:
    return Rejeicao(
        equipe_id=equipe.id,
        codigo_motivo=relaxamento.motivo,
        causa=(
            f"Sem {relaxamento.nome}, a equipe ({equipe.tamanho} pessoas) caberia na sala "
            f"{sala.codigo} do {sala.andar}o andar, que comporta {sala.capacidade} -- e sem "
            f"tirar nenhuma outra equipe do lugar. E a unica regra que, sozinha, resolve "
            f"este caso."
        ),
        encaminhamento=(
            f"{ENCAMINHAMENTO_PADRAO[relaxamento.motivo]} "
            f"Concretamente: rever {relaxamento.nome} desta equipe libera a sala "
            f"{sala.codigo}."
        ),
    )


def _sem_saida(base: Rejeicao, testados: int) -> Rejeicao:
    """Nenhum relaxamento isolado resolve: a causa e a disputa, nao uma regra."""
    if not testados:
        return base
    return replace(
        base,
        causa=(
            f"{base.causa} Nenhum dos {testados} relaxamentos testados resolveria "
            f"sozinho: as salas compativeis seguem ocupadas por equipes que tambem "
            f"precisam delas."
        ),
    )


def diagnosticar(problema: Problema, solucao: Solucao) -> tuple[Rejeicao, ...]:
    """Refina o motivo de cada equipe sem sala relaxando uma regra por vez.

    Parte de `solucao.nao_alocadas` -- a classificacao estatica ja produzida pelo
    solver -- e so a substitui quando tem algo melhor a dizer. `NaoAlocada` e
    append-only: linha gravada incompleta nunca mais e corrigida, entao o piso do
    diagnostico e o resultado do D2, nunca um campo vazio.
    """
    if not solucao.nao_alocadas:
        return ()

    indice = indexar(problema)
    equipes = {e.id: e for e in problema.equipes}
    sala_de = {a.equipe_id: a.sala_id for a in solucao.alocacoes}
    inicio = time.perf_counter()

    refinadas: list[Rejeicao] = []
    for posicao, base in enumerate(solucao.nao_alocadas):
        equipe = equipes.get(base.equipe_id)
        estourou = (
            posicao >= MAX_EQUIPES_DIAGNOSTICADAS
            or time.perf_counter() - inicio > ORCAMENTO_SEGUNDOS
        )
        if equipe is None or estourou:
            refinadas.append(base)
            continue

        passos = escada(problema, indice, equipe)
        refinada = None
        for relaxamento in passos:
            sala = _resolveria(problema, relaxamento, sala_de)
            if sala is not None:
                refinada = _refinar(equipe, relaxamento, sala)
                break
        refinadas.append(refinada or _sem_saida(base, len(passos)))

    return tuple(refinadas)
