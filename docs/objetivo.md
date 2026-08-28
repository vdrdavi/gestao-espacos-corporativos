# Função objetivo

> Escrito antes do código, como entregável conceitual do D1. É este documento
> que responde à pergunta 2 da demonstração: *por que determinada sala foi
> recomendada para determinada equipe?*

## O que é uma boa alocação

Uma alocação é boa quando **aloca o máximo de equipes**, **desperdiça o mínimo
de assentos** e **respeita as restrições**. As três coisas competem entre si, e
por isso precisam estar na mesma expressão matemática — não em três regras
soltas que se contradizem em silêncio.

O motor separa as regras em duas naturezas:

| Natureza | Como entra no modelo | Pode ser violada? |
|---|---|---|
| **Rígida** | restrição do modelo CP-SAT | Nunca. É um estado que o modelo não consegue representar. |
| **Flexível** | termo ponderado da função de custo | Sim, se o ganho compensar o peso. |

Essa separação é o que faz os critérios AC-1 e AC-2 valerem **por construção**:
uma alocação acima da capacidade não é um bug improvável de heurística, é uma
solução que o solver não tem como produzir.

## Restrições rígidas

| id | Restrição | No modelo | Como entra no CP-SAT |
|---|---|---|---|
| H1 | Capacidade | `x[e,s] = 1 ⟹ tamanho(e) ≤ capacidade(s)` | a variável não é criada |
| H2 | Exclusividade por turno | `Σ_e x[e,s,t] ≤ 1` | uma soma por sala e por slot |
| H3 | Recursos obrigatórios | `requeridos(e) ⊆ recursos(s)` | a variável não é criada |
| H4 | Acessibilidade | `exige_acess(e) ⟹ acessivel(s)` | a variável não é criada |
| H5 | Andares permitidos | `andar(s) ∈ permitidos(e)` | a variável não é criada |
| H6 | Sala reservada a setor | `reservada(s)=σ ⟹ setor(e)=σ` | a variável não é criada |
| H7 | Separação entre setores | setores incompatíveis não dividem andar | `ocupa[σ,andar]`, soma ≤ 1 |
| H8 | Uma sala por equipe | `Σ_s x[e,s] ≤ 1` | soma sobre as salas viáveis |

**"A variável não é criada" é mais forte que "a restrição é imposta."** H1 e
H3–H6 dependem só do par (equipe, sala), então `x[e,s]` só existe para os pares
viáveis: o estado inválido não é proibido, ele não é representável. O modelo
também fica menor — no cenário de referência, das 87 × 108 combinações possíveis
sobra uma fração, e o solver prova otimalidade em ~0,6 s.

**O modelo nunca é infactível.** Com H8 em `≤`, deixar todas as equipes de fora
é sempre uma solução viável — caríssima, mas viável. É deliberado: "2 equipes sem
sala, motivo CONFLITO_RESTRICOES" informa muito mais que um `INFEASIBLE` seco.

**H8 usa `≤ 1`, não `= 1`.** Uma equipe *pode* ficar sem sala. Forçar igualdade
tornaria o modelo inviável nos cenários de estresse, e o enunciado exige
justamente o contrário: que o sistema mostre o problema em vez de escondê-lo
(seção 11).

## Custo a minimizar

```
custo = W_NA · Σ_e  prioridade(e) · nao_alocada(e)
      + W_OC · Σ_e  ( capacidade(sala(e)) − tamanho(e) )      // assentos ociosos
      + W_PR · Σ_(a,b)∈proximidade  | andar(a) − andar(b) |
      + W_AP · Σ_e  [ andar(sala(e)) ≠ andar_preferido(e) ]
      + W_RS · Σ    restrições flexíveis violadas
```

Pesos padrão:

| Peso | Símbolo | Valor | Significado |
|---|---|---:|---|
| Não alocar | `W_NA` | 10.000 | por pessoa-prioridade deixada sem sala |
| Ociosidade | `W_OC` | 1 | por assento vazio numa sala ocupada |
| Proximidade | `W_PR` | 50 | por andar de distância entre equipes relacionadas |
| Andar preferido | `W_AP` | 20 | por preferência de andar não atendida |
| Restrição flexível | `W_RS` | 200 | por restrição flexível violada |

Os pesos são **dados de entrada, não constantes**. O Coordenador Geral pode
ajustá-los na interface e reexecutar, e cada `Run` grava os pesos que usou —
então duas execuções são sempre comparáveis.

**Peso por restrição.** Uma `Restricao` flexível pode trazer o próprio `peso`, e
quando ele é maior que zero sobrepõe o peso global — é o que permite dizer "esta
proximidade específica vale mais que as outras" sem mexer nos pesos da execução
inteira. Proximidade usa `W_PR` sobre `|Δ andar|`; as demais flexíveis usam
`W_RS` por violação.

**Proximidade só conta entre equipes alocadas.** Uma equipe sem sala não tem
andar; cobrar dela a distância até a parceira seria cobrar duas vezes pelo mesmo
problema, já que ela paga `W_NA`.

## A regra de dominância

> Esta é a armadilha que derruba a maioria das implementações deste problema.

Minimizar assentos ociosos, sozinho, ensina o solver a **deixar equipes de
fora**: uma equipe não alocada contribui com zero ociosidade, então esconder
equipes *melhora* o custo enquanto piora a solução. Para que isso nunca
compense, alocar qualquer equipe na pior sala possível tem que custar menos do
que não alocá-la:

```
W_NA · prioridade_mínima  >  W_OC · Σ_s capacidade(s)
```

Com os pesos padrão e o cenário de referência: `10.000 × 1 > 1 × 4.585`. ✓

Violar a regra não gera erro de execução — gera uma solução silenciosamente
errada, do tipo que passa despercebido numa demonstração. Por isso ela é
verificada em três lugares:

1. `Pesos.dominancia_ok()` em `apps/api/app/engine/types.py`;
2. `POST /api/runs` recusa com **422** antes de executar;
3. `test_ac5_pesos_padrao_respeitam_a_dominancia`, no gate do CI.

## Explicabilidade

O CP-SAT devolve o ótimo global, não a razão de uma alocação individual. O
`explainer` reavalia, para cada equipe, as salas viáveis com **a mesma** função
de custo acima, e devolve as cinco melhores com o custo decomposto termo a
termo:

```
Sala 701 recomendada para Equipe Alpha.

  Capacidade 50 · Equipe 46 · Ocupação prevista 92%
  Alternativas avaliadas: 5

  ociosidade       4 assentos × W_OC 1     =    4
  andar preferido  atendido                =    0
  proximidade      Beta no 7º, Δ=0         =    0
  custo total                              =    4

  melhor alternativa descartada
  Sala 812 · custo 34 (14 assentos ociosos, andar preferido não atendido)
```

É o que transforma *"o algoritmo decidiu"* em *"esta sala custa 4 e a segunda
melhor custa 34"*.

**O número exibido é o custo marginal**: quanto esta equipe nesta sala acrescenta
ao custo total, com as demais alocações fixas (`custo.custo_marginal`). Não é uma
fatia do custo total — os termos de par não pertencem a uma equipe só, e
reparti-los daria um número que não compara nada. O marginal, sim: é exatamente o
que mudaria se a equipe se mudasse de sala. `W_NA` não aparece porque ele é o
custo de *não* alocar, e quem está sendo explicado aqui tem sala.

São sempre os **mesmos quatro termos, na mesma ordem**, mesmo quando valem zero.
Um zero explícito — "andar preferido atendido" — informa tanto quanto um custo, e
é o que permite comparar duas salas linha a linha para dizer o que a descartada
piora.

**As alternativas são reais.** Só entram salas que a equipe poderia de fato
ocupar naquela execução: viáveis por H1 e H3–H6, livres no turno dela (H2) e sem
quebrar H7 nem a proximidade rígida. Uma sala compatível mas **ocupada** aparece
na lista marcada com quem a ocupa — num prédio quase cheio ela é a maior parte da
resposta, e *"a 812 seria igual, mas está com a equipe 12"* é o que o Coordenador
Geral precisa para decidir se intervém. O que nunca aparece é uma sala onde a
equipe não caberia: seria explicar a decisão com uma opção que nunca existiu.

**A explicação admite quando a sala escolhida não é a mais barata.** O solver
otimiza o prédio inteiro, não esta equipe — às vezes ela paga mais caro para que
outra caiba melhor. Nesse caso o campo `comparacao` diz `trade_off_global` e
mostra a diferença, em vez de afirmar que a escolha foi a melhor. Afirmar seria
mentir num campo que existe justamente para tornar a decisão auditável.

## Por que uma equipe ficou de fora

A classificação estática responde *qual filtro esvaziou o conjunto de salas*. É
factual e não serve para agir. O `diagnostics` responde a pergunta que o
Coordenador Geral realmente faz — *o que eu mudo para resolver?* — relaxando uma
regra por vez e reexecutando um subproblema pequeno com o **mesmo** solver:

```
Sem a exigência de recursos, a equipe (54 pessoas) caberia na sala 409 do
4º andar, que comporta 59 — e sem tirar nenhuma outra equipe do lugar.
É a única regra que, sozinha, resolve este caso.
```

Duas condições protegem essa frase de ser falsa:

- **Ninguém pode ser desalojado.** Uma "solução" que aloca esta equipe tirando
  outra do lugar não resolveu nada, só trocou quem fica de fora.
- **Sub-solve que não prova otimalidade não vira resposta.** Orçamento estourado
  ou recorte grande demais devolvem a classificação base. Uma causa que mudasse
  conforme a carga da máquina quebraria o AC-7 num registro append-only.

## Histórico de versões

| Versão | Mudança |
|---|---|
| `allocation-engine-v1` | Modelo inicial: H1–H8 e os cinco termos de custo acima. Implementado no D2 sem alteração da modelagem descrita aqui. O D3 acrescentou explicabilidade e diagnóstico, que **leem** esta função sem mudá-la, e corrigiu um truncamento na leitura do valor objetivo (`int` → `round`) que baixava o custo gravado em uma unidade. A modelagem não mudou; a versão não sobe. |

Suba `ENGINE_VERSION` (em `apps/api/app/engine/version.py`) sempre que mudar a
modelagem das restrições ou a função de custo — não para mudanças de
infraestrutura, que não alteram o resultado. É esse campo que permite auditar,
meses depois, com qual mecanismo uma decisão foi tomada.
