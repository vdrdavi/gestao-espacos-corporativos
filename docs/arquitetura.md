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

| Módulo | Papel | Entra em |
|---|---|---|
| `engine/baseline.py` | Guloso first-fit. Representa a distribuição manual de hoje. | D2 |
| `engine/solver.py` | Modelo CP-SAT com H1–H8 e a função de custo. | D2 |
| `engine/explainer.py` | Reavalia alternativas e decompõe o custo termo a termo. | D3 |
| `engine/diagnostics.py` | Por que cada equipe ficou de fora. | D3 |
| `engine/validator.py` | Reavalia H1–H8 independentemente do solver. | D2 |

O `baseline` não é código descartável — ele resolve três problemas de uma vez:

1. é a coluna **"Antes"** da tela de comparação (seção 8 do enunciado);
2. é a linha de base do **AC-5**;
3. é o **oráculo diferencial** do teste MR-6, num problema onde não se conhece
   a solução ótima.

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

**Turno como dimensão desde o D1.** A mesma sala pode servir duas equipes em
turnos diferentes. É barato no CP-SAT e é o que torna a métrica de ocupação
honesta: sem isso o prédio pareceria mais cheio do que está.
