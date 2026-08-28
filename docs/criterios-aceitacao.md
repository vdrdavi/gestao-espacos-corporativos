# Critérios de aceitação

> O enunciado (seção 14) pede pelo menos cinco critérios objetivos. São oito, e
> todos são testes automatizados em `apps/api/tests/test_acceptance.py`, que
> roda como job `gate` separado no CI.

| id | Critério | Verificação | Estado |
|---|---|---|---|
| **AC-1** | Nenhuma sala recebe mais pessoas que sua capacidade. | 0 violações em 100% das execuções, incluindo os 3 cenários de estresse. | D2 |
| **AC-2** | Nenhuma restrição rígida é ignorada. | Validador independente do solver reavalia H1–H8 sobre o resultado. | D2 |
| **AC-3** | Toda recomendação tem justificativa. | 100% dos `Assignment` com `explicacao` preenchida e ≥1 alternativa avaliada. | D3 |
| **AC-4** | Toda equipe não alocada tem motivo registrado. | 100% das `NaoAlocada` com `codigo_motivo`, `causa` e `encaminhamento`. | D3 |
| **AC-5** | A otimização não é pior que o baseline. | Ocupação ≥ baseline **e** assentos ociosos ≤ baseline **e** alocadas ≥ baseline. | D2 |
| **AC-6** | Recomendação dentro do limite de tempo. | p95 ≤ 10 s no cenário de referência (108 salas / 87 equipes). | D6 |
| **AC-7** | Execução reprodutível. | Mesma entrada + mesma seed + mesmos pesos ⟹ métricas globais idênticas. | **D1** (entrada) / D2 |
| **AC-8** | Toda execução é auditável. | Todo `Run` tem usuário, timestamp, `engine_version`, hash da entrada e métricas. | **D1** |

## Por que o validador do AC-2 tem que ser independente

Se o mesmo código que constrói as restrições também as verifica, um erro de
modelagem passa pelos dois lados sem ser notado. `engine/validator.py` reavalia
H1–H8 do zero, a partir da solução pronta, e **deve ser escrito por quem não
escreveu `engine/solver.py`**.

## O que o gate mostra hoje

No D1 rodam de verdade os critérios que não dependem do motor:

- **AC-7 (metade)** — o mesmo seed produz a mesma entrada, e o hash reage a
  qualquer mudança. Sem isso, comparar duas execuções não significa nada.
- **AC-8** — teste estrutural: cada pergunta da governança (quem, quando, com
  quais dados, qual versão, qual resultado) tem um campo obrigatório em `Run`
  que a responde.
- **Dominância dos pesos** — pré-condição do AC-5, verificável sem o motor.

Os demais aparecem como **skipped**, nomeando o dia em que entram. Um gate que
passa por vacuidade é pior que nenhum gate: dá a sensação de cobertura sem a
cobertura.
