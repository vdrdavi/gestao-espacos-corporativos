"""Relacoes metamorficas MR-1 a MR-6.

O problema da secao 15 do enunciado: para dezenas de equipes, salas e
restricoes, ninguem sabe de antemao qual e a melhor configuracao possivel.
Sem oraculo, nao da para escrever `assert resultado == esperado`.

A saida e testar *relacoes* entre execucoes. Nao se afirma qual e a resposta
certa; afirma-se que, ao transformar a entrada de um jeito conhecido, a saida
tem que se mover numa direcao conhecida.

    MR-1  invariante: nenhuma alocacao excede capacidade                D2
    MR-2  adicionar uma sala => alocadas nao diminui                    D2
    MR-3  remover uma restricao => custo nao aumenta                    D2
    MR-4  renomear e embaralhar => metricas globais identicas           D2
    MR-5  duplicar predio e equipes => taxa de alocacao preservada      D6
    MR-6  diferencial: custo do CP-SAT <= custo do guloso               D2

**A armadilha que derruba estes testes.** MR-2, MR-3 e MR-6 comparam valores de
objetivo entre duas execucoes. Sob limite de tempo, o CP-SAT pode devolver uma
solucao FEASIBLE mas nao otima -- e ai a monotonicidade quebra *por timeout, e
nao por bug*, gerando um teste instavel que a equipe acaba desabilitando. Um
teste desabilitado nao protege nada.

Tres mitigacoes, a usar as tres:

  (a) cenarios pequenos (<= 20 salas, <= 15 equipes), onde o solver prova
      otimalidade em milissegundos;
  (b) asserir so quando `status == OPTIMAL` nos dois lados, com pytest.skip
      caso contrario -- e registrar quantas vezes isso aconteceu;
  (c) passar a solucao da execucao original como hint (`AddHint`) na execucao
      transformada: ela ja e viavel no problema relaxado, entao o solver nunca
      devolve algo pior.

O gerador de cenarios pequenos com Hypothesis entra junto com o MR-1 no D2.
"""

import pytest

pytestmark = pytest.mark.metamorphic


@pytest.mark.skip(reason="D2 -- depende do solver")
def test_mr1_capacidade_nunca_e_excedida():
    """Invariante, verificado com cenarios gerados por Hypothesis.

    Se uma sala tem capacidade para 30, nenhuma recomendacao valida coloca 31
    pessoas nela -- para *qualquer* entrada, nao so para as que escrevemos.
    """


@pytest.mark.skip(reason="D2 -- depende do solver")
def test_mr2_adicionar_sala_nao_reduz_equipes_alocadas():
    """Adicionar uma sala sem mudar mais nada so amplia o espaco de solucoes.

    Se o numero de equipes alocadas cair, ha dependencia de ordem ou o solver
    parou cedo demais.
    """


@pytest.mark.skip(reason="D2 -- depende do solver")
def test_mr3_remover_restricao_nao_aumenta_o_custo():
    """Remover uma restricao relaxa o problema; o otimo nao pode piorar."""


@pytest.mark.skip(reason="D2 -- depende do solver")
def test_mr4_renomear_e_embaralhar_nao_muda_as_metricas():
    """O teste que mais encontra bug de verdade.

    Duas equipes com exatamente os mesmos requisitos nao podem produzir
    solucoes de qualidade diferente so porque tem nomes diferentes ou chegaram
    em outra ordem. Qualquer dependencia de ordem de iteracao -- um dict
    percorrido sem ordenacao, um desempate por indice -- aparece aqui. Rodar
    com muitos exemplos.
    """


@pytest.mark.skip(reason="D6 -- cenario grande, marcado slow")
def test_mr5_duplicar_o_problema_preserva_a_taxa_de_alocacao():
    """Dobrar predio e equipes mantem taxa de alocacao e ocupacao (+- 2 p.p.)."""


@pytest.mark.skip(reason="D2 -- depende de baseline + solver")
def test_mr6_solver_nunca_perde_para_o_guloso():
    """Teste diferencial: o baseline e o oraculo que o projeto tem.

    Nao se sabe qual e a solucao otima, mas sabe-se que o CP-SAT nao pode ser
    pior que o first-fit ingenuo. Cobre o AC-5 pelo lado do motor.
    """
