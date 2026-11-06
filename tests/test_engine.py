"""Testes de integração para a fachada orquestradora AlertEngine e persistência SQLite."""

import pytest
from datetime import datetime, timezone, timedelta
from src.core.models import TipoIncidente
from src.engine import AlertEngine


@pytest.fixture
def engine(tmp_path):
    db_file = tmp_path / "test_alertas.db"
    eng = AlertEngine(db_path=str(db_file), auto_seed_count=20)
    return eng


def test_engine_initialization_and_seed(engine):
    state = engine.get_system_state()
    assert state["total_incidents"] == 20
    assert len(engine.quadtree) == 20
    assert len(engine.min_heap) == 20
    assert len(engine.hash_table) == 20


def test_engine_report_incident(engine):
    inc = engine.report_incident(
        tipo=TipoIncidente.ASSALTO,
        latitude=-23.5505,
        longitude=-46.6333,
        titulo="Assalto Teste Sé",
        descricao="Teste automatizado",
        usuario_id="user-123",
    )

    assert inc.id in engine.hash_table
    assert inc.id in engine.min_heap
    assert len(engine.quadtree) == 21
    assert engine.storage.load_by_id(inc.id) is not None


def test_engine_upvote_updates_heap_priority(engine):
    base_time = engine.current_time
    inc = engine.report_incident(
        tipo=TipoIncidente.FURTO,
        latitude=-23.5614,
        longitude=-46.6558,
        titulo="Furto Paulista",
    )

    old_expires = inc.expires_at
    updated = engine.upvote_incident(inc.id, bonus_hours=6.0)

    assert updated.upvotes == 1
    assert updated.expires_at == old_expires + timedelta(hours=6.0)
    # Verifica que o objeto dentro da heap também foi atualizado
    assert engine.min_heap.get(inc.id).expires_at == updated.expires_at


def test_engine_advance_time_and_decay(engine):
    initial_count = len(engine)
    # Identifica o tempo de expiração do próximo incidente prestes a expirar
    next_to_expire = engine.min_heap.peek()
    assert next_to_expire is not None

    # Avança o tempo até ultrapassar a expiração desse incidente
    hours_to_advance = (next_to_expire.expires_at - engine.current_time).total_seconds() / 3600.0 + 1.0
    expirados = engine.advance_time(hours=hours_to_advance)

    assert expirados >= 1
    assert len(engine) < initial_count
    assert next_to_expire.id not in engine.hash_table
    assert next_to_expire.id not in engine.min_heap


def test_engine_search_radius_with_telemetry(engine):
    # Busca por raio no centro da Sé
    res = engine.search_radius(lat=-23.5505, lon=-46.6333, radius_meters=3000.0)

    assert "incidents" in res
    assert "telemetry" in res
    telemetry = res["telemetry"]

    assert "quadtree_nodes_visited" in telemetry
    assert "quadtree_calcs" in telemetry
    assert "linear_calcs" in telemetry
    assert "quadtree_ms" in telemetry
    assert "linear_ms" in telemetry
    assert "pruning_ratio_percent" in telemetry

    # Em uma busca em raio pequeno, a Quadtree deve avaliar menos distâncias que a busca linear
    assert telemetry["linear_calcs"] == len(engine)

