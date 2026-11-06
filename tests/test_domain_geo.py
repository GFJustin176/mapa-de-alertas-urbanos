"""Testes unitários para as entidades de domínio e cálculos geodésicos."""

import pytest
from datetime import datetime, timezone, timedelta
from src.core.models import Incidente, TipoIncidente, Usuario, BoundingBox
from src.core.geo import haversine_meters, bounding_box_from_radius


def test_bounding_box_contains_and_intersects():
    box = BoundingBox(min_lat=-23.60, max_lat=-23.50, min_lon=-46.70, max_lon=-46.60)

    # Ponto interno
    assert box.contains(-23.55, -46.65) is True
    # Ponto na borda
    assert box.contains(-23.60, -46.70) is True
    # Ponto externo
    assert box.contains(-23.40, -46.65) is False

    # Interseção total / parcial
    other_box = BoundingBox(min_lat=-23.55, max_lat=-23.45, min_lon=-46.65, max_lon=-46.55)
    assert box.intersects(other_box) is True

    # Sem interseção
    distant_box = BoundingBox(min_lat=-23.40, max_lat=-23.30, min_lon=-46.50, max_lon=-46.40)
    assert box.intersects(distant_box) is False


def test_haversine_meters_accuracy():
    # Coordenadas reais em São Paulo:
    # Marco Zero da Praça da Sé: (-23.55052, -46.633308)
    # MASP (Avenida Paulista): (-23.561414, -46.655881)
    # Distância em linha reta: aprox. 2.6 km (2550 a 2650 metros)
    dist = haversine_meters(-23.55052, -46.633308, -23.561414, -46.655881)
    assert 2550 <= dist <= 2650


def test_bounding_box_from_radius():
    center_lat, center_lon = -23.55052, -46.633308
    radius_m = 1000.0  # 1 km

    box = bounding_box_from_radius(center_lat, center_lon, radius_m)
    assert box.min_lat < center_lat < box.max_lat
    assert box.min_lon < center_lon < box.max_lon

    # Ponto a 500m ao norte deve estar contido na bounding box
    # 1 grau de latitude é aprox. 111.32 km -> 500m ~= 0.00449 graus
    north_lat = center_lat + 0.004
    assert box.contains(north_lat, center_lon) is True


def test_incidente_decay_levels():
    now = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    created_at = now - timedelta(hours=2)
    # TTL base de 10 horas
    expires_at = created_at + timedelta(hours=10)

    incidente = Incidente(
        id="inc-1",
        tipo=TipoIncidente.ASSALTO,
        latitude=-23.5505,
        longitude=-46.6333,
        created_at=created_at,
        expires_at=expires_at,
        upvotes=0,
        usuario_id="user-1",
    )

    # Restam 8 horas de 10 (80% restante) -> CRITICO (50% a 100%)
    assert incidente.calcular_nivel_alerta(now) == "CRITICO"

    # Restam 3 horas (30% restante) -> MODERADO (20% a 50%)
    later = now + timedelta(hours=5)
    assert incidente.calcular_nivel_alerta(later) == "MODERADO"

    # Resta 1 hora (10% restante) -> BAIXO (< 20%)
    much_later = now + timedelta(hours=7)
    assert incidente.calcular_nivel_alerta(much_later) == "BAIXO"

    # Expirado (0% restante)
    expired_time = now + timedelta(hours=9)
    assert incidente.calcular_nivel_alerta(expired_time) == "EXPIRADO"
