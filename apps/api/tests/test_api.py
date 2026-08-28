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
# Motor (stub no D1)
# --------------------------------------------------------------------------


def test_gerar_alocacao_responde_501_com_o_pipeline_ate_o_motor(client, cenario_referencia):
    """O D1 entrega tudo ate a fronteira do solver.

    O 501 nao e um erro generico: ele prova que a montagem do problema, o
    snapshot e o hash de entrada ja funcionam, e diz em que dia a etapa que
    falta entra.
    """
    resposta = client.post("/api/runs", json={"usuario": "coordenador-geral"})
    assert resposta.status_code == 501

    detalhe = resposta.json()["detail"]
    assert detalhe["previsto_para"] == "D2"

    pipeline = detalhe["pipeline_ate_aqui"]
    assert pipeline["salas"] == 108
    assert pipeline["equipes"] == 87
    assert len(pipeline["hash_entrada"]) == 64, "sha256 em hexadecimal"
    assert pipeline["pesos"]["W_NA"] == 10_000


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
