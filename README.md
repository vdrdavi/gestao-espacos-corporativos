# Sistema Inteligente de Gestão e Otimização de Espaços Corporativos

Protótipo que recebe salas, setores, equipes e restrições e produz uma proposta
otimizada de distribuição dos espaços de um prédio de 9 andares.

O objetivo do projeto não é alocar — é **conseguir justificar a alocação**. A
pergunta que ele precisa responder é:

> Como sabemos que a recomendação produzida pelo sistema é boa, confiável,
> rastreável e segura para ser usada numa decisão corporativa?

A resposta não é "porque usamos IA". É: **testes + critérios de aceitação +
explicabilidade + observabilidade + governança + intervenção humana.**

---

## Estado atual — D4 de 7

| | |
|---|---|
| ✅ | Modelo de dados, API completa com OpenAPI congelado, seed determinístico |
| ✅ | Shell do front consumindo a API, CI com 3 jobs, docs da função objetivo |
| ✅ | **O motor decide.** `POST /api/runs` resolve, valida e registra a execução |
| ✅ | **O motor explica.** Cada recomendação carrega a conta que a decidiu |
| ✅ | **As telas leem a execução.** Tabela equipe → sala, mapa dos 9 andares e comparação antes × depois |

No cenário de referência (108 salas, 87 equipes), o CP-SAT prova otimalidade em
**~0,63 s**: 84 das 87 equipes alocadas, ocupação média de 86,9%, 563 assentos
ociosos e **zero violações** — contra 79 equipes, 72,8% e 1.215 ociosos da
alocação gulosa que representa a distribuição manual de hoje.

Cada uma das 84 recomendações agora vem com o custo decomposto termo a termo, as
salas descartadas — inclusive as que teriam sido melhores e estavam ocupadas, com
o nome de quem as ocupava — e a admissão explícita de quando a escolha não foi a
melhor localmente. As três equipes sem sala passam por um diagnóstico que relaxa
uma regra por vez e reexecuta: duas recebem a sala que a mudança liberaria
(*"sem a exigência de recursos, a equipe caberia na sala 409"*), e a terceira, em
que nenhum relaxamento isolado resolve, recebe a causa que diz exatamente isso.

Explicar custa **~55 ms** sobre os ~0,63 s do solver, e as métricas da execução
são idênticas com e sem a camada — ela não decide nada, só reconstrói o porquê.

| Dia | Entrega | Estado |
|---|---|---|
| D1 | Fundação, contratos e trilhos | ✅ concluído |
| D2 | Baseline guloso + solver CP-SAT + validador independente | ✅ concluído |
| **D3** | Explicabilidade e diagnóstico de exceções | ✅ concluído |
| **D4** | Dashboard, mapa dos 9 andares e tela de comparação | ✅ concluído |
| — | — | **◀ o desenvolvimento parou aqui** |
| D5 | Governança, observabilidade e intervenção humana | ⬜ não iniciado |
| D6 | Testes metamórficos e endurecimento do gate | ⬜ não iniciado |
| D7 | Demo, evidências e apresentação | ⬜ não iniciado |

D1–D3 verificados contra as especificações em `docs/`: as 7 camadas do motor
estão implementadas (`restricoes` · `custo` · `baseline` · `solver` · `explainer`
· `diagnostics` · `validator`) e a suíte do backend fecha em **115 passed, 2
skipped** — os dois `skip` são `AC-6` e `MR-5`, ambos marcados para o D6. O D4
entregou as telas de leitura: o `Dashboard` e a `Comparacao` mostram a última
execução aprovada pelo validador (`useUltimaRun`), e a `Alocacao` desenha a
execução recém-gerada — as três com a tabela equipe → sala e o mapa dos 9
andares (`lib/alocacao.ts` faz o join id → nome/andar; o mapa é honesto quanto a
turno). Sem execução válida, as telas mostram um painel honesto com o caminho
para gerar uma, nunca zeros. O front fecha em **42 testes**. D5–D7 não começaram.

---

## Como rodar

Requisitos: **Python 3.13+** e **Node 22+**.

```bash
make setup     # cria a venv, instala backend e frontend
make seed      # popula o banco: 108 salas, 8 setores, 87 equipes
make api       # http://localhost:8000/docs
make web       # http://localhost:5173   (noutro terminal)
```

Outros atalhos: `make test` (suíte completa), `make gate` (só os critérios de
aceitação), `make lint`, `make help`.

---

## Arquitetura

```
apps/web  (React + Vite + Tailwind)  ──HTTP──>  apps/api  (FastAPI)  ──>  SQLite
                                                    │
                                                    └──> engine/  (OR-Tools CP-SAT)
```

**Por que CP-SAT.** Restrições rígidas viram restrições do modelo — uma
alocação acima da capacidade não é um bug improvável, é um estado que o modelo
não consegue representar. Restrições flexíveis viram termos ponderados da
função de custo, então a "decisão automática justificável" é literalmente uma
expressão matemática. E o solver devolve o valor do objetivo, que é o número
que os testes metamórficos comparam.

Detalhes em [`docs/arquitetura.md`](docs/arquitetura.md).

---

## A função objetivo

```
custo = W_NA · Σ  prioridade(e) · nao_alocada(e)
      + W_OC · Σ  ( capacidade(sala) − tamanho(equipe) )
      + W_PR · Σ  | andar(a) − andar(b) |     para equipes relacionadas
      + W_AP · Σ  [ andar ≠ andar preferido ]
      + W_RS · Σ  restrições flexíveis violadas
```

**A armadilha:** minimizar assentos ociosos sozinho ensina o solver a *deixar
equipes de fora* — uma equipe não alocada contribui com zero ociosidade. Por
isso vale a regra de dominância `W_NA · prioridade_mín > W_OC · Σ capacidades`,
verificada em três lugares, incluindo o CI.

Documento completo: [`docs/objetivo.md`](docs/objetivo.md).

---

## Como sabemos que a recomendação é confiável

| Mecanismo | Onde |
|---|---|
| **8 critérios de aceitação** automatizados | [`docs/criterios-aceitacao.md`](docs/criterios-aceitacao.md) · `tests/test_acceptance.py` |
| **6 relações metamórficas** — testar sem conhecer a solução ótima | `tests/test_metamorphic.py` |
| **Explicabilidade** — custo decomposto e alternativas descartadas | `engine/explainer.py` |
| **Exceções** — equipe, restrição, causa e encaminhamento | `engine/diagnostics.py` |
| **Leitura da execução** — tabela equipe → sala, mapa dos 9 andares e antes × depois | `apps/web` · `Dashboard` · `Comparacao` · `Alocacao` |
| **Governança** — `Run` append-only com usuário, hash da entrada e versão do motor | `GET /api/runs` |
| **Observabilidade** — duração, taxa de alocação, intervenções por execução | `GET /api/metrics` |
| **Intervenção humana** — aceitar, rejeitar, alterar, reexecutar, tudo registrado | `POST /api/runs/{id}/intervencoes` |
| **CI** — nenhuma versão chega ao cliente sem passar pelo gate | `.github/workflows/ci.yml` |

### Testar sem conhecer a resposta certa

Para 87 equipes e 108 salas ninguém sabe de antemão qual é a melhor
configuração possível — não dá para escrever `assert resultado == esperado`. A
saída é afirmar **relações** entre execuções:

| | Transformação | Relação esperada | |
|---|---|---|---|
| MR-1 | — | nenhuma alocação excede a capacidade | ✅ |
| MR-2 | adicionar uma sala | equipes alocadas não diminui | ✅ |
| MR-3 | remover uma restrição | custo não aumenta | ✅ |
| MR-4 | renomear e embaralhar a entrada | métricas globais idênticas | ✅ |
| MR-5 | duplicar prédio e equipes | taxa de alocação preservada | D6 |
| MR-6 | trocar o motor pelo baseline | custo do CP-SAT ≤ custo do guloso | ✅ |

MR-2, MR-3 e MR-6 comparam valores de objetivo entre execuções, e sob limite de
tempo o CP-SAT pode devolver uma solução boa mas não ótima — a comparação
quebraria por *timeout*, não por bug, e o time acabaria desabilitando o teste.
Por isso eles rodam em cenários pequenos gerados por Hypothesis, só afirmam
quando os dois lados provaram otimalidade, e passam a solução original como
`AddHint` na execução transformada.

---

## Cenários

`POST /api/cenarios/{nome}/carregar` reseta o banco e aplica um conjunto
conhecido de dados:

| Cenário | Para quê |
|---|---|
| `referencia` | 108 salas / 87 equipes / 4.585 assentos para 3.913 pessoas |
| `estresse-superdimensionada` | equipe de 92 contra sala máxima de 80 |
| `estresse-recurso-escasso` | 5 equipes exigem laboratório, existem 3 |
| `estresse-conflito-restricoes` | restrições rígidas mutuamente insatisfazíveis |

Os três de estresse existem porque a seção 11 do enunciado é avaliada: o
sistema tem que **mostrar** o que não conseguiu resolver, com causa e
encaminhamento, em vez de inflar o próprio indicador de sucesso.

---

## Estrutura

```
apps/api/         FastAPI + OR-Tools
  app/models.py     domínio em português, infraestrutura em inglês
  app/engine/       motor em camadas (baseline · solver · explainer · diagnostics · validator)
  app/problema.py   ponte banco → motor, snapshot e hash de auditoria
  seed/             cenário de referência (seed 42) e cenários de estresse
  tests/            api · seed · aceitação · metamórficos
apps/web/         React + Vite + Tailwind
docs/             objetivo · arquitetura · critérios de aceitação · uso de IA
```

O enunciado original está em
[`desafio-gestao-espacos-corporativos.md`](desafio-gestao-espacos-corporativos.md).
