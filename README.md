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

## Estado atual — D1 de 7

| | |
|---|---|
| ✅ | Modelo de dados, API completa com OpenAPI congelado, seed determinístico |
| ✅ | Shell do front consumindo a API, CI com 3 jobs, docs da função objetivo |
| ⏳ | **`POST /api/runs` responde 501** — a lógica de alocação entra no D2 |

O motor está em stub de propósito. `baseline.py`, `solver.py`, `explainer.py`,
`diagnostics.py` e `validator.py` levantam `NotImplementedError` com o dia
previsto. Um stub honesto vale mais que um guloso improvisado que depois briga
com o CP-SAT.

| Dia | Entrega |
|---|---|
| **D1** | Fundação, contratos e trilhos ← *você está aqui* |
| D2 | Baseline guloso + solver CP-SAT |
| D3 | Explicabilidade e diagnóstico de exceções |
| D4 | Dashboard, mapa dos 9 andares e tela de comparação |
| D5 | Governança, observabilidade e intervenção humana |
| D6 | Testes metamórficos e endurecimento do gate |
| D7 | Demo, evidências e apresentação |

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
| **Governança** — `Run` append-only com usuário, hash da entrada e versão do motor | `GET /api/runs` |
| **Observabilidade** — duração, taxa de alocação, intervenções por execução | `GET /api/metrics` |
| **Intervenção humana** — aceitar, rejeitar, alterar, reexecutar, tudo registrado | `POST /api/runs/{id}/intervencoes` |
| **CI** — nenhuma versão chega ao cliente sem passar pelo gate | `.github/workflows/ci.yml` |

### Testar sem conhecer a resposta certa

Para 87 equipes e 108 salas ninguém sabe de antemão qual é a melhor
configuração possível — não dá para escrever `assert resultado == esperado`. A
saída é afirmar **relações** entre execuções:

| | Transformação | Relação esperada |
|---|---|---|
| MR-1 | — | nenhuma alocação excede a capacidade |
| MR-2 | adicionar uma sala | equipes alocadas não diminui |
| MR-3 | remover uma restrição | custo não aumenta |
| MR-4 | renomear e embaralhar a entrada | métricas globais idênticas |
| MR-5 | duplicar prédio e equipes | taxa de alocação preservada |
| MR-6 | trocar o motor pelo baseline | custo do CP-SAT ≤ custo do guloso |

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
