"""Validador independente das restricoes rigidas (AC-2).

Reavalia H1-H8 sobre uma solucao pronta, **sem** usar o codigo que construiu o
modelo CP-SAT. A independencia e o ponto: se o mesmo codigo que monta as
restricoes tambem as verifica, um erro de modelagem passa pelos dois lados.

Por isso este arquivo **nao importa** `solver.py`, `baseline.py`, `restricoes.py`
nem `custo.py` -- ele le `RestricaoDTO` por conta propria, com sua propria
interpretacao dos parametros. A duplicacao de leitura e deliberada: e ela que faz
o teste ter valor. Se um dia um parametro mudar de nome e so um dos dois lados
for atualizado, o AC-2 quebra -- que e exatamente o comportamento desejado.

Tambem e o que roda quando o Coordenador Geral altera uma alocacao a mao -- o
sistema avisa que a alteracao viola uma restricao, registra o alerta, e nao
bloqueia: a decisao final e humana (secao 10).
"""

from app.engine.types import Problema, Solucao
from app.enums import TipoRestricao


def _violacao(regra: str, detalhe: str, equipe_id: int | None = None,
              sala_id: int | None = None) -> dict:
    return {"regra": regra, "equipe_id": equipe_id, "sala_id": sala_id, "detalhe": detalhe}


def violacoes(problema: Problema, solucao: Solucao) -> list[dict]:
    """Lista de violacoes de restricao rigida. Vazia = solucao valida."""
    salas = {s.id: s for s in problema.salas}
    equipes = {e.id: e for e in problema.equipes}
    achadas: list[dict] = []

    # ------------------------------------------------------------------ H8
    # Uma sala por equipe. Checado antes de tudo porque uma equipe em duas salas
    # falsearia todas as contagens abaixo.
    vistas: dict[int, int] = {}
    for alocacao in solucao.alocacoes:
        if alocacao.equipe_id in vistas:
            achadas.append(
                _violacao(
                    "H8",
                    f"equipe alocada em duas salas ({vistas[alocacao.equipe_id]} e "
                    f"{alocacao.sala_id})",
                    alocacao.equipe_id,
                    alocacao.sala_id,
                )
            )
        vistas[alocacao.equipe_id] = alocacao.sala_id

    for alocacao in solucao.alocacoes:
        equipe = equipes.get(alocacao.equipe_id)
        sala = salas.get(alocacao.sala_id)
        if equipe is None or sala is None:
            achadas.append(
                _violacao("H0", "alocacao referencia equipe ou sala inexistente",
                          alocacao.equipe_id, alocacao.sala_id)
            )
            continue

        if not sala.disponivel:
            achadas.append(
                _violacao("H0", f"sala {sala.codigo} esta indisponivel",
                          equipe.id, sala.id)
            )

        # -------------------------------------------------------------- H1
        if equipe.tamanho > sala.capacidade:
            achadas.append(
                _violacao(
                    "H1",
                    f"{equipe.tamanho} pessoas em sala {sala.codigo} de capacidade "
                    f"{sala.capacidade}",
                    equipe.id,
                    sala.id,
                )
            )

        # -------------------------------------------------------------- H3
        faltantes = set(equipe.recursos_requeridos) - set(sala.recursos)
        if faltantes:
            achadas.append(
                _violacao("H3", f"sala {sala.codigo} nao tem {', '.join(sorted(faltantes))}",
                          equipe.id, sala.id)
            )

        # -------------------------------------------------------------- H4
        if equipe.exige_acessibilidade and not sala.acessivel:
            achadas.append(
                _violacao("H4", f"sala {sala.codigo} nao e acessivel", equipe.id, sala.id)
            )

        # -------------------------------------------------------------- H6
        if (
            sala.reservada_para_setor_id is not None
            and sala.reservada_para_setor_id != equipe.setor_id
        ):
            achadas.append(
                _violacao(
                    "H6",
                    f"sala {sala.codigo} e reservada ao setor "
                    f"{sala.reservada_para_setor_id}",
                    equipe.id,
                    sala.id,
                )
            )

    # ------------------------------------------------------------------ H2
    # Duas equipes na mesma sala no mesmo slot elementar. INTEGRAL consome os dois.
    ocupantes: dict[tuple[int, str], int] = {}
    for alocacao in solucao.alocacoes:
        equipe = equipes.get(alocacao.equipe_id)
        if equipe is None:
            continue
        for slot in equipe.turno.slots:
            anterior = ocupantes.get((alocacao.sala_id, slot))
            if anterior is not None:
                achadas.append(
                    _violacao(
                        "H2",
                        f"equipes {anterior} e {equipe.id} na mesma sala no turno {slot}",
                        equipe.id,
                        alocacao.sala_id,
                    )
                )
            ocupantes[alocacao.sala_id, slot] = equipe.id

    achadas += _violacoes_de_restricao(problema, solucao, salas, equipes)
    return achadas


def _violacoes_de_restricao(problema: Problema, solucao: Solucao, salas, equipes) -> list[dict]:
    """H5, H6 e H7 declarados como `Restricao`, mais capacidade minima e proximidade.

    Leitura propria dos parametros -- ver o docstring do modulo.
    """
    achadas: list[dict] = []
    andar_da_equipe = {
        a.equipe_id: salas[a.sala_id].andar for a in solucao.alocacoes if a.sala_id in salas
    }
    sala_da_equipe = {
        a.equipe_id: salas[a.sala_id] for a in solucao.alocacoes if a.sala_id in salas
    }
    ids_de_equipe = set(equipes)
    equipes_do_setor: dict[int, list[int]] = {}
    for equipe in problema.equipes:
        equipes_do_setor.setdefault(equipe.setor_id, []).append(equipe.id)

    def atingidas(restricao) -> list[int]:
        if restricao.alvo_id is None:
            return list(ids_de_equipe)
        if restricao.alvo_id in ids_de_equipe:
            return [restricao.alvo_id]
        return equipes_do_setor.get(restricao.alvo_id, [])

    for restricao in problema.restricoes:
        if not restricao.rigida:
            continue
        parametros = restricao.parametros or {}

        if restricao.tipo is TipoRestricao.ANDAR_PERMITIDO:
            permitidos = set(parametros.get("andares", []))
            for equipe_id in atingidas(restricao):
                andar = andar_da_equipe.get(equipe_id)
                if permitidos and andar is not None and andar not in permitidos:
                    achadas.append(
                        _violacao(
                            "H5",
                            f"andar {andar} fora dos permitidos "
                            f"({sorted(permitidos)}) pela restricao {restricao.id}",
                            equipe_id,
                            sala_da_equipe[equipe_id].id,
                        )
                    )

        elif restricao.tipo is TipoRestricao.SALA_RESERVADA:
            setor_id = parametros.get("setor_id")
            codigo = parametros.get("codigo_sala")
            sala_id = parametros.get("sala_id")
            for equipe_id, sala in sala_da_equipe.items():
                mesma_sala = sala.id == sala_id or (codigo is not None and sala.codigo == codigo)
                if mesma_sala and equipes[equipe_id].setor_id != setor_id:
                    achadas.append(
                        _violacao(
                            "H6",
                            f"sala {sala.codigo} e reservada ao setor {setor_id} "
                            f"pela restricao {restricao.id}",
                            equipe_id,
                            sala.id,
                        )
                    )

        elif restricao.tipo is TipoRestricao.CAPACIDADE_MINIMA:
            minima = parametros.get("minima") or parametros.get("capacidade_minima")
            for equipe_id in atingidas(restricao):
                sala = sala_da_equipe.get(equipe_id)
                if minima and sala is not None and sala.capacidade < int(minima):
                    achadas.append(
                        _violacao(
                            "H1",
                            f"sala {sala.codigo} tem {sala.capacidade} lugares e a "
                            f"restricao {restricao.id} exige {minima}",
                            equipe_id,
                            sala.id,
                        )
                    )

        elif restricao.tipo is TipoRestricao.RECURSO_OBRIGATORIO:
            exigidos = {
                str(r) for r in (parametros.get("recursos") or [parametros.get("recurso")]) if r
            }
            for equipe_id in atingidas(restricao):
                sala = sala_da_equipe.get(equipe_id)
                if sala is not None and not exigidos <= set(sala.recursos):
                    achadas.append(
                        _violacao(
                            "H3",
                            f"sala {sala.codigo} nao atende a restricao {restricao.id} "
                            f"({', '.join(sorted(exigidos))})",
                            equipe_id,
                            sala.id,
                        )
                    )

        elif restricao.tipo is TipoRestricao.ACESSIBILIDADE_OBRIGATORIA:
            for equipe_id in atingidas(restricao):
                sala = sala_da_equipe.get(equipe_id)
                if sala is not None and not sala.acessivel:
                    achadas.append(
                        _violacao(
                            "H4",
                            f"sala {sala.codigo} nao e acessivel (restricao {restricao.id})",
                            equipe_id,
                            sala.id,
                        )
                    )

        elif restricao.tipo is TipoRestricao.SEPARACAO_SETORES:
            setor_a, setor_b = parametros.get("setor_a"), parametros.get("setor_b")
            def andares_de(setor: int | None) -> set[int]:
                return {
                    andar_da_equipe[e]
                    for e in equipes_do_setor.get(setor, [])
                    if e in andar_da_equipe
                }

            andares_a, andares_b = andares_de(setor_a), andares_de(setor_b)
            for andar in sorted(andares_a & andares_b):
                achadas.append(
                    _violacao(
                        "H7",
                        f"setores {setor_a} e {setor_b} dividem o andar {andar} "
                        f"(restricao {restricao.id})",
                    )
                )

        elif restricao.tipo is TipoRestricao.PROXIMIDADE:
            equipe_a, equipe_b = parametros.get("equipe_a"), parametros.get("equipe_b")
            andar_a, andar_b = andar_da_equipe.get(equipe_a), andar_da_equipe.get(equipe_b)
            # Rigida com uma so das duas alocadas tambem e violacao: a regra e
            # "mesmo andar ou nenhuma das duas".
            if (andar_a is None) != (andar_b is None) or (
                andar_a is not None and andar_a != andar_b
            ):
                achadas.append(
                    _violacao(
                        "H7",
                        f"equipes {equipe_a} e {equipe_b} deveriam ficar no mesmo andar "
                        f"(restricao {restricao.id})",
                        equipe_a,
                    )
                )

    return achadas
