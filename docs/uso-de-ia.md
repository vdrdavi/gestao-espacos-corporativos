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

## Perguntas que a equipe precisa saber responder sem consultar o código

1. Por que CP-SAT em vez de um algoritmo guloso? → `docs/arquitetura.md`
2. O que a função de custo minimiza, e com que pesos? → `docs/objetivo.md`
3. Por que `W_NA` é 10.000 e não 10? → regra de dominância, `docs/objetivo.md`
4. Por que o `baseline` guloso continua no código depois que o solver ficou pronto?
5. Por que `Run` e `Intervencao` não têm rota de `UPDATE`?
6. Como se testa o motor sem conhecer a solução ótima? → `apps/api/tests/test_metamorphic.py`
7. O que acontece quando duas restrições rígidas se contradizem?
