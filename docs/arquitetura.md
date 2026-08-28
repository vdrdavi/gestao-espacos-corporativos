# Arquitetura

## Visão geral

```
apps/web  (React + Vite)  ──HTTP──>  apps/api  (FastAPI)  ──>  SQLite
                                         │
                                         └──> engine/  (OR-Tools CP-SAT)
```

## Por que programação por restrições

O enunciado permite heurísticas, busca, algoritmos evolutivos ou bibliotecas de
otimização. A escolha por **CP-SAT** vem do critério central da atividade — não
é sobre alocar, é sobre **justificar**:

- Restrições rígidas viram restrições do modelo, então AC-1 e AC-2 valem por
  construção, não por qualidade de implementação.
- Restrições flexíveis viram termos ponderados, então a "decisão automática
  justificável" é literalmente uma expressão matemática que dá para mostrar ao
  cliente (`docs/objetivo.md`).
- O solver devolve o **valor da função objetivo**, que é o número que os testes
  metamórficos comparam entre duas execuções.

## O motor em camadas

| Módulo | Papel | Estado |
|---|---|---|
| `engine/restricoes.py` | Lê as `RestricaoDTO` e responde quais salas servem a uma equipe. | ✅ D2 |
| `engine/custo.py` | A função objetivo em Python puro, para medir uma solução pronta. | ✅ D2 |
| `engine/baseline.py` | Guloso first-fit. Representa a distribuição manual de hoje. | ✅ D2 |
| `engine/solver.py` | Modelo CP-SAT com H1–H8 e a função de custo. | ✅ D2 |
| `engine/explainer.py` | Reavalia alternativas e decompõe o custo termo a termo. | ✅ D3 |
| `engine/diagnostics.py` | Por que cada equipe ficou de fora. | ✅ D3 |
| `engine/validator.py` | Reavalia H1–H8 independentemente do solver. | ✅ D2 |

`restricoes.py` existe porque `baseline` e `solver` precisam **concordar** sobre
quais salas servem a uma equipe — se cada um lesse os parâmetros à sua maneira,
o MR-6 estaria comparando duas leituras diferentes do mesmo enunciado. `explainer`
e `diagnostics` se juntaram a eles no D3 pelo mesmo motivo: uma alternativa
oferecida na tela tem que ser viável segundo o critério que decidiu, não segundo
uma segunda leitura dele. É importado pelos quatro e, deliberadamente, **pelo
validador nunca**.

`custo.py` é a mesma função objetivo do modelo CP-SAT escrita em Python puro. A
duplicação é intencional e vem com o teste que a justifica:
`avaliar(problema, solucao.alocacoes) == solucao.custo`. Sem ele, a expressão
que o solver minimiza e a fórmula que o `docs/objetivo.md` documenta poderiam
divergir em silêncio — e a explicação mostrada ao cliente deixaria de ser a
razão real da decisão. Foi exatamente esse teste que pegou, no D3, um
`int(objective_value)` que truncava 14,999… para 14: o custo gravado ficava um
abaixo do real, sem erro nenhum, e a igualdade acima era a única coisa no
sistema capaz de notar.

O `baseline` não é código descartável — ele resolve três problemas de uma vez:

1. é a coluna **"Antes"** da tela de comparação (seção 8 do enunciado);
2. é a linha de base do **AC-5**;
3. é o **oráculo diferencial** do teste MR-6, num problema onde não se conhece
   a solução ótima.

**Ele respeita H1–H8.** É ingênuo na *escolha* — percorre as equipes na ordem de
chegada e pega a primeira sala que couber, sem olhar o que vem depois — nunca na
validade. A tentação é deixá-lo violar restrições para parecer mais com a
planilha real, mas restrição violada é restrição que não custa nada: o guloso
teria custo artificialmente baixo e o MR-6 (`custo do CP-SAT ≤ custo do guloso`)
falharia por construção, e não por bug. O oráculo do projeto se perderia no
teste que existe para proteger o motor.

O que ele não sabe fazer é **negociar**: quando duas equipes precisam ficar no
mesmo andar e não há par de salas livres, ele desiste das duas. É exatamente o
que acontece na planilha que ele representa.

## O contrato interno

O motor não conhece SQLModel. `app/problema.py` lê o banco e monta um
`Problema` de dataclasses puras (`app/engine/types.py`); o motor devolve uma
`Solucao`. Duas razões práticas:

- `baseline` e `solver` implementam a **mesma assinatura**, o que torna o teste
  diferencial MR-6 trivial;
- os testes metamórficos precisam transformar a entrada (adicionar sala,
  remover restrição, embaralhar ordem) sem passar por banco de dados.

## Entrada mutável, registro imutável

| Família | Tabelas | Regra |
|---|---|---|
| Entrada | `Sala`, `Setor`, `Equipe`, `Restricao` | CRUD completo. |
| Registro | `Run`, `Assignment`, `NaoAlocada`, `Intervencao` | **Append-only.** Nenhuma rota de `PATCH` ou `DELETE`. |

Uma alteração manual do Coordenador Geral cria uma `Intervencao` nova em vez de
editar o `Assignment` original. É isso que faz a governança responder *"quem
executou, quando, com quais dados, qual versão e qual foi o resultado"* — e
manter visível tanto o que o motor recomendou quanto o que o humano decidiu.

## Decisões que valem explicar

**Sem Alembic.** `SQLModel.create_all` no lifespan e um seed que recria o banco.
Num protótipo de uma semana o custo de manter migrations não se paga. O preço é
conhecido: mudar o schema apaga os dados locais.

**Sem autenticação.** Um seletor de perfil no cabeçalho do front. O nome
escolhido ali é o que vai para `Run.usuario` e `Intervencao.usuario` — a trilha
de auditoria precisa responder "quem executou?", e no protótipo quem responde é
o seletor.

**Uma execução reprovada pelo validador vira `Run` com status `ERRO`.** As
alocações que o motor produziu são gravadas junto. Poderia ser tentador
descartá-las e responder 500, mas o registro é append-only justamente para
mostrar o que aconteceu: sem as alocações, ninguém consegue auditar *qual* erro
o solver cometeu. Vale a mesma regra que a seção 11 aplica às equipes sem sala —
o sistema não esconde o próprio defeito.

**Explicar é pós-processamento, não uma etapa do solver.** `explainer` e
`diagnostics` recebem uma solução *pronta* e são chamados por `routers/runs.py`,
nunca de dentro de `solver.alocar`. Duas razões: o solver roda dezenas de vezes
nos testes metamórficos, onde a justificativa não interessa e só custaria tempo;
e manter a decisão e a explicação em funções separadas garante que a segunda não
possa alterar a primeira. No cenário de referência a conta fecha — solver ~0,63 s,
justificativa ~55 ms — e as métricas da execução são idênticas com e sem a camada,
o que é o teste mais simples de que ela não decide nada.

**O número que a explicação mostra é o custo marginal.** Quanto aquela equipe
naquela sala acrescenta ao custo total, com as demais alocações fixas
(`custo.custo_marginal`). É o único número que torna duas salas comparáveis entre
si: uma repartição do custo total não seria, porque os termos de par —
proximidade, separação de setores — não pertencem a uma equipe só. Um teste do
gate remede cada explicação contra `custo.avaliar` removendo a equipe da solução,
para que a conta exibida não possa divergir da que o solver minimizou.

**O diagnóstico relaxa e reexecuta, em vez de classificar.** A classificação
estática de `restricoes.rejeicoes()` responde *qual filtro esvaziou o conjunto de
salas* — factual, e inútil para quem precisa agir. `diagnostics` monta um
subproblema pequeno com uma regra a menos e chama o **mesmo** `solver.alocar`: se
a equipe passa a caber sem desalojar ninguém, aquela regra é a causa, e o
encaminhamento nomeia a sala que ela liberaria. Cada relaxamento é uma
*transformação da entrada*, nunca uma segunda modelagem — um diagnóstico com
modelo próprio poderia discordar do solver por erro de tradução e apontar a
restrição errada com toda a confiança.

A degradação é honesta: sub-solve que não prova otimalidade, orçamento estourado
ou equipes demais na fila devolvem a classificação base, não uma causa que muda
conforme a carga da máquina. O registro é append-only e o AC-7 cobra
reprodutibilidade.

**Turno como dimensão desde o D1.** A mesma sala pode servir duas equipes em
turnos diferentes. É barato no CP-SAT e é o que torna a métrica de ocupação
honesta: sem isso o prédio pareceria mais cheio do que está.
