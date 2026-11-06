"""Quadtree espacial 2D com suporte a Range Query e colapso automático (merge) de quadrantes."""

from typing import Any, Dict, List, Optional, Tuple
from src.core.models import Incidente, BoundingBox
from src.core.geo import haversine_meters, bounding_box_from_radius


class QuadtreeNode:
    """Nó individual da Quadtree delimitando uma BoundingBox 2D."""

    def __init__(self, boundary: BoundingBox, capacity: int = 4, depth: int = 0, max_depth: int = 10):
        self.boundary = boundary
        self.capacity = capacity
        self.depth = depth
        self.max_depth = max_depth

        self.points: List[Incidente] = []
        self.is_divided = False

        self.northwest: Optional["QuadtreeNode"] = None
        self.northeast: Optional["QuadtreeNode"] = None
        self.southwest: Optional["QuadtreeNode"] = None
        self.southeast: Optional["QuadtreeNode"] = None

    def subdivide(self) -> None:
        """Divide o nó atual em 4 quadrantes filhos (NW, NE, SW, SE) e redistribui seus pontos."""
        mid_lat = self.boundary.center_lat
        mid_lon = self.boundary.center_lon
        next_depth = self.depth + 1

        # Quadrante Noroeste (NW): latitudes superiores, longitudes esquerdas
        nw_box = BoundingBox(min_lat=mid_lat, max_lat=self.boundary.max_lat, min_lon=self.boundary.min_lon, max_lon=mid_lon)
        self.northwest = QuadtreeNode(nw_box, self.capacity, next_depth, self.max_depth)

        # Quadrante Nordeste (NE): latitudes superiores, longitudes direitas
        ne_box = BoundingBox(min_lat=mid_lat, max_lat=self.boundary.max_lat, min_lon=mid_lon, max_lon=self.boundary.max_lon)
        self.northeast = QuadtreeNode(ne_box, self.capacity, next_depth, self.max_depth)

        # Quadrante Sudoeste (SW): latitudes inferiores, longitudes esquerdas
        sw_box = BoundingBox(min_lat=self.boundary.min_lat, max_lat=mid_lat, min_lon=self.boundary.min_lon, max_lon=mid_lon)
        self.southwest = QuadtreeNode(sw_box, self.capacity, next_depth, self.max_depth)

        # Quadrante Sudeste (SE): latitudes inferiores, longitudes direitas
        se_box = BoundingBox(min_lat=self.boundary.min_lat, max_lat=mid_lat, min_lon=mid_lon, max_lon=self.boundary.max_lon)
        self.southeast = QuadtreeNode(se_box, self.capacity, next_depth, self.max_depth)

        self.is_divided = True

        # Redistribui os pontos existentes entre os novos quadrantes filhos
        for ponto in self.points:
            self._insert_into_children(ponto)
        self.points.clear()

    def _insert_into_children(self, incidente: Incidente) -> bool:
        """Encaminha a inserção para o quadrante filho correspondente."""
        return (
            (self.northwest is not None and self.northwest.insert(incidente))
            or (self.northeast is not None and self.northeast.insert(incidente))
            or (self.southwest is not None and self.southwest.insert(incidente))
            or (self.southeast is not None and self.southeast.insert(incidente))
        )

    def insert(self, incidente: Incidente) -> bool:
        """Insere um incidente no nó ou propaga para um filho."""
        if not self.boundary.contains(incidente.latitude, incidente.longitude):
            return False

        if not self.is_divided:
            if len(self.points) < self.capacity or self.depth >= self.max_depth:
                self.points.append(incidente)
                return True
            self.subdivide()

        return self._insert_into_children(incidente)

    def query(
        self,
        search_box: BoundingBox,
        center_lat: float,
        center_lon: float,
        radius_meters: float,
        results: List[Incidente],
        metrics: Dict[str, int],
    ) -> None:
        """
        Executa a busca por raio com poda espacial:
        1. Se a bounding box deste nó não intersecta a caixa de busca, poda o ramo inteiro.
        2. Se intersecta e for folha, valida a distância geodésica exata via Haversine.
        3. Se for nó interno, visita recursivamente os 4 quadrantes.
        """
        metrics["nodes_visited"] += 1

        if not self.boundary.intersects(search_box):
            return

        if not self.is_divided:
            for ponto in self.points:
                metrics["distance_calculations"] += 1
                dist = haversine_meters(center_lat, center_lon, ponto.latitude, ponto.longitude)
                if dist <= radius_meters:
                    results.append(ponto)
            return

        # Visita recursiva aos 4 filhos
        if self.northwest:
            self.northwest.query(search_box, center_lat, center_lon, radius_meters, results, metrics)
        if self.northeast:
            self.northeast.query(search_box, center_lat, center_lon, radius_meters, results, metrics)
        if self.southwest:
            self.southwest.query(search_box, center_lat, center_lon, radius_meters, results, metrics)
        if self.southeast:
            self.southeast.query(search_box, center_lat, center_lon, radius_meters, results, metrics)

    def remove(self, incidente_id: str, lat: float, lon: float) -> bool:
        """Remove o incidente por id e coordenada GPS, colapsando quadrantes ociosos no retorno."""
        if not self.boundary.contains(lat, lon):
            return False

        if not self.is_divided:
            for idx, ponto in enumerate(self.points):
                if ponto.id == incidente_id:
                    self.points.pop(idx)
                    return True
            return False

        removido = (
            (self.northwest is not None and self.northwest.remove(incidente_id, lat, lon))
            or (self.northeast is not None and self.northeast.remove(incidente_id, lat, lon))
            or (self.southwest is not None and self.southwest.remove(incidente_id, lat, lon))
            or (self.southeast is not None and self.southeast.remove(incidente_id, lat, lon))
        )

        if removido:
            self._try_merge()

        return removido

    def _try_merge(self) -> None:
        """
        Colapsa os 4 filhos de volta para o nó atual se todos forem folhas
        e a soma total de pontos for menor ou igual à capacidade do nó pai.
        """
        if not self.is_divided:
            return

        nw, ne, sw, se = self.northwest, self.northeast, self.southwest, self.southeast
        if (
            nw is not None and not nw.is_divided
            and ne is not None and not ne.is_divided
            and sw is not None and not sw.is_divided
            and se is not None and not se.is_divided
        ):
            total_pontos = len(nw.points) + len(ne.points) + len(sw.points) + len(se.points)
            if total_pontos <= self.capacity:
                self.points = nw.points + ne.points + sw.points + se.points
                self.northwest = None
                self.northeast = None
                self.southwest = None
                self.southeast = None
                self.is_divided = False

    def collect_quadrants(self, quadrants_list: List[Dict[str, Any]]) -> None:
        """Coleta as coordenadas delimitadoras de cada nó da árvore para renderização no mapa."""
        quadrants_list.append({
            "min_lat": self.boundary.min_lat,
            "max_lat": self.boundary.max_lat,
            "min_lon": self.boundary.min_lon,
            "max_lon": self.boundary.max_lon,
            "depth": self.depth,
            "is_divided": self.is_divided,
            "points_count": len(self.points) if not self.is_divided else 0,
        })

        if self.is_divided:
            if self.northwest:
                self.northwest.collect_quadrants(quadrants_list)
            if self.northeast:
                self.northeast.collect_quadrants(quadrants_list)
            if self.southwest:
                self.southwest.collect_quadrants(quadrants_list)
            if self.southeast:
                self.southeast.collect_quadrants(quadrants_list)


class Quadtree:
    """Estrutura hierárquica espacial para indexação e consultas em tempo logarítmico O(log n)."""

    def __init__(self, boundary: BoundingBox, capacity: int = 4, max_depth: int = 10):
        self.boundary = boundary
        self.capacity = capacity
        self.max_depth = max_depth
        self.root = QuadtreeNode(boundary, capacity, depth=0, max_depth=max_depth)
        self._total_points = 0

    def __len__(self) -> int:
        return self._total_points

    def insert(self, incidente: Incidente) -> bool:
        """Insere um novo incidente na árvore espacial."""
        sucesso = self.root.insert(incidente)
        if sucesso:
            self._total_points += 1
        return sucesso

    def query_radius(self, center_lat: float, center_lon: float, radius_meters: float) -> Tuple[List[Incidente], Dict[str, int]]:
        """
        Retorna todos os incidentes dentro do raio esférico especificado
        juntamente com as métricas de nós visitados e cálculos realizados.
        """
        search_box = bounding_box_from_radius(center_lat, center_lon, radius_meters)
        results: List[Incidente] = []
        metrics: Dict[str, int] = {
            "nodes_visited": 0,
            "distance_calculations": 0,
        }

        self.root.query(search_box, center_lat, center_lon, radius_meters, results, metrics)
        return results, metrics

    def remove(self, incidente_id: str, lat: float, lon: float) -> bool:
        """Remove o incidente por coordenada GPS e ID."""
        removido = self.root.remove(incidente_id, lat, lon)
        if removido:
            self._total_points -= 1
        return removido

    def get_all_quadrants(self) -> List[Dict[str, Any]]:
        """Exporta os limites de todos os quadrantes para plotagem gráfica."""
        quadrants: List[Dict[str, Any]] = []
        self.root.collect_quadrants(quadrants)
        return quadrants
