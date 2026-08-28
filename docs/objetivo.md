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

| id | Restrição | No modelo |
|---|---|---|
| H1 | Capacidade | `x[e,s] = 1 ⟹ tamanho(e) ≤ capacidade(s)` |
| H2 | Exclusividade por turno | `Σ_e x[e,s,t] ≤ 1` |
| H3 | Recursos obrigatórios | `requeridos(e) ⊆ recursos(s)` |
| H4 | Acessibilidade | `exige_acess(e) ⟹ acessivel(s)` |
| H5 | Andares permitidos | `andar(s) ∈ permitidos(e)` |
| H6 | Sala reservada a setor | `reservada(s)=σ ⟹ setor(e)=σ` |
| H7 | Separação entre setores | setores incompatíveis não dividem andar |
| H8 | Uma sala por equipe | `Σ_s x[e,s] ≤ 1` |

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

## Histórico de versões

| Versão | Mudança |
|---|---|
| `allocation-engine-v1` | Modelo inicial: H1–H8 e os cinco termos de custo acima. |

Suba `ENGINE_VERSION` (em `apps/api/app/engine/version.py`) sempre que mudar a
modelagem das restrições ou a função de custo — não para mudanças de
infraestrutura, que não alteram o resultado. É esse campo que permite auditar,
meses depois, com qual mecanismo uma decisão foi tomada.
