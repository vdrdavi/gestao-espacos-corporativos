"""Smoke da API.

Cobre o contrato que o front passa a consumir a partir do D1. Se algum destes
quebrar, o front quebra junto -- e por isso que o OpenAPI e congelado hoje.
"""

import pytest


def test_health(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "ok"
    assert resposta.json()["engine_version"] == "allocation-engine-v1"


# --------------------------------------------------------------------------
# CRUD
# --------------------------------------------------------------------------


def test_crud_de_sala(client):
    criada = client.post(
        "/api/salas",
        json={"codigo": "704", "andar": 7, "capacidade": 45, "tipo": "reuniao"},
    )
    assert criada.status_code == 201
    sala_id = criada.json()["id"]

    assert client.get(f"/api/salas/{sala_id}").json()["capacidade"] == 45

    alterada = client.patch(f"/api/salas/{sala_id}", json={"capacidade": 50})
    assert alterada.status_code == 200
    assert alterada.json()["capacidade"] == 50
    assert alterada.json()["codigo"] == "704", "PATCH nao pode zerar campos omitidos"

    assert client.delete(f"/api/salas/{sala_id}").status_code == 204
    assert client.get(f"/api/salas/{sala_id}").status_code == 404


def test_codigo_de_sala_duplicado_e_rejeitado(client):
    corpo = {"codigo": "701", "andar": 7, "capacidade": 30, "tipo": "reuniao"}
    assert client.post("/api/salas", json=corpo).status_code == 201
    assert client.post("/api/salas", json=corpo).status_code == 409


def test_andar_fora_do_predio_e_rejeitado(client):
    resposta = client.post(
        "/api/salas", json={"codigo": "X", "andar": 12, "capacidade": 30, "tipo": "reuniao"}
    )
    assert resposta.status_code == 422, "o predio tem 9 andares"


def test_equipe_exige_setor_existente(client):
    resposta = client.post("/api/equipes", json={"setor_id": 999, "nome": "Fantasma", "tamanho": 10})
    assert resposta.status_code == 422


def test_setor_com_equipes_nao_pode_ser_removido(client):
    setor_id = client.post(
        "/api/setores", json={"nome": "Juridico", "coordenador": "Antonio", "total_funcionarios": 300}
    ).json()["id"]
    client.post("/api/equipes", json={"setor_id": setor_id, "nome": "Juridico Alpha", "tamanho": 12})

    assert client.delete(f"/api/setores/{setor_id}").status_code == 409


def test_filtro_por_andar(client, cenario_referencia):
    salas = client.get("/api/salas", params={"andar": 7}).json()
    assert len(salas) == 12
    assert {s["andar"] for s in salas} == {7}


# --------------------------------------------------------------------------
# Cenarios
# --------------------------------------------------------------------------


def test_listar_cenarios(client):
    nomes = {c["nome"] for c in client.get("/api/cenarios").json()}
    assert "referencia" in nomes
    assert sum(1 for n in nomes if n.startswith("estresse-")) == 3


def test_carregar_cenario_reseta_e_popula(client):
    client.post("/api/salas", json={"codigo": "999", "andar": 1, "capacidade": 5, "tipo": "reuniao"})

    dados = client.post("/api/cenarios/estresse-superdimensionada/carregar").json()

    assert dados["salas"] == 4
    codigos = {s["codigo"] for s in client.get("/api/salas").json()}
    assert "999" not in codigos, "carregar cenario tem que limpar o que havia antes"


def test_cenario_inexistente_lista_os_disponiveis(client):
    resposta = client.post("/api/cenarios/nao-existe/carregar")
    assert resposta.status_code == 404
    assert "referencia" in resposta.json()["detail"]


# --------------------------------------------------------------------------
# Motor
# --------------------------------------------------------------------------


def test_gerar_alocacao_persiste_uma_execucao_auditavel(client, cenario_referencia):
    """O caminho completo: montar, resolver, validar e registrar.

    Verifica o contrato da rota, nao a qualidade da solucao -- essa e a tarefa
    do gate (tests/test_acceptance.py). Aqui interessa que a execucao vire um
    registro capaz de responder as perguntas da secao 12.
    """
    resposta = client.post("/api/runs", json={"usuario": "coordenador-geral"})
    assert resposta.status_code == 201

    corpo = resposta.json()
    assert corpo["status"] in ("OPTIMAL", "FEASIBLE")
    assert corpo["engine_version"] == "allocation-engine-v1"
    assert len(corpo["hash_entrada"]) == 64, "sha256 em hexadecimal"
    assert corpo["pesos"]["W_NA"] == 10_000
    assert corpo["metricas"]["violacoes"] == 0
    assert corpo["metricas"]["equipes_total"] == 87
    assert corpo["metricas_baseline"], "a coluna 'Antes' da comparacao tem que vir junto"

    alocadas = corpo["metricas"]["equipes_alocadas"]
    assert len(corpo["alocacoes"]) == alocadas
    assert len(corpo["nao_alocadas"]) == 87 - alocadas


def test_a_recomendacao_gravada_carrega_a_propria_justificativa(client, cenario_referencia):
    """AC-3 pelo contrato da rota: a explicacao sai persistida, nao calculada na leitura.

    O registro e append-only e a entrada muda entre execucoes. Se a tela
    recalculasse a justificativa ao abrir a execucao, ela mostraria a razao de
    *hoje* para uma decisao tomada ontem -- exatamente o que a auditoria da secao
    12 existe para impedir.
    """
    corpo = client.post("/api/runs", json={"usuario": "coordenador-geral"}).json()
    alocacao = corpo["alocacoes"][0]

    assert alocacao["explicacao"]["resumo"]
    assert alocacao["explicacao"]["termos"], "a conta tem que vir termo a termo"
    assert alocacao["explicacao"]["comparacao"]["detalhe"]
    assert alocacao["explicacao"]["alternativas_avaliadas"] >= 1

    # Reler a execucao devolve os mesmos bytes: a justificativa esta no banco.
    relido = client.get(f"/api/runs/{corpo['id']}").json()
    assert relido["alocacoes"] == corpo["alocacoes"]

    # A separacao dos tempos deixa auditavel quanto custou explicar.
    assert corpo["metricas"]["duracao_solver_ms"] >= 0
    assert corpo["metricas"]["duracao_justificativa_ms"] >= 0


def test_o_diagnostico_da_equipe_sem_sala_aponta_o_que_mudar(client):
    """AC-4 pelo contrato da rota.

    O cenario tem salas grandes de sobra e a causa real e a bancada tecnica que
    elas nao tem. O encaminhamento gravado tem que nomear a sala que o
    relaxamento abriria -- "recurso indisponivel" sozinho nao e acionavel.
    """
    client.post("/api/cenarios/estresse-recurso-escasso/carregar")
    corpo = client.post("/api/runs", json={"usuario": "coordenador-geral"}).json()

    assert corpo["nao_alocadas"]
    for rejeitada in corpo["nao_alocadas"]:
        assert rejeitada["codigo_motivo"] == "RECURSO_INDISPONIVEL"
        assert "caberia na sala" in rejeitada["causa"]
        assert "Concretamente" in rejeitada["encaminhamento"]


def test_execucao_gravada_pode_ser_reconsultada(client, cenario_referencia):
    """Governanca: o registro tem que continuar la depois da resposta."""
    run_id = client.post("/api/runs", json={"usuario": "coordenador-geral"}).json()["id"]

    detalhe = client.get(f"/api/runs/{run_id}").json()
    assert detalhe["usuario"] == "coordenador-geral"
    assert detalhe["snapshot_entrada"]["salas"], "o snapshot responde 'com quais dados'"
    assert client.get("/api/runs").json()[0]["id"] == run_id


def test_toda_equipe_sem_sala_aparece_com_motivo(client):
    """Secao 11: o sistema mostra o que nao conseguiu resolver.

    Usa o cenario onde a resposta certa e conhecida de antemao -- equipe de 92
    pessoas contra uma sala maxima de 80.
    """
    client.post("/api/cenarios/estresse-superdimensionada/carregar")
    corpo = client.post("/api/runs", json={"usuario": "coordenador-geral"}).json()

    assert len(corpo["nao_alocadas"]) == 1
    rejeitada = corpo["nao_alocadas"][0]
    assert rejeitada["codigo_motivo"] == "SEM_SALA_COMPATIVEL"
    assert "92" in rejeitada["causa"] and "80" in rejeitada["causa"]
    assert rejeitada["encaminhamento"]


def test_metricas_do_motor_alimentam_o_painel(client, cenario_referencia):
    """Observabilidade (secao 13): o painel agrega sobre as execucoes."""
    client.post("/api/runs", json={"usuario": "coordenador-geral"})

    painel = client.get("/api/metrics").json()
    assert painel["execucoes_total"] == 1
    assert painel["execucoes_com_erro"] == 0
    assert painel["duracao_p95_ms"] is not None
    assert painel["taxa_alocacao_pct"] > 0
    assert painel["violacoes"] == 0


def test_gerar_alocacao_sem_equipes_e_erro_de_entrada(client):
    resposta = client.post("/api/runs", json={"usuario": "coordenador-geral"})
    assert resposta.status_code == 422
    assert "cenario" in resposta.json()["detail"].lower()


def test_pesos_que_quebram_a_dominancia_sao_rejeitados(client, cenario_referencia):
    """Ver docs/objetivo.md.

    Com W_NA baixo e W_OC alto, deixar uma equipe de fora fica mais barato do
    que aloca-la, e o motor passaria a esconder equipes para melhorar o proprio
    indicador. A API recusa antes de executar.
    """
    resposta = client.post(
        "/api/runs",
        json={"usuario": "coordenador-geral", "pesos": {"nao_alocada": 1, "ociosidade": 100}},
    )
    assert resposta.status_code == 422
    assert "dominancia" in resposta.json()["detail"].lower()


# --------------------------------------------------------------------------
# Governanca e observabilidade
# --------------------------------------------------------------------------


def test_historico_de_execucoes_comeca_vazio(client):
    assert client.get("/api/runs").json() == []


def test_metricas_respondem_sem_nenhuma_execucao(client):
    """O painel de monitoramento nao pode quebrar num sistema recem-instalado."""
    dados = client.get("/api/metrics").json()
    assert dados["execucoes_total"] == 0
    assert dados["duracao_p95_ms"] is None
    assert dados["engine_version"] == "allocation-engine-v1"


def test_trilha_de_auditoria_comeca_vazia(client):
    assert client.get("/api/audit").json() == []


def test_intervencao_exige_execucao_existente(client):
    resposta = client.post(
        "/api/runs/1/intervencoes", json={"usuario": "coordenador-geral", "tipo": "aceitar"}
    )
    assert resposta.status_code == 404


@pytest.mark.parametrize(
    "metodo,rota",
    [("patch", "/api/runs/1"), ("delete", "/api/runs/1"), ("delete", "/api/audit")],
)
def test_registros_sao_append_only(client, metodo, rota):
    """Nenhuma rota permite editar ou apagar o historico.

    405 (metodo nao permitido) e a resposta certa: a rota de leitura existe, a
    de escrita nunca existiu. Corrigir uma recomendacao se faz criando uma
    Intervencao.
    """
    assert getattr(client, metodo)(rota).status_code == 405


# --------------------------------------------------------------------------
# Os dois caminhos de falha do motor
# --------------------------------------------------------------------------


def test_execucao_que_estoura_vira_registro_de_erro(client, cenario_referencia, monkeypatch):
    """Uma execucao que falhou tambem e uma execucao.

    Sem este registro o painel de observabilidade ficaria cego justamente para o
    que mais importa saber depois que o sistema entra em producao.
    """
    from app.engine import solver

    def explode(*_args, **_kwargs):
        raise RuntimeError("solver indisponivel")

    monkeypatch.setattr(solver, "alocar", explode)

    assert client.post("/api/runs", json={"usuario": "coordenador-geral"}).status_code == 500

    registrada = client.get("/api/runs").json()[0]
    assert registrada["status"] == "ERRO"
    assert "solver indisponivel" in registrada["erro"]
    assert client.get("/api/metrics").json()["execucoes_com_erro"] == 1


def test_solucao_reprovada_pelo_validador_e_marcada_como_erro(
    client, cenario_referencia, monkeypatch
):
    """O validador e independente do solver para poder discordar dele.

    Quando discorda, a execucao inteira fica marcada -- e as alocacoes produzidas
    continuam gravadas, porque sem elas ninguem consegue auditar *qual* erro o
    motor cometeu.
    """
    from app.engine import validator

    monkeypatch.setattr(
        validator,
        "violacoes",
        lambda *_: [{"regra": "H1", "equipe_id": 1, "sala_id": 1, "detalhe": "estourou a sala"}],
    )

    corpo = client.post("/api/runs", json={"usuario": "coordenador-geral"}).json()

    assert corpo["status"] == "ERRO"
    assert "H1" in corpo["erro"] and "estourou a sala" in corpo["erro"]
    assert corpo["metricas"]["violacoes"] == 1
    assert corpo["alocacoes"], "as alocacoes do motor tem que ficar disponiveis para auditoria"
