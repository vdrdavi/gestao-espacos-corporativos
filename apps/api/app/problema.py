"""Ponte entre o banco e o motor.

Le as tabelas de entrada e monta o `Problema` de dataclasses puras que o motor
consome, junto com o snapshot e o hash que vao para o registro de governanca.

O hash e o que permite responder "com quais dados?" (secao 12) e sustentar o
AC-7: duas execucoes com o mesmo hash, a mesma seed e os mesmos pesos tem que
produzir as mesmas metricas globais.
"""

import hashlib
import json

from sqlmodel import Session, select

from app.engine.types import EquipeDTO, Pesos, Problema, RestricaoDTO, SalaDTO
from app.models import Equipe, Restricao, Sala


def _ordenado(dados: list[dict]) -> list[dict]:
    """Ordena por id para que o snapshot nao dependa da ordem do SELECT."""
    return sorted(dados, key=lambda d: d["id"])


def montar_snapshot(session: Session) -> dict:
    salas = session.exec(select(Sala)).all()
    equipes = session.exec(select(Equipe)).all()
    restricoes = session.exec(select(Restricao)).all()

    return {
        "salas": _ordenado(
            [
                {
                    "id": s.id,
                    "codigo": s.codigo,
                    "andar": s.andar,
                    "capacidade": s.capacidade,
                    "tipo": str(s.tipo),
                    "recursos": sorted(s.recursos),
                    "acessivel": s.acessivel,
                    "disponivel": s.disponivel,
                    "reservada_para_setor_id": s.reservada_para_setor_id,
                }
                for s in salas
            ]
        ),
        "equipes": _ordenado(
            [
                {
                    "id": e.id,
                    "nome": e.nome,
                    "setor_id": e.setor_id,
                    "tamanho": e.tamanho,
                    "turno": str(e.turno),
                    "recursos_requeridos": sorted(e.recursos_requeridos),
                    "exige_acessibilidade": e.exige_acessibilidade,
                    "andar_preferido": e.andar_preferido,
                    "prioridade": e.prioridade,
                }
                for e in equipes
            ]
        ),
        "restricoes": _ordenado(
            [
                {
                    "id": r.id,
                    "tipo": str(r.tipo),
                    "alvo_tipo": str(r.alvo_tipo),
                    "alvo_id": r.alvo_id,
                    "parametros": r.parametros,
                    "rigida": r.rigida,
                    "peso": r.peso,
                }
                for r in restricoes
            ]
        ),
    }


def hash_entrada(snapshot: dict) -> str:
    """sha256 canonico do snapshot.

    `sort_keys=True` e obrigatorio: sem ele, duas execucoes identicas gerariam
    hashes diferentes so pela ordem das chaves do dict.
    """
    canonico = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def montar_problema(
    session: Session,
    pesos: Pesos | None = None,
    seed: int = 42,
    limite_segundos: float = 10.0,
) -> Problema:
    snapshot = montar_snapshot(session)

    salas = tuple(
        SalaDTO(
            id=s["id"],
            codigo=s["codigo"],
            andar=s["andar"],
            capacidade=s["capacidade"],
            tipo=s["tipo"],
            recursos=frozenset(s["recursos"]),
            acessivel=s["acessivel"],
            disponivel=s["disponivel"],
            reservada_para_setor_id=s["reservada_para_setor_id"],
        )
        for s in snapshot["salas"]
    )
    equipes = tuple(
        EquipeDTO(
            id=e["id"],
            nome=e["nome"],
            setor_id=e["setor_id"],
            tamanho=e["tamanho"],
            turno=e["turno"],
            recursos_requeridos=frozenset(e["recursos_requeridos"]),
            exige_acessibilidade=e["exige_acessibilidade"],
            andar_preferido=e["andar_preferido"],
            prioridade=e["prioridade"],
        )
        for e in snapshot["equipes"]
    )
    restricoes = tuple(
        RestricaoDTO(
            id=r["id"],
            tipo=r["tipo"],
            parametros=r["parametros"],
            rigida=r["rigida"],
            peso=r["peso"],
            alvo_id=r["alvo_id"],
        )
        for r in snapshot["restricoes"]
    )

    return Problema(
        salas=salas,
        equipes=equipes,
        restricoes=restricoes,
        pesos=pesos or Pesos(),
        limite_segundos=limite_segundos,
        seed=seed,
    )
