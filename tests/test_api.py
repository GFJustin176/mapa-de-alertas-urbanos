"""Testes de integração para a API REST FastAPI do Sentinela SP."""

import pytest
from fastapi.testclient import TestClient
from src.api.app import app, get_engine


@pytest.fixture
def client(tmp_path):
    # Garante um banco temporário isolado para testes da API
    engine = get_engine()
    engine.reset_simulation(seed_count=25)
    return TestClient(app)


def test_api_get_state(client):
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    assert "current_time" in data
    assert "total_incidents" in data
    assert "quadtree" in data
    assert "min_heap" in data
    assert "hash_table" in data
    assert "grid_graph" in data


def test_api_search_radius(client):
    response = client.get("/api/search?lat=-23.5505&lon=-46.6333&radius_m=3000")
    assert response.status_code == 200
    data = response.json()
    assert "incidents" in data
    assert "telemetry" in data
    assert data["telemetry"]["linear_calcs"] > 0
    assert data["telemetry"]["quadtree_nodes_visited"] > 0


def test_api_report_incident_and_upvote(client):
    payload = {
        "tipo": "ASSALTO",
        "latitude": -23.5505,
        "longitude": -46.6333,
        "titulo": "Assalto Teste API",
        "descricao": "Teste de integração",
    }
    # Criar incidente
    post_res = client.post("/api/incidents", json=payload)
    assert post_res.status_code == 201
    inc_data = post_res.json()
    inc_id = inc_data["id"]

    # Dar upvote (+2 horas)
    upvote_res = client.post(f"/api/incidents/{inc_id}/upvote")
    assert upvote_res.status_code == 200
    updated = upvote_res.json()
    assert updated["upvotes"] == 1


def test_api_simulate_time_and_bulk_seed(client):
    # Injetar incidentes em lote
    bulk_res = client.post("/api/simulate/seed", json={"count": 50})
    assert bulk_res.status_code == 200
    assert bulk_res.json()["injected"] == 50

    # Avançar relógio em 60 horas para forçar decaimento
    time_res = client.post("/api/simulate/time", json={"hours": 60.0})
    assert time_res.status_code == 200
    assert time_res.json()["expired_count"] > 0
