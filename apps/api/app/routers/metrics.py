"""Observabilidade -- "Monitoramento do Motor de Alocacao" (secao 13).

Tudo aqui e agregacao sobre Run e Intervencao. Nenhuma metrica e escrita a
mao em lugar nenhum: como as tabelas de registro sao append-only, o painel nao
tem como divergir do que de fato aconteceu.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.engine.version import ENGINE_VERSION
from app.enums import StatusRun
from app.models import Intervencao, Run
from app.schemas import MetricasRead

router = APIRouter(prefix="/api/metrics", tags=["observabilidade"])
SessionDep = Annotated[Session, Depends(get_session)]


def _percentil(valores: list[int], p: float) -> int | None:
    """Percentil por interpolacao mais proxima. Suficiente para o painel."""
    if not valores:
        return None
    ordenados = sorted(valores)
    indice = min(int(round(p * (len(ordenados) - 1))), len(ordenados) - 1)
    return ordenados[indice]


def _media(valores: list[float]) -> float | None:
    return round(sum(valores) / len(valores), 1) if valores else None


@router.get("", response_model=MetricasRead, summary="Indicadores do motor")
def obter(session: SessionDep) -> MetricasRead:
    runs = list(session.exec(select(Run).order_by(Run.criado_em.desc())).all())
    intervencoes = list(session.exec(select(Intervencao)).all())

    ok = [r for r in runs if r.status in (StatusRun.OPTIMAL, StatusRun.FEASIBLE)]
    duracoes = [r.duracao_ms for r in ok]
    ultima = ok[0] if ok else None

    return MetricasRead(
        execucoes_total=len(runs),
        execucoes_com_erro=sum(1 for r in runs if r.status is StatusRun.ERRO),
        duracao_ultima_ms=ultima.duracao_ms if ultima else None,
        duracao_p50_ms=_percentil(duracoes, 0.50),
        duracao_p95_ms=_percentil(duracoes, 0.95),
        ocupacao_media_pct=_media(
            [r.metricas.get("ocupacao_media_pct", 0.0) for r in ok if r.metricas]
        ),
        taxa_alocacao_pct=(
            round(
                ultima.metricas["equipes_alocadas"] / ultima.metricas["equipes_total"] * 100, 1
            )
            if ultima and ultima.metricas.get("equipes_total")
            else None
        ),
        equipes_nao_alocadas=(
            ultima.metricas.get("equipes_nao_alocadas") if ultima and ultima.metricas else None
        ),
        violacoes=(ultima.metricas.get("violacoes", 0) if ultima and ultima.metricas else None),
        intervencoes_total=len(intervencoes),
        # A metrica mais interessante do painel: se o Coordenador Geral altera
        # muitas recomendacoes por execucao, o motor esta desalinhado com o
        # julgamento humano. E o sinal de degradacao mais proximo de um drift
        # que da para ter num prototipo.
        intervencoes_por_execucao=(
            round(len(intervencoes) / len(runs), 2) if runs else None
        ),
        engine_version=ENGINE_VERSION,
    )
