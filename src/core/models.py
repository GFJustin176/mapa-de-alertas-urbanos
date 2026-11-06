"""Modelos de dados fundamentais do domínio de alertas urbanos."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TipoIncidente(str, Enum):
    """Tipos de incidentes suportados com seus respectivos pesos e TTL padrão."""
    ASSALTO = "ASSALTO"
    FURTO = "FURTO"
    VIA_PERIGOSA = "VIA_PERIGOSA"

    @property
    def gravidade_peso(self) -> int:
        """Retorna o peso do incidente para agregação nas células do Grid Graph."""
        pesos = {
            TipoIncidente.ASSALTO: 5,
            TipoIncidente.FURTO: 3,
            TipoIncidente.VIA_PERIGOSA: 2,
        }
        return pesos[self]

    @property
    def ttl_base_horas(self) -> int:
        """Tempo de vida base em horas antes de expirar sem upvotes."""
        ttls = {
            TipoIncidente.ASSALTO: 48,
            TipoIncidente.FURTO: 24,
            TipoIncidente.VIA_PERIGOSA: 36,
        }
        return ttls[self]


@dataclass(frozen=True)
class Usuario:
    """Representa um usuário do sistema colaborativo."""
    id: str
    nome: str
    reputacao: float = 1.0


@dataclass
class Incidente:
    """Entidade central de um relato urbano geolocalizado."""
    id: str
    tipo: TipoIncidente
    latitude: float
    longitude: float
    created_at: datetime
    expires_at: datetime
    upvotes: int = 0
    usuario_id: str = "anonimo"
    titulo: Optional[str] = None
    descricao: Optional[str] = None

    def calcular_nivel_alerta(self, tempo_atual: datetime) -> str:
        """
        Determina o estágio de decaimento visual com base na vida útil restante.
        - CRITICO: 50% a 100% do TTL original restante.
        - MODERADO: 20% a 50% do TTL restante.
        - BAIXO: Menos de 20% do TTL restante.
        - EXPIRADO: Timestamp de expiração já ultrapassado.
        """
        if tempo_atual >= self.expires_at:
            return "EXPIRADO"

        tempo_total = (self.expires_at - self.created_at).total_seconds()
        if tempo_total <= 0:
            return "EXPIRADO"

        tempo_restante = (self.expires_at - tempo_atual).total_seconds()
        percentual_restante = tempo_restante / tempo_total

        if percentual_restante >= 0.50:
            return "CRITICO"
        if percentual_restante >= 0.20:
            return "MODERADO"
        return "BAIXO"


@dataclass(frozen=True)
class BoundingBox:
    """Retângulo delimitador 2D no plano de coordenadas geográficas (Latitude e Longitude)."""
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

    def __post_init__(self):
        if self.min_lat > self.max_lat:
            raise ValueError(f"min_lat ({self.min_lat}) deve ser <= max_lat ({self.max_lat})")
        if self.min_lon > self.max_lon:
            raise ValueError(f"min_lon ({self.min_lon}) deve ser <= max_lon ({self.max_lon})")

    def contains(self, lat: float, lon: float) -> bool:
        """Verifica se uma coordenada GPS está dentro dos limites deste retângulo."""
        return (self.min_lat <= lat <= self.max_lat) and (self.min_lon <= lon <= self.max_lon)

    def intersects(self, other: "BoundingBox") -> bool:
        """Verifica se há sobreposição espacial com outro retângulo delimitador."""
        # Não há interseção se um estiver totalmente à esquerda, direita, acima ou abaixo do outro
        if self.max_lat < other.min_lat or self.min_lat > other.max_lat:
            return False
        if self.max_lon < other.min_lon or self.min_lon > other.max_lon:
            return False
        return True

    @property
    def center_lat(self) -> float:
        """Latitude central da caixa delimitadora."""
        return (self.min_lat + self.max_lat) / 2.0

    @property
    def center_lon(self) -> float:
        """Longitude central da caixa delimitadora."""
        return (self.min_lon + self.max_lon) / 2.0
