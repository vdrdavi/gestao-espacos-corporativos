# Critérios de aceitação

> O enunciado (seção 14) pede pelo menos cinco critérios objetivos. São oito, e
> todos são testes automatizados em `apps/api/tests/test_acceptance.py`, que
> roda como job `gate` separado no CI.

| id | Critério | Verificação | Estado |
|---|---|---|---|
| **AC-1** | Nenhuma sala recebe mais pessoas que sua capacidade. | 0 violações em 100% das execuções, incluindo os 3 cenários de estresse. | ✅ |
| **AC-2** | Nenhuma restrição rígida é ignorada. | Validador independente do solver reavalia H1–H8 sobre o resultado. | ✅ |
| **AC-3** | Toda recomendação tem justificativa. | 100% dos `Assignment` com `explicacao` preenchida e ≥1 alternativa avaliada. | ✅ |
| **AC-4** | Toda equipe não alocada tem motivo registrado. | 100% das `NaoAlocada` com `codigo_motivo`, `causa` e `encaminhamento`. | ✅ |
| **AC-5** | A otimização não é pior que o baseline. | Ocupação ≥ baseline **e** assentos ociosos ≤ baseline **e** alocadas ≥ baseline. | ✅ |
| **AC-6** | Recomendação dentro do limite de tempo. | p95 ≤ 10 s no cenário de referência (108 salas / 87 equipes). | D6 |
| **AC-7** | Execução reprodutível. | Mesma entrada + mesma seed + mesmos pesos ⟹ métricas globais idênticas. | ✅ |
| **AC-8** | Toda execução é auditável. | Todo `Run` tem usuário, timestamp, `engine_version`, hash da entrada e métricas. | ✅ |

## Por que o validador do AC-2 tem que ser independente

Se o mesmo código que constrói as restrições também as verifica, um erro de
modelagem passa pelos dois lados sem ser notado. `engine/validator.py` reavalia
H1–H8 do zero, a partir da solução pronta, e **deve ser escrito por quem não
escreveu `engine/solver.py`**.

## O que o gate mostra hoje

No D3, sete dos oito critérios rodam de verdade. AC-1 a AC-5 são verificados nos
**quatro cenários** do catálogo, não só no de referência: é nos três de estresse
que uma implementação apressada é tentada a esconder o problema para melhorar o
próprio indicador.

Quatro testes existem para impedir que um critério passe por vacuidade:

- **`test_o_validador_acusa_uma_solucao_fabricada_acima_da_capacidade`** — um
  validador que sempre devolvesse `[]` passaria no AC-2 sem verificar nada. Este
  teste lhe entrega uma solução inválida montada à mão e exige que ele reprove.
- **`test_ac5_no_cenario_de_referencia_o_ganho_e_visivel`** — empatar com o
  guloso satisfaz "não é pior que o baseline" e ainda assim significaria que a
  otimização não serviu para nada. O gate cobra ganho real no cenário da demo.
- **`test_ac3_o_custo_da_explicacao_e_o_custo_que_o_solver_minimizou`** — uma
  explicação com números plausíveis mas inventados passaria no AC-3 e mentiria
  em cada tela. O teste remove a equipe da solução, remede com `custo.avaliar` —
  a fórmula de `objetivo.md` — e cobra o mesmo total, em todas as recomendações
  dos quatro cenários.
- **`test_ac4_o_diagnostico_aponta_a_regra_que_resolveria`** — "não coube"
  satisfaz "todo motivo registrado" e não diz o que mudar. No cenário
  `estresse-recurso-escasso` sobram salas grandes e a causa é a bancada técnica
  que elas não têm; o gate cobra que a causa nomeie a sala que o relaxamento
  abriria.

Só AC-6 (D6) aparece como **skipped**, nomeando o dia em que entra. Um gate que
passa por vacuidade é pior que nenhum gate: dá a sensação de cobertura sem a
cobertura.

### O que AC-3 e AC-4 **não** cobram

O AC-3 cobra que a explicação seja a conta real, não que ela seja lisonjeira.
Quando uma alternativa livre custa menos que a sala escolhida — o CP-SAT otimiza
o prédio, não a equipe — o critério exige que o campo `comparacao` assuma o
trade-off (`test_ac3_a_explicacao_admite_quando_a_sala_escolhida_nao_e_a_mais_barata`).
No cenário de referência isso hoje **não acontece**: das 84 recomendações, 28
são ótimas localmente e 56 não tinham outra sala livre. O ramo existe testado e
não exercitado, e este parágrafo está aqui para que ninguém leia "passou" como
"foi verificado nos dois lados".

O AC-4 também não promete que toda equipe de fora ganhe um encaminhamento
acionável. Quando nenhum relaxamento isolado resolve — a sala existe e está
ocupada por quem também precisa dela — a causa gravada diz isso, com o número de
relaxamentos testados. No cenário de referência, duas das três equipes sem sala
recebem a causa refinada e uma fica com a classificação base.

### Verificado por mutação

Um teste que nunca falhou não provou nada. Antes de fechar o D2, o gate foi
conferido desligando o filtro de capacidade do motor: **oito testes quebraram**
(AC-1, AC-2 e AC-5, nos vários cenários). O experimento também mostrou o
contrário e ficou registrado no código — a ordenação canônica do solver e o
`num_workers = 1` **não** são hoje o que faz o AC-7 e o MR-4 passarem; o CP-SAT
já devolve o mesmo resultado sem eles neste cenário. Continuam no código como
defesa para quando o solver parar antes de provar otimalidade, e o comentário
diz isso em vez de reivindicar mérito que a medição não confirmou.

No D3 o exercício se repetiu sobre as camadas novas, e a primeira rodada
**passou onde não devia**. Zerar o termo de proximidade e esconder as salas
ocupadas da lista de alternativas quebrou o gate, como se esperava. Mas remover
a guarda que impede o diagnóstico de prometer uma sala à custa de desalojar
outra equipe não quebrou nada: o micro-cenário escrito para cobri-la não chegava
até ela, porque o sub-solve já desistia antes, por outro motivo. Foi reescrito
com prioridades (5 contra 1) que fazem o CP-SAT do recorte de fato preferir
trocar uma equipe pela outra — e só então passou a acusar a mutação. O teste
anterior continua no arquivo, agora com o nome do que ele realmente cobre.
