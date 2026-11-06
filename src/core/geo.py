"""Cálculos geodésicos e transformações espaciais baseadas na Terra esférica."""

import math
from src.core.models import BoundingBox

# Raio médio volumétrico da Terra em metros (WGS 84 aproximado)
RAIO_TERRA_METROS = 6371000.0


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula a distância ortodrômica (grande círculo) em metros entre dois pontos geográficos
    utilizando a fórmula de Haversine.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Evita erros de precisão de ponto flutuante que possam gerar a > 1.0
    c = 2.0 * math.atan2(math.sqrt(min(1.0, a)), math.sqrt(max(0.0, 1.0 - a)))
    return RAIO_TERRA_METROS * c


def bounding_box_from_radius(center_lat: float, center_lon: float, radius_meters: float) -> BoundingBox:
    """
    Constrói a BoundingBox retangular que circunscreve um círculo de busca de raio R metros.
    Utilizada para podar os ramos da Quadtree antes da validação exata por Haversine.
    """
    # 1 grau de latitude equivale a aproximadamente 111.32 km em qualquer ponto da Terra
    delta_lat = radius_meters / 111320.0

    # 1 grau de longitude varia conforme o cosseno da latitude média
    cos_lat = math.cos(math.radians(center_lat))
    # Proteção para latitudes extremas nos polos para evitar divisão por zero
    if abs(cos_lat) < 1e-6:
        delta_lon = 180.0
    else:
        delta_lon = radius_meters / (111320.0 * cos_lat)

    return BoundingBox(
        min_lat=center_lat - delta_lat,
        max_lat=center_lat + delta_lat,
        min_lon=center_lon - delta_lon,
        max_lon=center_lon + delta_lon,
    )

