"""Testes unitários para o GridGraph e clusterização de Zonas Vermelhas via BFS."""

import pytest
from datetime import datetime, timezone, timedelta
from src.core.models import Incidente, TipoIncidente, BoundingBox
from src.structures.grid_graph import GridGraph


def _criar_incidente(id_inc: str, lat: float, lon: float, tipo: TipoIncidente) -> Incidente:
    now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    return Incidente(
        id=id_inc,
        tipo=tipo,
        latitude=lat,
        longitude=lon,
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )


def test_grid_graph_coord_to_cell_mapping():
    # Bounding box cobrindo São Paulo: lat: [-23.70, -23.45], lon: [-46.80, -46.45]
    boundary = BoundingBox(min_lat=-23.70, max_lat=-23.45, min_lon=-46.80, max_lon=-46.45)
    graph = GridGraph(boundary=boundary, rows=30, cols=30)

    # Canto inferior esquerdo (SW)
    cell_sw = graph.coord_to_cell(-23.70, -46.80)
    assert cell_sw == (0, 0)

    # Canto superior direito (NE)
    cell_ne = graph.coord_to_cell(-23.45, -46.45)
    assert cell_ne == (29, 29)

    # Centro
    cell_center = graph.coord_to_cell(boundary.center_lat, boundary.center_lon)
    assert 14 <= cell_center[0] <= 15
    assert 14 <= cell_center[1] <= 15

    # Coordenada fora do mapa
    assert graph.coord_to_cell(-22.0, -40.0) is None


def test_grid_graph_add_and_remove_incident_score():
    boundary = BoundingBox(min_lat=-23.70, max_lat=-23.45, min_lon=-46.80, max_lon=-46.45)
    graph = GridGraph(boundary=boundary, rows=30, cols=30)

    # Assalto = 5 pontos
    inc1 = _criar_incidente("i1", -23.55, -46.63, TipoIncidente.ASSALTO)
    graph.add_incident(inc1)

    cell = graph.coord_to_cell(-23.55, -46.63)
    assert graph.get_cell_score(cell[0], cell[1]) == 5

    # Furto = 3 pontos na mesma célula -> Total 8 pontos
    inc2 = _criar_incidente("i2", -23.55, -46.63, TipoIncidente.FURTO)
    graph.add_incident(inc2)
    assert graph.get_cell_score(cell[0], cell[1]) == 8

    # Remover o assalto -> Volta para 3 pontos
    graph.remove_incident(inc1)
    assert graph.get_cell_score(cell[0], cell[1]) == 3


def test_grid_graph_find_red_zones_bfs_connected_components():
    boundary = BoundingBox(min_lat=-23.70, max_lat=-23.45, min_lon=-46.80, max_lon=-46.45)
    graph = GridGraph(boundary=boundary, rows=30, cols=30)

    # Ponto A: Centro da Sé (Célula r, c)
    # 2 assaltos de 5 pontos = 10 pontos (atinge threshold)
    lat_a, lon_a = -23.550, -46.633
    cell_a = graph.coord_to_cell(lat_a, lon_a)
    graph.add_incident(_criar_incidente("a1", lat_a, lon_a, TipoIncidente.ASSALTO))
    graph.add_incident(_criar_incidente("a2", lat_a, lon_a, TipoIncidente.ASSALTO))

    # Ponto B: Célula adjacente vizinha imediata a A
    # Criamos coordenadas na célula ao lado (r, c+1)
    cell_b_box = graph.get_cell_box(cell_a[0], cell_a[1] + 1)
    lat_b, lon_b = cell_b_box.center_lat, cell_b_box.center_lon
    graph.add_incident(_criar_incidente("b1", lat_b, lon_b, TipoIncidente.ASSALTO))
    graph.add_incident(_criar_incidente("b2", lat_b, lon_b, TipoIncidente.ASSALTO))

    # Ponto C: Célula distante isolada (ex: Zona Sul Santo Amaro) com >= 10 pontos
    lat_c, lon_c = -23.650, -46.700
    graph.add_incident(_criar_incidente("c1", lat_c, lon_c, TipoIncidente.ASSALTO))
    graph.add_incident(_criar_incidente("c2", lat_c, lon_c, TipoIncidente.ASSALTO))

    # Ponto D: Célula com apenas 5 pontos (não deve virar Zona Vermelha)
    lat_d, lon_d = -23.580, -46.680
    graph.add_incident(_criar_incidente("d1", lat_d, lon_d, TipoIncidente.ASSALTO))

    # Executa BFS para encontrar componentes conectados com threshold >= 10
    red_zones = graph.find_red_zones_bfs(threshold=10)

    # Deve encontrar exatamente 2 Zonas Vermelhas:
    # 1. Cluster A+B (2 células conectadas)
    # 2. Cluster C (1 célula isolada)
    assert len(red_zones) == 2

    # Verifica o cluster com 2 células
    cluster_duplo = next(rz for rz in red_zones if len(rz["cells"]) == 2)
    assert cluster_duplo["total_score"] == 20
    assert cluster_duplo["incident_count"] == 4

    # Verifica o cluster isolado com 1 célula
    cluster_isolado = next(rz for rz in red_zones if len(rz["cells"]) == 1)
    assert cluster_isolado["total_score"] == 10
    assert cluster_isolado["incident_count"] == 2
