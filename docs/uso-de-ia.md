# Uso de IA no desenvolvimento

> A seção 17 do enunciado torna o uso de IA obrigatório — e é explícita ao
> dizer que isso **não elimina a responsabilidade da equipe** sobre o código
> gerado. Este registro existe para que qualquer integrante consiga explicar
> qualquer decisão do sistema na apresentação.
>
> **Preencher diariamente.** Reconstituir isso no domingo não funciona.

## Como usar esta tabela

| Coluna | O que registrar |
|---|---|
| Data | quando |
| O quê | o artefato gerado ou alterado |
| Ferramenta | qual assistente |
| Revisão | o que foi conferido, corrigido ou reescrito à mão |
| Responsável | quem responde por esse código na demo |

## Registro

| Data | O quê | Ferramenta | Revisão | Responsável |
|---|---|---|---|---|
| 2026-08-28 | Esqueleto do D1: modelos, endpoints, seed determinístico, shell do front, CI, docs | Claude Code (Opus 5) | Stack verificada contra Python 3.14 antes de fixar versões (OR-Tools tem wheel `cp314`); calibragem do seed conferida rodando o gerador; regra de dominância dos pesos derivada à mão e coberta por teste | |
| 2026-08-28 | D2: `restricoes`, `custo`, `baseline`, `solver` CP-SAT e `validator`; `POST /api/runs` real; AC-1/2/5/7 e MR-1/2/3/4/6; resumo da execução na tela | Claude Code (Opus 5) | Gate conferido por **mutação**: desligar o filtro de capacidade quebra 8 testes. A mesma verificação derrubou duas crenças que estavam escritas como fato no código — ordem canônica e `num_workers=1` não são hoje o que faz AC-7 e MR-4 passarem, e os comentários foram corrigidos para dizer isso. A primeira versão do MR-4 renomeava salas e acusava uma diferença que era da transformação (a restrição `SALA_RESERVADA` referencia a sala por código), não do motor. Diagnóstico do cenário `estresse-recurso-escasso` corrigido: dizia "capacidade" onde a causa é o recurso escasso | |
| 2026-08-28 | D3: `custo.custo_marginal` e `Contexto`; `explainer` e `diagnostics` ligados ao `POST /api/runs`; AC-3 e AC-4 no gate; painel "Por que esta sala?" na tela | Claude Code (Opus 5) | O contrato `avaliar == solucao.custo` pegou um `int(objective_value)` que truncava 14,999… para 14 — o custo gravado ficava **um abaixo do real** e o MR-2 falhava por isso, não por bug de modelagem; trocado por `round`. Rodada de mutação sobre as camadas novas: zerar o termo de proximidade e esconder as salas ocupadas quebrou o gate, mas remover a guarda anti-desalojamento do diagnóstico **não quebrou nada** — o micro-cenário não chegava até ela, e foi reescrito com prioridades 5 contra 1 até acusar. O ramo `trade_off_global` da explicação está testado mas não é exercitado pelo cenário de referência, e `docs/criterios-aceitacao.md` diz isso em vez de deixar o "passou" sugerir cobertura que não existe | |
| 2026-08-28 | D4: `lib/alocacao.ts` (join id → nome/andar/turno), `useUltimaRun`/`useReferencia`, `MapaAndares`, `TabelaAlocacao`, `TabelaComparacao`; três `<Pendente dia="D4">` removidos de `Dashboard`, `Comparacao` e `Alocacao`; 27 testes novos de front | Claude Code (Sonnet 5) | Faixas de ocupação ancoradas no corte de 70 que o painel do D3 já usa, não numa escala inventada. A ocupação por andar do mapa é a **mesma conta turno a turno** de `Solucao.metricas` (capacidade contada uma vez por alocação): um teste reconcilia a média ponderada dos 9 andares contra o `ocupacao_media_pct` gravado (86,9). Sem execução válida as telas mostram painel honesto com link para `/alocacao` — nunca zeros. Fixtures copiadas de um `POST /api/runs` real (seed 42), não inventadas. `metricas.custo` fora da linha de total da tabela: carrega termos de par que não vivem em nenhuma linha | |

## Perguntas que a equipe precisa saber responder sem consultar o código

1. Por que CP-SAT em vez de um algoritmo guloso? → `docs/arquitetura.md`
2. O que a função de custo minimiza, e com que pesos? → `docs/objetivo.md`
3. Por que `W_NA` é 10.000 e não 10? → regra de dominância, `docs/objetivo.md`
4. Por que o `baseline` guloso continua no código depois que o solver ficou pronto?
   E por que ele **respeita** as restrições rígidas, em vez de ser ingênuo de verdade?
5. Por que `Run` e `Intervencao` não têm rota de `UPDATE`?
6. Como se testa o motor sem conhecer a solução ótima? → `apps/api/tests/test_metamorphic.py`
7. O que acontece quando duas restrições rígidas se contradizem? → cenário
   `estresse-conflito-restricoes`: o modelo não fica infactível, as duas equipes
   saem com `CONFLITO_RESTRICOES`
8. Como sabemos que o validador do AC-2 realmente verifica alguma coisa, em vez
   de sempre devolver "nenhuma violação"?
9. O número que aparece na tela ao lado de cada recomendação é o custo *de quê*?
   → custo marginal, `docs/objetivo.md` — e por que uma fatia do custo total não
   serviria
10. Por que `explainer` e `diagnostics` são chamados pelo router e não de dentro
   do `solver.alocar`?
11. O que o sistema responde quando **nenhuma** regra relaxada resolve o caso de
   uma equipe sem sala? E por que ele não escolhe uma culpada mesmo assim?
