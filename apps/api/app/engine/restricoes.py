"""Interpretacao das restricoes e viabilidade estatica.

`RestricaoDTO` chega do banco como um `dict` de parametros solto. Este modulo e
quem le esse dict uma unica vez e devolve estruturas indexadas -- andares
permitidos por equipe, salas reservadas, pares de proximidade, pares de setores
que nao dividem andar.

Compartilhado por `baseline`, `solver`, `explainer` e `diagnostics`: os quatro
precisam concordar sobre *quais salas uma equipe pode ocupar*, senao o teste
diferencial MR-6 compara duas leituras diferentes do mesmo enunciado.

**Nunca importado por `validator.py`** -- ver regra 3 do CLAUDE.md. O validador
reavalia H1-H8 do zero justamente para nao herdar um erro daqui.

Divisao de trabalho:

- os filtros que dependem so do par (equipe, sala) ficam aqui, em
  `salas_viaveis()`: H1, H3, H4, H5, H6 e capacidade minima;
- H2 (turno), H7 (separacao de setores) e proximidade dependem de estado global
  -- de quem mais esta na sala, no andar -- e ficam no solver e no baseline.
"""

from dataclasses import dataclass, field

from app.engine.types import Alocacao, EquipeDTO, Problema, Rejeicao, SalaDTO
from app.enums import ENCAMINHAMENTO_PADRAO, CodigoMotivo, TipoRestricao


@dataclass(frozen=True, slots=True)
class Indice:
    """Restricoes lidas uma vez e indexadas pelo que o motor consulta.

    Todos os campos sao indexados por id de equipe ou de sala, nunca por nome:
    o MR-4 renomeia a entrada inteira e as metricas tem que ficar identicas.
    """

    #: equipe_id -> andares que ela pode ocupar (H5). Ausente = qualquer andar.
    andares_permitidos: dict[int, frozenset[int]] = field(default_factory=dict)
    #: sala_id -> setor_id que a reservou (H6).
    sala_reservada: dict[int, int] = field(default_factory=dict)
    #: equipe_id -> capacidade minima exigida.
    capacidade_minima: dict[int, int] = field(default_factory=dict)
    #: equipe_id -> recursos exigidos por restricao (somados aos da propria equipe).
    recursos_extras: dict[int, frozenset[str]] = field(default_factory=dict)
    #: equipes que exigem acessibilidade por restricao (alem do campo da equipe).
    exige_acessibilidade: frozenset[int] = frozenset()
    #: pares (setor_a, setor_b) que nao podem dividir andar (H7), rigidos.
    separacoes_rigidas: tuple[tuple[int, int], ...] = ()
    #: idem, flexiveis: viram termo de custo.
    separacoes_flexiveis: tuple[tuple[int, int, int], ...] = ()
    #: pares (equipe_a, equipe_b) que devem ficar no mesmo andar (proximidade rigida).
    proximidades_rigidas: tuple[tuple[int, int], ...] = ()
    #: (equipe_a, equipe_b, peso) -- distancia entre andares entra no custo.
    proximidades_flexiveis: tuple[tuple[int, int, int], ...] = ()

    def acoplada(self, equipe_id: int, setor_id: int) -> bool:
        """A equipe participa de alguma restricao rigida que envolve terceiros?

        E o que distingue "nao coube" de "nao fechou com as outras": uma equipe
        com salas viaveis que mesmo assim ficou de fora ou esbarrou em
        acoplamento (CONFLITO_RESTRICOES) ou o predio lotou (CAPACIDADE_ESGOTADA).
        """
        if any(equipe_id in par for par in self.proximidades_rigidas):
            return True
        return any(setor_id in par for par in self.separacoes_rigidas)


def _peso_da(restricao, padrao: int) -> int:
    """Peso efetivo de uma restricao flexivel.

    `Restricao.peso` sobrepoe o peso global quando preenchido -- e o que permite
    dizer "esta proximidade especifica vale mais que as outras" sem mexer nos
    pesos da execucao inteira. Ver docs/objetivo.md.
    """
    return restricao.peso if restricao.peso > 0 else padrao


def indexar(problema: Problema) -> Indice:
    setor_por_equipe = {e.id: e.setor_id for e in problema.equipes}
    equipes_do_setor: dict[int, list[int]] = {}
    for equipe in problema.equipes:
        equipes_do_setor.setdefault(equipe.setor_id, []).append(equipe.id)

    sala_por_codigo = {s.codigo: s.id for s in problema.salas}

    andares: dict[int, set[int]] = {}
    reservadas: dict[int, int] = {s.id: s.reservada_para_setor_id for s in problema.salas
                                 if s.reservada_para_setor_id is not None}
    capacidade_minima: dict[int, int] = {}
    recursos_extras: dict[int, set[str]] = {}
    acessibilidade: set[int] = set()
    separacoes_rigidas: list[tuple[int, int]] = []
    separacoes_flexiveis: list[tuple[int, int, int]] = []
    proximidades_rigidas: list[tuple[int, int]] = []
    proximidades_flexiveis: list[tuple[int, int, int]] = []

    def alvos(restricao) -> list[int]:
        """Equipes atingidas: a propria, todas do setor, ou todas do problema."""
        if restricao.alvo_id is None:
            return [e.id for e in problema.equipes]
        if restricao.alvo_id in setor_por_equipe:
            # Ambiguidade real: o mesmo id pode ser de equipe e de setor. O
            # alvo_tipo do banco resolve, mas o DTO nao o carrega -- entao a
            # convencao e: se existe equipe com esse id, o alvo e a equipe.
            return [restricao.alvo_id]
        return equipes_do_setor.get(restricao.alvo_id, [])

    for restricao in problema.restricoes:
        parametros = restricao.parametros or {}

        match restricao.tipo:
            case TipoRestricao.ANDAR_PERMITIDO if restricao.rigida:
                permitidos = frozenset(parametros.get("andares", []))
                if permitidos:
                    for equipe_id in alvos(restricao):
                        # Duas restricoes de andar sobre a mesma equipe se
                        # intersectam: ambas continuam valendo.
                        anterior = andares.get(equipe_id)
                        andares[equipe_id] = (
                            set(permitidos) if anterior is None else anterior & permitidos
                        )

            case TipoRestricao.SALA_RESERVADA if restricao.rigida:
                setor_id = parametros.get("setor_id")
                sala_id = parametros.get("sala_id") or sala_por_codigo.get(
                    parametros.get("codigo_sala", "")
                )
                if sala_id is not None and setor_id is not None:
                    reservadas[sala_id] = setor_id

            case TipoRestricao.CAPACIDADE_MINIMA if restricao.rigida:
                minima = parametros.get("minima") or parametros.get("capacidade_minima")
                if minima:
                    for equipe_id in alvos(restricao):
                        capacidade_minima[equipe_id] = max(
                            capacidade_minima.get(equipe_id, 0), int(minima)
                        )

            case TipoRestricao.RECURSO_OBRIGATORIO if restricao.rigida:
                exigidos = parametros.get("recursos") or [parametros.get("recurso")]
                exigidos = {str(r) for r in exigidos if r}
                if exigidos:
                    for equipe_id in alvos(restricao):
                        recursos_extras.setdefault(equipe_id, set()).update(exigidos)

            case TipoRestricao.ACESSIBILIDADE_OBRIGATORIA if restricao.rigida:
                acessibilidade.update(alvos(restricao))

            case TipoRestricao.SEPARACAO_SETORES:
                par = (parametros.get("setor_a"), parametros.get("setor_b"))
                if None not in par:
                    if restricao.rigida:
                        separacoes_rigidas.append((par[0], par[1]))
                    else:
                        separacoes_flexiveis.append(
                            (par[0], par[1], _peso_da(restricao, problema.pesos.restricao_flexivel))
                        )

            case TipoRestricao.PROXIMIDADE:
                par = (parametros.get("equipe_a"), parametros.get("equipe_b"))
                if None not in par:
                    if restricao.rigida:
                        proximidades_rigidas.append((par[0], par[1]))
                    else:
                        proximidades_flexiveis.append(
                            (par[0], par[1], _peso_da(restricao, problema.pesos.proximidade))
                        )

            case _:
                # ANDAR_PREFERIDO e PRIORIDADE_EQUIPE ja sao campos da propria
                # equipe (andar_preferido, prioridade) e entram no custo por la.
                # Restricoes rigidas por natureza marcadas como flexiveis viram
                # termo de custo no solver, nao filtro de viabilidade.
                pass

    return Indice(
        andares_permitidos={e: frozenset(a) for e, a in andares.items()},
        sala_reservada=reservadas,
        capacidade_minima=capacidade_minima,
        recursos_extras={e: frozenset(r) for e, r in recursos_extras.items()},
        exige_acessibilidade=frozenset(acessibilidade),
        separacoes_rigidas=tuple(separacoes_rigidas),
        separacoes_flexiveis=tuple(separacoes_flexiveis),
        proximidades_rigidas=tuple(proximidades_rigidas),
        proximidades_flexiveis=tuple(proximidades_flexiveis),
    )


# --------------------------------------------------------------------------
# Viabilidade estatica -- os filtros do par (equipe, sala)
# --------------------------------------------------------------------------


def _recursos_de(indice: Indice, equipe: EquipeDTO) -> frozenset[str]:
    return equipe.recursos_requeridos | indice.recursos_extras.get(equipe.id, frozenset())


def _exige_acessibilidade(indice: Indice, equipe: EquipeDTO) -> bool:
    return equipe.exige_acessibilidade or equipe.id in indice.exige_acessibilidade


def cabe(indice: Indice, equipe: EquipeDTO, sala: SalaDTO) -> bool:
    """H1 -- capacidade, incluindo a capacidade minima exigida pela equipe."""
    if equipe.tamanho > sala.capacidade:
        return False
    return sala.capacidade >= indice.capacidade_minima.get(equipe.id, 0)


def viavel(indice: Indice, equipe: EquipeDTO, sala: SalaDTO) -> bool:
    """A sala pode receber a equipe olhando so para o par (H1, H3, H4, H5, H6)."""
    if not sala.disponivel:
        return False
    if not cabe(indice, equipe, sala):
        return False
    if not _recursos_de(indice, equipe) <= sala.recursos:  # H3
        return False
    if _exige_acessibilidade(indice, equipe) and not sala.acessivel:  # H4
        return False
    permitidos = indice.andares_permitidos.get(equipe.id)  # H5
    if permitidos is not None and sala.andar not in permitidos:
        return False
    reservada_para = indice.sala_reservada.get(sala.id)  # H6
    return not (reservada_para is not None and reservada_para != equipe.setor_id)


def salas_viaveis(
    problema: Problema, indice: Indice, equipe: EquipeDTO
) -> tuple[SalaDTO, ...]:
    return tuple(s for s in problema.salas if viavel(indice, equipe, s))


def _filtro_que_esvaziou(
    indice: Indice, equipe: EquipeDTO, salas: list[SalaDTO]
) -> CodigoMotivo | None:
    """Relaxa um filtro por vez e devolve o primeiro cujo conjunto fica vazio.

    Devolve `None` quando sobra ao menos uma sala compativel no conjunto dado.

    A ordem importa e nao e arbitraria: recurso antes de capacidade e o que faz o
    cenario `estresse-recurso-escasso` responder a verdade. La existem salas
    grandes de sobra e a causa real e a bancada tecnica que elas nao tem --
    "capacidade" seria a primeira resposta encontrada, nao a certa.
    """
    if not salas:
        return CodigoMotivo.SEM_SALA_COMPATIVEL

    exigidos = _recursos_de(indice, equipe)
    salas = [s for s in salas if exigidos <= s.recursos]
    if not salas:
        return CodigoMotivo.RECURSO_INDISPONIVEL

    if _exige_acessibilidade(indice, equipe):
        salas = [s for s in salas if s.acessivel]
        if not salas:
            return CodigoMotivo.ACESSIBILIDADE_INDISPONIVEL

    salas = [s for s in salas if cabe(indice, equipe, s)]
    if not salas:
        return CodigoMotivo.SEM_SALA_COMPATIVEL

    permitidos = indice.andares_permitidos.get(equipe.id)
    if permitidos is not None:
        salas = [s for s in salas if s.andar in permitidos]
        if not salas:
            return CodigoMotivo.ANDAR_SEM_VAGA

    salas = [s for s in salas if indice.sala_reservada.get(s.id) in (None, equipe.setor_id)]
    if not salas:
        return CodigoMotivo.SEM_SALA_COMPATIVEL

    return None


def motivo_inviabilidade(
    problema: Problema, indice: Indice, equipe: EquipeDTO
) -> CodigoMotivo | None:
    """Por que nao existe sala **nenhuma** no predio para esta equipe.

    Inviabilidade estrutural: independe do que as outras equipes ocuparam.
    `None` significa que existe sala compativel -- se a equipe mesmo assim ficou
    de fora, quem responde e a disputa, nao a incompatibilidade.
    """
    return _filtro_que_esvaziou(
        indice, equipe, [s for s in problema.salas if s.disponivel]
    )


def causa_de(
    problema: Problema,
    indice: Indice,
    equipe: EquipeDTO,
    motivo: CodigoMotivo,
    estrutural: bool = True,
) -> str:
    """Frase com os numeros do caso concreto.

    `estrutural=False` significa que a sala existe no predio mas estava ocupada
    -- a diferenca entre "o predio nao tem laboratorio" e "os tres laboratorios
    ja estao com outras equipes" muda completamente o encaminhamento.

    Esta e a causa-base. O `diagnostics` a substitui quando o relaxamento por
    reexecucao consegue dizer *qual* regra remover resolveria; quando nao
    consegue -- sub-solve inconclusivo, orcamento estourado, ou nenhuma regra
    isolada bastando -- e esta frase que fica gravada. Ela nunca e um chute: os
    numeros vem da entrada e da solucao.
    """
    disponiveis = [s for s in problema.salas if s.disponivel]
    maior = max((s.capacidade for s in disponiveis), default=0)
    exigidos = sorted(_recursos_de(indice, equipe))

    match motivo:
        case CodigoMotivo.SEM_SALA_COMPATIVEL:
            return (
                f"A equipe tem {equipe.tamanho} pessoas e a maior sala disponivel "
                f"comporta {maior}."
            )
        case CodigoMotivo.RECURSO_INDISPONIVEL:
            recursos = ", ".join(exigidos) or "nenhum"
            if estrutural:
                return f"Nenhuma sala do predio reune os recursos exigidos ({recursos})."
            com_recurso = sum(1 for s in disponiveis if set(exigidos) <= s.recursos)
            return (
                f"As {com_recurso} salas com os recursos exigidos ({recursos}) ja estao "
                f"ocupadas; as salas livres nao os possuem."
            )
        case CodigoMotivo.ACESSIBILIDADE_INDISPONIVEL:
            acessiveis = sum(1 for s in disponiveis if s.acessivel)
            situacao = "nenhuma" if estrutural else "nenhuma das livres"
            return (
                f"A equipe exige acessibilidade e {situacao} das {acessiveis} salas "
                f"acessiveis comporta {equipe.tamanho} pessoas."
            )
        case CodigoMotivo.ANDAR_SEM_VAGA:
            permitidos = sorted(indice.andares_permitidos.get(equipe.id, frozenset()))
            andares = ", ".join(map(str, permitidos))
            if estrutural:
                return f"Nenhuma sala compativel nos andares permitidos ({andares})."
            return f"Todas as salas compativeis dos andares permitidos ({andares}) estao ocupadas."
        case CodigoMotivo.CONFLITO_RESTRICOES:
            return (
                "Ha sala compativel e livre, mas as restricoes rigidas que ligam esta "
                "equipe a outras nao podem ser satisfeitas ao mesmo tempo."
            )
        case _:
            return (
                f"Ha salas compativeis no predio, mas todas ja estao ocupadas no turno "
                f"{equipe.turno} por equipes de prioridade igual ou maior."
            )


def rejeicoes(
    problema: Problema, indice: Indice, alocacoes: tuple[Alocacao, ...]
) -> tuple[Rejeicao, ...]:
    """Motivo de cada equipe que ficou sem sala.

    No D2 a classificacao e estatica e factual, derivada da entrada e da solucao
    pronta -- nunca de suposicao. Em tres passos:

    1. **Inviabilidade estrutural**: nao ha sala nenhuma no predio que sirva.
       `motivo_inviabilidade` diz qual filtro esvaziou o conjunto.
    2. **Escassez**: ha sala no predio, mas entre as que sobraram livres o mesmo
       relaxamento filtro a filtro diz o que faltou -- recurso, acessibilidade ou
       andar. E o que faz o cenario `estresse-recurso-escasso` responder
       RECURSO_INDISPONIVEL e nao "capacidade".
    3. **Disputa**: sobrou sala livre e compativel. Com a regra de dominancia
       valendo, alocar sempre compensa -- entao se o solver otimo deixou a equipe
       de fora tendo onde a por, quem a impediu foi o acoplamento com outras
       equipes (CONFLITO_RESTRICOES); do contrario, o turno lotou
       (CAPACIDADE_ESGOTADA).

    O `diagnostics` refina isto relaxando uma restricao por vez e reexecutando um
    subproblema, e sabe dizer *qual* remocao tornaria a equipe alocavel. Esta
    classificacao continua sendo o piso: quando o relaxamento nao conclui, e ela
    que vai para o registro. `NaoAlocada` e append-only, e linha gravada
    incompleta nunca mais e corrigida.
    """
    alocadas = {a.equipe_id for a in alocacoes}
    equipes = {e.id: e for e in problema.equipes}
    ocupados: set[tuple[int, str]] = {
        (a.sala_id, slot) for a in alocacoes for slot in equipes[a.equipe_id].turno.slots
    }

    lista: list[Rejeicao] = []
    for equipe in problema.equipes:
        if equipe.id in alocadas:
            continue

        estrutural = True
        motivo = motivo_inviabilidade(problema, indice, equipe)

        if motivo is None:
            estrutural = False
            livres = [
                sala
                for sala in problema.salas
                if sala.disponivel
                and all((sala.id, slot) not in ocupados for slot in equipe.turno.slots)
            ]
            motivo = _filtro_que_esvaziou(indice, equipe, livres)
            if motivo in (None, CodigoMotivo.SEM_SALA_COMPATIVEL):
                motivo = (
                    CodigoMotivo.CONFLITO_RESTRICOES
                    if motivo is None and indice.acoplada(equipe.id, equipe.setor_id)
                    else CodigoMotivo.CAPACIDADE_ESGOTADA
                )

        lista.append(
            Rejeicao(
                equipe_id=equipe.id,
                codigo_motivo=motivo,
                causa=causa_de(problema, indice, equipe, motivo, estrutural),
                encaminhamento=ENCAMINHAMENTO_PADRAO[motivo],
            )
        )
    return tuple(lista)
