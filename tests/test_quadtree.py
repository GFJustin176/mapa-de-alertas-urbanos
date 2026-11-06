"""Testes unitários exaustivos para a Quadtree espacial com Range Query e Merge dinâmico."""

import pytest
from datetime import datetime, timezone, timedelta
from src.core.models import Incidente, TipoIncidente, BoundingBox
from src.core.geo import haversine_meters
from src.structures.quadtree import Quadtree


def _criar_incidente(id_inc: str, lat: float, lon: float) -> Incidente:
    now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    return Incidente(
        id=id_inc,
        tipo=TipoIncidente.ASSALTO,
        latitude=lat,
        longitude=lon,
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )


def test_quadtree_subdivide_at_fifth_element():
    # Bounding box cobrindo o centro de São Paulo
    boundary = BoundingBox(min_lat=-23.60, max_lat=-23.50, min_lon=-46.70, max_lon=-46.60)
    qt = Quadtree(boundary=boundary, capacity=4, max_depth=10)

    # Inserção de 4 elementos: não deve subdividir
    for i in range(1, 5):
        qt.insert(_criar_incidente(f"i{i}", -23.55 + i * 0.005, -46.65 + i * 0.005))

    assert qt.root.is_divided is False
    assert len(qt.root.points) == 4
    assert len(qt) == 4

    # 5º elemento força a subdivisão em 4 quadrantes (NW, NE, SW, SE)
    qt.insert(_criar_incidente("i5", -23.52, -46.62))
    assert qt.root.is_divided is True
    assert len(qt.root.points) == 0  # Pontos migrados para os filhos
    assert len(qt) == 5


def test_quadtree_max_depth_prevents_infinite_recursion():
    boundary = BoundingBox(min_lat=-23.60, max_lat=-23.50, min_lon=-46.70, max_lon=-46.60)
    qt = Quadtree(boundary=boundary, capacity=4, max_depth=2)

    # Inserir 6 pontos exatamente na mesma coordenada
    for i in range(6):
        qt.insert(_criar_incidente(f"same-{i}", -23.55, -46.65))

    assert len(qt) == 6


def test_quadtree_query_radius_matches_linear_search():
    boundary = BoundingBox(min_lat=-23.70, max_lat=-23.45, min_lon=-46.80, max_lon=-46.45)
    qt = Quadtree(boundary=boundary, capacity=4, max_depth=10)

    # Cria 30 pontos espalhados
    incidentes = []
    for i in range(30):
        lat = -23.65 + (i % 6) * 0.03
        lon = -46.75 + (i // 6) * 0.05
        inc = _criar_incidente(f"p-{i}", lat, lon)
        incidentes.append(inc)
        qt.insert(inc)

    center_lat, center_lon = -23.55, -46.63
    radius_m = 5000.0  # 5 km

    # Busca na Quadtree com poda espacial
    quad_res, metrics = qt.query_radius(center_lat, center_lon, radius_m)
    quad_ids = {inc.id for inc in quad_res}

    # Busca linear de referência O(n)
    linear_ids = {
        inc.id for inc in incidentes
        if haversine_meters(center_lat, center_lon, inc.latitude, inc.longitude) <= radius_m
    }

    # Ambas as buscas devem retornar EXATAMENTE o mesmo conjunto de incidentes
    assert quad_ids == linear_ids
    # A telemetria deve registrar nós visitados e cálculos de distância
    assert metrics["nodes_visited"] > 0
    assert metrics["distance_calculations"] <= len(incidentes)


def test_quadtree_remove_and_merge():
    boundary = BoundingBox(min_lat=-23.60, max_lat=-23.50, min_lon=-46.70, max_lon=-46.60)
    qt = Quadtree(boundary=boundary, capacity=4, max_depth=10)

    # Insere 5 pontos para forçar a divisão
    pontos = [
        _criar_incidente("p1", -23.52, -46.62),
        _criar_incidente("p2", -23.58, -46.68),
        _criar_incidente("p3", -23.52, -46.68),
        _criar_incidente("p4", -23.58, -46.62),
        _criar_incidente("p5", -23.55, -46.65),
    ]
    for p in pontos:
        qt.insert(p)

    assert qt.root.is_divided is True

    # Remove 1 ponto: agora restam 4 pontos no total dos 4 filhos.
    # Como 4 <= capacity (4), o nó raiz DEVE fazer merge/colapso dos 4 filhos!
    removido = qt.remove("p5", -23.55, -46.65)
    assert removido is True
    assert len(qt) == 4
    assert qt.root.is_divided is False
    assert len(qt.root.points) == 4


def test_quadtree_get_all_quadrants_for_visualization():
    boundary = BoundingBox(min_lat=-23.60, max_lat=-23.50, min_lon=-46.70, max_lon=-46.60)
    qt = Quadtree(boundary=boundary, capacity=4, max_depth=10)

    for i in range(5):
        qt.insert(_criar_incidente(f"v-{i}", -23.55 + (i * 0.01), -46.65 + (i * 0.01)))

    quadrantes = qt.get_all_quadrants()
    # Ao subdividir, teremos o nó pai + 4 filhos = ao menos 5 quadrantes delimitados
    assert len(quadrantes) >= 5
    for q in quadrantes:
        assert "min_lat" in q and "max_lat" in q
        assert "min_lon" in q and "max_lon" in q
        assert "depth" in q

