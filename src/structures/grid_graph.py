"""Grafo em grade 2D (Grid Graph) com clusterização de Zonas Vermelhas via BFS."""

from typing import Any, Dict, List, Optional, Set, Tuple
from src.core.models import Incidente, BoundingBox


class GridGraph:
    """
    Grafo em grade espacial 2D particionando uma região em células contíguas.
    Permite agregação de risco em tempo O(1) e detecção de componentes conectados
    de alta periculosidade ('Zonas Vermelhas') via Busca em Largura (BFS).
    """

    def __init__(self, boundary: BoundingBox, rows: int = 30, cols: int = 30):
        self.boundary = boundary
        self.rows = rows
        self.cols = cols

        self.row_height = (boundary.max_lat - boundary.min_lat) / rows
        self.col_width = (boundary.max_lon - boundary.min_lon) / cols

        # Matrizes bidimensionais representando os vértices da grade
        self._scores = [[0 for _ in range(cols)] for _ in range(rows)]
        self._incident_counts = [[0 for _ in range(cols)] for _ in range(rows)]

    def coord_to_cell(self, lat: float, lon: float) -> Optional[Tuple[int, int]]:
        """Mapeia uma coordenada GPS em um par de índices de célula (linha, coluna) em tempo O(1)."""
        if not self.boundary.contains(lat, lon):
            return None

        r = int((lat - self.boundary.min_lat) / self.row_height)
        c = int((lon - self.boundary.min_lon) / self.col_width)

        # Ajuste de borda no extremo superior/direito
        r = min(self.rows - 1, max(0, r))
        c = min(self.cols - 1, max(0, c))
        return (r, c)

    def get_cell_box(self, r: int, c: int) -> BoundingBox:
        """Calcula os limites geográficos retangulares de uma célula específica."""
        min_lat = self.boundary.min_lat + r * self.row_height
        max_lat = min_lat + self.row_height
        min_lon = self.boundary.min_lon + c * self.col_width
        max_lon = min_lon + self.col_width
        return BoundingBox(min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon)

    def get_cell_score(self, r: int, c: int) -> int:
        """Retorna a pontuação de risco acumulada na célula."""
        return self._scores[r][c]

    def add_incident(self, incidente: Incidente) -> None:
        """Acumula o peso da gravidade do incidente na célula correspondente."""
        cell = self.coord_to_cell(incidente.latitude, incidente.longitude)
        if cell is not None:
            r, c = cell
            self._scores[r][c] += incidente.tipo.gravidade_peso
            self._incident_counts[r][c] += 1

    def remove_incident(self, incidente: Incidente) -> None:
        """Deduz o peso do incidente da célula após expiração ou exclusão."""
        cell = self.coord_to_cell(incidente.latitude, incidente.longitude)
        if cell is not None:
            r, c = cell
            self._scores[r][c] = max(0, self._scores[r][c] - incidente.tipo.gravidade_peso)
            self._incident_counts[r][c] = max(0, self._incident_counts[r][c] - 1)

    def find_red_zones_bfs(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """
        Executa Busca em Largura (BFS) sobre células com pontuação >= threshold
        para identificar Componentes Conectados (Zonas Vermelhas contínuas).
        Utiliza vizinhança de 8 direções (ortogonal e diagonal).
        """
        visited: Set[Tuple[int, int]] = set()
        red_zones: List[Dict[str, Any]] = []

        # Vetores de deslocamento para 8 direções adjacentes
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]

        for r in range(self.rows):
            for c in range(self.cols):
                if self._scores[r][c] >= threshold and (r, c) not in visited:
                    # Inicia uma nova busca BFS para este componente conexo
                    queue: List[Tuple[int, int]] = [(r, c)]
                    visited.add((r, c))

                    cluster_cells: List[Tuple[int, int]] = []
                    cluster_score = 0
                    cluster_incidents = 0

                    min_lat = float("inf")
                    max_lat = float("-inf")
                    min_lon = float("inf")
                    max_lon = float("-inf")

                    head = 0
                    while head < len(queue):
                        curr_r, curr_c = queue[head]
                        head += 1

                        cluster_cells.append((curr_r, curr_c))
                        cluster_score += self._scores[curr_r][curr_c]
                        cluster_incidents += self._incident_counts[curr_r][curr_c]

                        cell_box = self.get_cell_box(curr_r, curr_c)
                        min_lat = min(min_lat, cell_box.min_lat)
                        max_lat = max(max_lat, cell_box.max_lat)
                        min_lon = min(min_lon, cell_box.min_lon)
                        max_lon = max(max_lon, cell_box.max_lon)

                        for dr, dc in directions:
                            nr, nc = curr_r + dr, curr_c + dc
                            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                                if self._scores[nr][nc] >= threshold and (nr, nc) not in visited:
                                    visited.add((nr, nc))
                                    queue.append((nr, nc))

                    red_zones.append({
                        "cells": cluster_cells,
                        "bounding_box": BoundingBox(min_lat=min_lat, max_lat=max_lat, min_lon=min_lon, max_lon=max_lon),
                        "total_score": cluster_score,
                        "incident_count": cluster_incidents,
                    })

        return red_zones

    def get_active_cells(self) -> List[Dict[str, Any]]:
        """Retorna todas as células que possuem pelo menos 1 incidente registrado."""
        active: List[Dict[str, Any]] = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self._scores[r][c] > 0:
                    box = self.get_cell_box(r, c)
                    active.append({
                        "row": r,
                        "col": c,
                        "score": self._scores[r][c],
                        "incident_count": self._incident_counts[r][c],
                        "min_lat": box.min_lat,
                        "max_lat": box.max_lat,
                        "min_lon": box.min_lon,
                        "max_lon": box.max_lon,
                    })
        return active
