# Sistema Inteligente de Gestão e Otimização de Espaços Corporativos

> **Tempo disponível:** 1 semana
> **Modalidade:** desenvolvimento rápido de protótipo funcional
> **Uso de Inteligência Artificial:** obrigatório
> **Contexto:** Qualidade e Testes de Sistemas Baseados em IA — ISTQB CT-AI
> **Entrega:** protótipo funcional + repositório + evidências de testes

---

## Sumário

1. [Situação-problema](#1-situação-problema)
2. [Estrutura de gestão](#2-estrutura-de-gestão)
3. [Missão da equipe](#3-missão-da-equipe)
4. [O que significa uma boa alocação?](#4-o-que-significa-uma-boa-alocação)
5. [Entradas mínimas do sistema](#5-entradas-mínimas-do-sistema)
6. [Motor inteligente de alocação](#6-motor-inteligente-de-alocação)
7. [Dashboard executivo](#7-dashboard-executivo)
8. [Tela de comparação](#8-tela-de-comparação)
9. [Explicabilidade](#9-explicabilidade)
10. [Intervenção humana](#10-intervenção-humana)
11. [Tratamento de exceções](#11-tratamento-de-exceções)
12. [Governança](#12-governança)
13. [Observabilidade](#13-observabilidade)
14. [Critérios de aceitação](#14-critérios-de-aceitação)
15. [Testando sem conhecer a solução ótima](#15-testando-um-sistema-sem-saber-previamente-qual-é-a-solução-ótima)
16. [CI/CD](#16-cicd)
17. [Uso obrigatório de IA durante o desenvolvimento](#17-uso-obrigatório-de-ia-durante-o-desenvolvimento)
18. [Escopo esperado](#18-escopo-esperado)
19. [Entregáveis](#19-entregáveis)
20. [Organização da semana](#20-organização-da-semana)
21. [Demonstração final](#21-demonstração-final)
22. [Critério central do desafio](#22-critério-central-do-desafio)

---

## 1. Situação-problema

Uma empresa multinacional possui aproximadamente **7.000 funcionários** distribuídos em um prédio corporativo de **9 andares**.

O prédio possui salas de reunião, salas de treinamento, auditórios, laboratórios, salas de projeto e espaços de trabalho colaborativo com diferentes capacidades e características.

Atualmente, a distribuição desses espaços é realizada de forma predominantemente **manual**. Isso gera problemas como:

- espaços grandes utilizados por equipes pequenas;
- equipes grandes alocadas em ambientes inadequados;
- salas ociosas enquanto outros setores enfrentam falta de espaço;
- conflitos de horário;
- uso inadequado de salas especiais;
- dificuldade de visualizar a ocupação do prédio;
- dificuldade de justificar por que determinado setor recebeu determinada sala;
- baixa capacidade de reorganização diante de mudanças.

A multinacional decidiu desenvolver um **Sistema Inteligente de Gestão e Otimização de Espaços Corporativos**.

Sua equipe foi contratada para produzir, em apenas **uma semana**, um protótipo funcional capaz de ser apresentado ao cliente.

---

## 2. Estrutura de gestão

O sistema deverá considerar **dois níveis de decisão**.

### Coordenador Geral

Administra os espaços físicos do prédio. Ele poderá:

- cadastrar ou visualizar as salas disponíveis;
- informar a capacidade de cada sala;
- definir características e restrições;
- visualizar a ocupação dos nove andares;
- disponibilizar conjuntos de salas para os diferentes setores;
- executar uma otimização global;
- analisar conflitos e exceções;
- aprovar ou revisar sugestões produzidas pelo sistema.

### Coordenadores de Setor

Cada setor da multinacional possui seu próprio coordenador. Exemplos de setores:

- Tecnologia
- Recursos Humanos
- Financeiro
- Jurídico
- Marketing
- Comercial
- Operações
- Pesquisa e Desenvolvimento

Cada Coordenador de Setor poderá informar:

- quantidade de funcionários;
- equipes existentes;
- horários necessários;
- tamanho das equipes;
- necessidade de equipamentos;
- preferência por determinado andar;
- necessidade de acessibilidade;
- salas ou setores que precisam permanecer próximos;
- restrições específicas.

O sistema deverá utilizar essas informações para sugerir a distribuição mais adequada dos espaços disponibilizados pelo Coordenador Geral.

---

## 3. Missão da equipe

Utilizando ferramentas de Inteligência Artificial como apoio ao desenvolvimento, sua equipe deverá construir um **protótipo funcional full stack** capaz de:

> Receber informações sobre salas, setores, equipes e restrições e produzir automaticamente uma proposta otimizada de distribuição dos espaços corporativos.

O objetivo **não** é simplesmente encontrar qualquer sala disponível. O sistema deverá tentar encontrar a **melhor combinação possível** entre demanda e capacidade disponível.

---

## 4. O que significa uma boa alocação?

A equipe deverá estabelecer uma **função de otimização**. Uma possível abordagem é considerar simultaneamente:

### Maximizar

- número de equipes corretamente alocadas;
- percentual de ocupação das salas;
- atendimento das restrições;
- proximidade entre equipes relacionadas.

### Minimizar

- assentos ociosos;
- salas subutilizadas;
- conflitos;
- violações de restrições;
- movimentação desnecessária entre andares.

**Exemplo:** uma equipe com 12 funcionários não deveria ocupar uma sala para 80 pessoas se existe uma sala para 15 disponível. Da mesma forma, uma equipe com 60 funcionários não pode ser colocada em uma sala com capacidade para 40.

---

## 5. Entradas mínimas do sistema

O sistema deverá permitir trabalhar, no mínimo, com:

### Sala

- identificação
- andar
- capacidade
- tipo
- recursos disponíveis
- acessibilidade
- disponibilidade

### Setor

- nome
- coordenador
- quantidade total de funcionários

### Equipe

- setor
- quantidade de funcionários
- horário
- requisitos especiais
- prioridade

### Restrições

Exemplos:

- capacidade mínima;
- andar permitido;
- acessibilidade obrigatória;
- equipamento obrigatório;
- proximidade entre equipes;
- determinados setores não podem compartilhar uma área;
- sala reservada para determinado setor;
- prioridade de determinada equipe.

---

## 6. Motor inteligente de alocação

O sistema deverá possuir uma função **Gerar alocação**. Ao executá-la, o sistema deverá analisar os dados disponíveis e retornar uma sugestão.

**Exemplo de saída:**

| Equipe            | Pessoas | Sala sugerida | Capacidade | Andar |
| ----------------- | ------: | ------------- | ---------: | ----- |
| Desenvolvimento A |      42 | Sala 704      |         45 | 7º    |
| Desenvolvimento B |      18 | Sala 702      |         20 | 7º    |
| RH                |      28 | Sala 503      |         30 | 5º    |
| Financeiro        |      54 | Sala 402      |         60 | 4º    |

Não é necessário implementar um modelo complexo de Machine Learning. É permitido utilizar:

- heurísticas;
- algoritmos de busca;
- otimização;
- programação por restrições;
- algoritmos evolutivos;
- bibliotecas de otimização;
- componentes baseados em IA;
- combinações dessas abordagens.

> O importante é que exista uma **decisão automática justificável**.

---

## 7. Dashboard executivo

O Coordenador Geral deverá possuir um dashboard capaz de visualizar rapidamente a situação do prédio. O dashboard deverá apresentar pelo menos:

- ocupação total do prédio;
- ocupação por andar;
- capacidade disponível;
- quantidade de funcionários alocados;
- quantidade de funcionários ou equipes não alocados;
- salas disponíveis;
- salas ocupadas;
- percentual de utilização;
- quantidade de restrições violadas.

A representação poderá utilizar cards, gráficos, tabelas, mapas simplificados dos andares e indicadores visuais.

---

## 8. Tela de comparação

O sistema deverá permitir compreender se a recomendação produzida é realmente vantajosa. Apresente pelo menos:

- **Situação inicial** — distribuição existente ou alocação simples.
- **Situação otimizada** — distribuição sugerida pelo sistema.

**Exemplo:**

| Indicador       |  Antes | Depois |
| --------------- | -----: | -----: |
| Ocupação média  |    61% |    84% |
| Assentos ociosos |  1.420 |    580 |
| Equipes sem sala |     12 |      3 |
| Violações       |      8 |      0 |

> Os números acima são apenas ilustrativos.

---

## 9. Explicabilidade

Um sistema corporativo não deve simplesmente informar:

> "Equipe A → Sala 701."

Ele deverá **explicar a decisão**. Ao selecionar uma recomendação, o usuário deverá visualizar algo semelhante a:

```text
Sala 701 recomendada para Equipe Alpha.

Capacidade da sala: 50 pessoas
Equipe: 46 pessoas
Ocupação prevista: 92%
Recursos necessários atendidos: sim
Restrição de andar atendida: sim
Alternativas avaliadas: 5

Esta sala apresentou o melhor equilíbrio entre capacidade,
localização e restrições dentre as alternativas disponíveis.
```

A explicação poderá ser simplificada. Entretanto, deverá permitir ao usuário compreender **por que** aquela decisão foi tomada.

---

## 10. Intervenção humana

A recomendação do sistema **não** deverá ser tratada como uma decisão absoluta. O Coordenador Geral deverá poder:

- aceitar a recomendação;
- rejeitar;
- alterar manualmente uma alocação;
- solicitar nova otimização.

O sistema deverá **registrar** essa intervenção. A decisão final continua pertencendo ao responsável humano.

---

## 11. Tratamento de exceções

Nem todo problema possuirá solução perfeita. O sistema deverá identificar situações como:

```text
Equipe Delta possui 92 funcionários.
Maior sala disponível possui capacidade para 80.

Resultado:
ALERTA — não foi encontrada uma sala compatível.
```

O sistema não deverá esconder o problema nem realizar uma alocação inválida apenas para aumentar artificialmente seu indicador de sucesso. Deverá apresentar:

- equipe afetada;
- restrição não atendida;
- causa;
- possível encaminhamento.

---

## 12. Governança

Toda execução do mecanismo de recomendação deverá produzir um registro mínimo.

**Exemplo:**

```text
Execução: #145
Data/hora: 14:32
Usuário: coordenador-geral
Algoritmo: allocation-engine-v1
Equipes analisadas: 87
Salas analisadas: 108
Equipes alocadas: 82
Equipes não alocadas: 5
Restrições violadas: 0
Ocupação prevista: 86%
```

O objetivo é permitir responder posteriormente:

- Quem executou?
- Quando?
- Com quais dados?
- Qual versão do mecanismo foi utilizada?
- Qual foi o resultado?

---

## 13. Observabilidade

Imagine que o sistema entrou em produção. A empresa precisa saber se o mecanismo de recomendação continua funcionando corretamente.

O protótipo deverá apresentar, mesmo que de maneira simplificada, indicadores como:

- tempo necessário para gerar uma recomendação;
- número de execuções;
- percentual médio de ocupação;
- quantidade de conflitos;
- quantidade de equipes não alocadas;
- quantidade de alterações manuais realizadas após recomendações;
- erros ocorridos.

**Exemplo:**

```text
Tempo da última otimização: 1,8 s
Taxa de alocação: 96%
Ocupação média: 84%
Violações: 0
Intervenções manuais: 7
```

Essas informações poderão aparecer em uma área denominada **Monitoramento do Motor de Alocação**.

---

## 14. Critérios de aceitação

A equipe deverá definir critérios objetivos para determinar quando uma recomendação pode ser considerada aceitável. Exemplos:

- nenhuma sala poderá receber mais pessoas que sua capacidade;
- nenhuma restrição obrigatória poderá ser ignorada;
- 100% das recomendações deverão possuir justificativa;
- todas as equipes não alocadas deverão possuir motivo registrado;
- o sistema deverá reduzir a ociosidade em relação à estratégia inicial;
- recomendações deverão ser produzidas dentro de um limite de tempo definido pela equipe.

> Cada grupo deverá definir **pelo menos cinco** critérios de aceitação.

---

## 15. Testando um sistema sem saber previamente qual é a solução ótima

Existe um problema interessante: para dezenas de equipes, salas e restrições, provavelmente vocês **não** sabem antecipadamente qual é a melhor configuração possível.

> Como testar um sistema quando não conhecemos exatamente a resposta ideal?

Sua equipe deverá criar **pelo menos três testes** baseados em propriedades ou relações esperadas.

### Teste 1 — Capacidade

Se uma sala possui capacidade para 30 pessoas, nenhuma recomendação válida poderá colocar 31 pessoas nela.

### Teste 2 — Expansão da capacidade

Se adicionarmos uma nova sala ao prédio e não alterarmos nenhuma outra condição, a quantidade de equipes possíveis de alocar não deveria diminuir.

### Teste 3 — Remoção de restrição

Se uma restrição for removida, o espaço de soluções possíveis aumenta. Portanto, a nova solução não deveria apresentar menos possibilidades exclusivamente por causa da retirada daquela restrição.

### Teste 4 — Equipes equivalentes

Se duas equipes possuem exatamente os mesmos requisitos, pequenas alterações irrelevantes em seus nomes não deveriam alterar drasticamente a qualidade global da solução.

> Esse tipo de raciocínio aproxima o exercício de **testes metamórficos**, especialmente úteis quando determinar antecipadamente uma resposta exata é difícil.

---

## 16. CI/CD

O projeto deverá possuir um pipeline mínimo de integração contínua. A cada atualização enviada ao repositório, o pipeline deverá executar automaticamente pelo menos:

- instalação das dependências;
- build ou validação da aplicação;
- execução dos testes automatizados.

**Sugestão de fluxo:**

```text
git push
   ↓
Pipeline CI
   ↓
Build
   ↓
Testes
   ↓
Resultado
```

É permitido utilizar, por exemplo, GitHub Actions, GitLab CI ou outra ferramenta equivalente.

O objetivo não é criar infraestrutura complexa. É demonstrar que uma mudança no sistema não deve chegar automaticamente ao cliente sem passar por algum mecanismo de verificação.

---

## 17. Uso obrigatório de IA durante o desenvolvimento

Existe uma restrição adicional neste desafio: vocês possuem apenas **uma semana**. Portanto, utilizar IA para acelerar o desenvolvimento faz parte da atividade.

É permitido e recomendado utilizar ferramentas de IA para:

- gerar componentes;
- criar telas;
- implementar APIs;
- gerar dados fictícios;
- sugerir algoritmos;
- gerar testes;
- depurar erros;
- criar o pipeline CI/CD;
- construir dashboards;
- melhorar interfaces.

> Entretanto: utilizar IA para gerar código **não elimina a responsabilidade da equipe** sobre o código gerado. A equipe deverá ser capaz de explicar as principais decisões do sistema.

---

## 18. Escopo esperado

Não tentem construir um produto completo. Construam um **MVP demonstrável**.

Ao final da semana, deve ser possível executar uma demonstração semelhante a:

| Etapa | Ação |
| ----: | ---- |
| 1 | O Coordenador Geral abre o dashboard. |
| 2 | Visualiza a ocupação dos nove andares. |
| 3 | Um Coordenador de Setor cadastra ou altera a quantidade de funcionários de uma equipe. |
| 4 | São definidas algumas restrições. |
| 5 | O usuário executa **GERAR ALOCAÇÃO OTIMIZADA**. |
| 6 | O sistema apresenta a distribuição proposta. |
| 7 | O usuário seleciona uma recomendação e visualiza sua justificativa. |
| 8 | O dashboard mostra os indicadores da nova configuração. |
| 9 | O usuário visualiza situações que não puderam ser resolvidas. |
| 10 | A equipe demonstra os testes e o pipeline CI/CD. |

---

## 19. Entregáveis

Ao final da semana, cada equipe deverá entregar:

1. **Repositório do projeto** — código, README e instruções de execução.
2. **Protótipo funcional** — front-end e back-end integrados.
3. **Motor de recomendação** — mesmo que simples.
4. **Dashboard** — com indicadores de ocupação.
5. **Evidência de explicabilidade** — pelo menos uma recomendação deverá apresentar justificativa.
6. **Evidência de observabilidade** — dashboard, logs ou métricas.
7. **Evidência de governança** — histórico de execução ou auditoria.
8. **Testes automatizados** — incluindo pelo menos três testes relacionados ao comportamento do mecanismo de recomendação.
9. **Pipeline CI/CD** — build e testes executados automaticamente.

---

## 20. Organização da semana

Sugestão de divisão:

| Tempo      | Atividade                                       |
| ---------- | ----------------------------------------------- |
| 0–15 min   | compreender o problema e definir arquitetura     |
| 15–30 min  | definir regras e estratégia de alocação          |
| 30–80 min  | desenvolvimento assistido por IA                 |
| 80–100 min | testes + CI/CD                                   |
| 100–110 min | observabilidade, explicabilidade e governança   |
| 110–120 min | preparação da demonstração                      |

---

## 21. Demonstração final

Cada equipe deverá demonstrar o sistema respondendo às seguintes perguntas:

1. Como o sistema distribuiu os funcionários pelos espaços?
2. Por que determinada sala foi recomendada para determinada equipe?
3. O que acontece quando não existe solução possível?
4. Como vocês sabem que uma nova versão do sistema não piorou a solução?
5. Se o sistema apresentar uma recomendação, por que o Coordenador Geral deveria confiar nela?

A última pergunta é a mais importante. A resposta **não** deverá ser:

> "Porque usamos Inteligência Artificial."

A confiança deverá ser sustentada por:

**testes + critérios de aceitação + explicabilidade + observabilidade + governança + possibilidade de intervenção humana**

---

## 22. Critério central do desafio

O objetivo desta atividade não é descobrir quem consegue gerar a interface mais bonita utilizando IA.

O objetivo é demonstrar que vocês conseguem utilizar IA para acelerar a construção de um sistema e, simultaneamente, desenvolver mecanismos para responder:

> **Como sabemos que a recomendação produzida pelo sistema é boa, confiável, rastreável e segura para ser utilizada em uma decisão corporativa?**

Esse é o verdadeiro problema que deverá ser resolvido.
