"""Testes do gerador de cenarios.

O determinismo do seed nao e detalhe de conveniencia: e a base do AC-7. Se a
mesma seed produzir prediios diferentes, nenhuma comparacao entre duas
execucoes -- nem a tela de "Antes x Depois", nem os testes metamorficos --
significa coisa alguma.
"""

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.problema import hash_entrada, montar_snapshot
from seed.cenarios import CENARIOS
from seed.generate import gerar


def _banco_novo():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _hash_com_seed(seed: int) -> str:
    with Session(_banco_novo()) as session:
        gerar(session, seed=seed)
        return hash_entrada(montar_snapshot(session))


def test_seed_e_deterministico():
    """Mesma seed, dois processos de geracao independentes, mesmo hash."""
    assert _hash_com_seed(42) == _hash_com_seed(42)


def test_seeds_diferentes_geram_predios_diferentes():
    """Guarda contra o oposto: um gerador que ignora a seed tambem passaria
    no teste acima."""
    assert _hash_com_seed(42) != _hash_com_seed(7)


def test_dimensoes_do_cenario_de_referencia(cenario_referencia):
    dados = cenario_referencia
    assert dados["salas"] == 108, "9 andares x 12 salas"
    assert dados["setores"] == 8
    assert dados["equipes"] == 87, "mesmo numero do exemplo da secao 12 do enunciado"
    assert dados["funcionarios_declarados"] == 7_000


def test_demanda_cabe_folgadamente_abaixo_da_capacidade(cenario_referencia):
    """O cenario tem que ser apertado, mas nao impossivel.

    Se a demanda passasse da capacidade, o motor so saberia dizer "nao coube" e
    nao haveria o que otimizar. Se sobrasse capacidade demais, qualquer
    alocacao serviria e a otimizacao nao apareceria na tela de comparacao.
    """
    ocupacao_teorica = cenario_referencia["pessoas_em_equipes"] / cenario_referencia[
        "capacidade_total"
    ]
    assert 0.60 < ocupacao_teorica < 0.95, (
        f"ocupacao teorica de {ocupacao_teorica:.0%} deixa o cenario "
        "trivial ou impossivel -- recalibrar seed/generate.py"
    )


def test_todos_os_cenarios_carregam(session):
    for nome, cenario in sorted(CENARIOS.items()):
        dados = cenario.aplicar(session, seed=42)
        assert dados["salas"] > 0, f"cenario {nome} nao gerou salas"
        assert dados["equipes"] > 0, f"cenario {nome} nao gerou equipes"


def test_cenario_superdimensionada_reproduz_o_exemplo_do_enunciado(session):
    """Equipe de 92 pessoas contra a maior sala de 80 (secao 11)."""
    from sqlmodel import select

    from app.models import Equipe, Sala

    CENARIOS["estresse-superdimensionada"].aplicar(session, seed=42)

    maior_equipe = max(session.exec(select(Equipe)).all(), key=lambda e: e.tamanho)
    maior_sala = max(session.exec(select(Sala)).all(), key=lambda s: s.capacidade)

    assert maior_equipe.tamanho == 92
    assert maior_sala.capacidade == 80
    assert maior_equipe.tamanho > maior_sala.capacidade
