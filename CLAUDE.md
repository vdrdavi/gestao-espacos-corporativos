# CLAUDE.md

Protótipo de alocação de equipes em espaços corporativos (9 andares, 108 salas).
O critério central do projeto não é alocar — é **conseguir justificar a
alocação**. Quando houver dúvida entre duas opções, escolha a que deixa a
decisão mais auditável.

Estado: **D1 de 7**. O motor está em stub; `POST /api/runs` responde 501.

## Comandos

```bash
make setup   # venv + npm install
make api     # http://localhost:8000/docs
make web     # http://localhost:5173
make seed    # recria o banco: 108 salas, 8 setores, 87 equipes (seed 42)
make test    # backend + frontend
make gate    # só os critérios de aceitação e as relações metamórficas
make lint    # ruff + tsc
```

A venv fica na **raiz** (`.venv/`), mas o pytest roda **de `apps/api`** —
`pythonpath = ["."]` no `pyproject.toml` é o que torna `app` e `seed`
importáveis. Rodando à mão:

```bash
cd apps/api && ../../.venv/bin/python -m pytest -q
```

## Convenção de nomes

**Domínio em português, infraestrutura em inglês.** `Sala.capacidade`,
`Equipe.tamanho`, `montar_problema()` — mas `Field`, `Session`, `router`,
`get_session`. Valores de enum são ASCII sem acento, porque viram chave de JSON
e coluna de banco (`"reuniao"`, não `"reunião"`).

## Regras que não se quebram

1. **Append-only.** `Run`, `Assignment`, `NaoAlocada` e `Intervencao` nunca
   sofrem `UPDATE` nem `DELETE`, e nenhuma rota expõe `PATCH`/`DELETE` sobre
   elas. Corrigir uma recomendação se faz criando uma `Intervencao` nova. É o
   que faz a governança responder "quem decidiu o quê" em vez de virar log
   decorativo.

2. **Dominância dos pesos.** `W_NA · prioridade_mín > W_OC · Σ capacidades`.
   Sem isso o solver aprende a deixar equipes de fora para zerar assentos
   ociosos — e isso não dá erro, dá uma solução silenciosamente errada.
   Verificada em três lugares: `Pesos.dominancia_ok()`, o 422 de `POST
   /api/runs`, e o gate do CI. Mexeu em peso, confira os três.

3. **O validador é independente do solver.** `engine/validator.py` reavalia
   H1–H8 do zero a partir da solução pronta. Não importe nem espelhe a
   modelagem de `engine/solver.py`: se o mesmo código constrói e verifica as
   restrições, um erro de modelagem passa pelos dois lados.

4. **Stub honesto em vez de implementação provisória.** O que ainda não existe
   levanta `EtapaNaoImplementada(etapa, dia)` ou renderiza `<Pendente dia=…>`.
   Nunca um guloso improvisado "só para ter algo na tela" — ele vira dívida no
   dia em que o código real chega, e some do radar porque a tela parece pronta.

## Os marcadores D1–D7

`D1`…`D7` são os dias do cronograma. Aparecem em quatro lugares:

| Onde | Forma |
|---|---|
| Testes | `@pytest.mark.skip(reason="D2 -- depende do solver")` |
| Motor | `EtapaNaoImplementada("O solver CP-SAT", "D2")` |
| Front | `<Pendente dia="D4" o="…" />` |
| Código | comentários `# No D2 o validator entra aqui` |

Ao implementar um dia, **remova o marcador junto com o código** — nunca deixe
um `skip` órfão apontando para um dia que já passou. Se algo escorregar de dia,
atualize o marcador em vez de apagá-lo: o valor dele é dizer a verdade sobre o
que ainda não existe.

## Onde ler mais

| Documento | Quando consultar |
|---|---|
| [docs/objetivo.md](docs/objetivo.md) | Antes de mexer em pesos, restrições ou na função de custo. Traz H1–H8, os cinco termos e a regra de dominância. |
| [docs/arquitetura.md](docs/arquitetura.md) | Antes de adicionar um módulo ao `engine/` ou uma tabela. Explica por que CP-SAT e por que o baseline guloso continua no código. |
| [docs/criterios-aceitacao.md](docs/criterios-aceitacao.md) | Antes de tocar em `tests/test_acceptance.py`. Os 8 critérios e o dia de cada um. |
| [docs/uso-de-ia.md](docs/uso-de-ia.md) | Preencher ao fim de cada sessão de trabalho — a equipe precisa saber explicar o código na apresentação. |
| [README.md](README.md) | Visão geral, como rodar, e as 6 relações metamórficas. |
| [desafio-gestao-espacos-corporativos.md](desafio-gestao-espacos-corporativos.md) | O enunciado. Fonte de verdade sobre o que é avaliado. |
