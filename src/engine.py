"""Fachada orquestradora (AlertEngine) integrando as 4 estruturas de dados e a persistência."""

import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from src.core.models import Incidente, TipoIncidente, BoundingBox
from src.core.geo import haversine_meters
from src.structures.hash_table import HashTable
from src.structures.min_heap import IndexedMinHeap
from src.structures.quadtree import Quadtree
from src.structures.grid_graph import GridGraph
from src.storage.database import DatabaseStorage
from src.storage.seed import generate_realistic_incidents

# Limites geográficos da BoundingBox raiz de São Paulo
SP_BOUNDING_BOX = BoundingBox(
    min_lat=-23.70,
    max_lat=-23.45,
    min_lon=-46.80,
    max_lon=-46.45,
)


class AlertEngine:
    """
    Controlador central em memória que mantém 100% sincronizadas as 4 estruturas de dados:
    1. Quadtree (Busca espacial por raio O(log n))
    2. IndexedMinHeap (Expiração dinâmica e prioridades O(log n))
    3. HashTable (Acesso direto por chave O(1) e tratamento de colisões com Tombstones)
    4. GridGraph (Detecção de Zonas Vermelhas via BFS 8-direcional)
    """

    def __init__(self, db_path: str = "mapa_alertas.db", auto_seed_count: int = 150):
        self.boundary = SP_BOUNDING_BOX
        self.storage = DatabaseStorage(db_path=db_path)

        # Relógio virtual do sistema para simulações cronológicas (Time Travel)
        self.current_time = datetime(2026, 11, 5, 22, 0, tzinfo=timezone.utc)

        # Inicialização das 4 estruturas de dados avançadas
        self.quadtree = Quadtree(boundary=self.boundary, capacity=4, max_depth=10)
        self.min_heap = IndexedMinHeap()
        self.hash_table = HashTable(initial_capacity=101)
        self.grid_graph = GridGraph(boundary=self.boundary, rows=30, cols=30)

        # Reidratação a partir do SQLite ou geração de seed inicial
        self._rehydrate_or_seed(auto_seed_count)

    def __len__(self) -> int:
        return len(self.hash_table)

    def _rehydrate_or_seed(self, seed_count: int) -> None:
        """Carrega incidentes ativos do banco de dados ou popula com o gerador de São Paulo."""
        ativos_db = self.storage.load_all_active(self.current_time)

        if not ativos_db and seed_count > 0:
            incidentes_seed = generate_realistic_incidents(seed_count, base_time=self.current_time)
            for inc in incidentes_seed:
                self.storage.save_incident(inc)
            ativos_db = incidentes_seed

        for inc in ativos_db:
            if self.boundary.contains(inc.latitude, inc.longitude):
                self.hash_table.put(inc.id, inc)
                self.min_heap.push(inc)
                self.quadtree.insert(inc)
                self.grid_graph.add_incident(inc)

    def report_incident(
        self,
        tipo: TipoIncidente,
        latitude: float,
        longitude: float,
        titulo: Optional[str] = None,
        descricao: Optional[str] = None,
        usuario_id: str = "anonimo",
    ) -> Incidente:
        """Registra um novo incidente e atualiza atomicamente todas as estruturas."""
        if not self.boundary.contains(latitude, longitude):
            raise ValueError(f"As coordenadas ({latitude}, {longitude}) estão fora da região de São Paulo.")

        inc_id = f"inc-{uuid.uuid4().hex[:8]}"
        created_at = self.current_time
        expires_at = created_at + timedelta(hours=tipo.ttl_base_horas)

        incidente = Incidente(
            id=inc_id,
            tipo=tipo,
            latitude=round(latitude, 6),
            longitude=round(longitude, 6),
            created_at=created_at,
            expires_at=expires_at,
            upvotes=0,
            usuario_id=usuario_id,
            titulo=titulo or f"{tipo.value.replace('_', ' ').title()}",
            descricao=descricao or "Relato colaborativo inserido pelo usuário.",
        )

        # Inserção atômica nas 4 estruturas
        self.hash_table.put(incidente.id, incidente)
        self.min_heap.push(incidente)
        self.quadtree.insert(incidente)
        self.grid_graph.add_incident(incidente)
        self.storage.save_incident(incidente)

        return incidente

    def upvote_incident(self, incidente_id: str, bonus_hours: float = 2.0) -> Incidente:
        """
        Confirma um alerta urbano (+1 upvote) e estende seu tempo de vida útil (TTL).
        Atualiza a posição do nó na Min-Heap em tempo O(log n).
        """
        incidente: Optional[Incidente] = self.hash_table.get(incidente_id)
        if incidente is None:
            raise KeyError(f"Incidente '{incidente_id}' não encontrado.")

        incidente.upvotes += 1
        # Garante que o bônus seja somado ao maior valor entre a expiração atual e o relógio
        base_exp = max(self.current_time, incidente.expires_at)
        novo_expires_at = base_exp + timedelta(hours=bonus_hours)
        incidente.expires_at = novo_expires_at

        # Atualiza a heap utilizando o mapeamento O(1) da HashTable interna
        self.min_heap.update_expiration(incidente_id, novo_expires_at)
        self.storage.update_incident_upvotes_and_expiration(incidente_id, incidente.upvotes, novo_expires_at)

        return incidente

    def advance_time(self, hours: float) -> int:
        """
        Avança o relógio virtual em X horas, aciona o decaimento (Decay) e purga
        automaticamente todos os alertas expirados da Quadtree, Heap, Hash Table e Grafo.
        """
        if hours <= 0:
            return 0

        self.current_time += timedelta(hours=hours)
        # Remove da Min-Heap todos os itens cujo expires_at <= current_time
        expirados = self.min_heap.pop_expired(self.current_time)

        for inc in expirados:
            # Purgar da HashTable
            if inc.id in self.hash_table:
                self.hash_table.remove(inc.id)

            # Purgar da Quadtree (com colapso / merge automático)
            self.quadtree.remove(inc.id, inc.latitude, inc.longitude)

            # Purgar do GridGraph
            self.grid_graph.remove_incident(inc)

            # Purgar do banco de dados
            self.storage.delete_incident(inc.id)

        return len(expirados)

    def search_radius(self, lat: float, lon: float, radius_meters: float) -> Dict[str, Any]:
        """
        Executa a busca espacial na Quadtree e simultaneamente em força bruta O(n)
        para gerar a telemetria comparativa de performance em milissegundos e contadores.
        """
        # 1. Busca na Quadtree com poda espacial
        t0_quad = time.perf_counter()
        quad_results, metrics = self.quadtree.query_radius(lat, lon, radius_meters)
        t_quad_ms = (time.perf_counter() - t0_quad) * 1000.0

        # 2. Busca linear O(n) para aferição comparativa de desempenho
        t0_lin = time.perf_counter()
        linear_count = 0
        todos_ativos = list(self.hash_table.values())
        for inc in todos_ativos:
            linear_count += 1
            _ = haversine_meters(lat, lon, inc.latitude, inc.longitude)
        t_lin_ms = (time.perf_counter() - t0_lin) * 1000.0

        # Cálculo do percentual de podas (operações economizadas)
        total_pontos = len(todos_ativos)
        calcs_economizados = max(0, total_pontos - metrics["distance_calculations"])
        pruning_ratio = (calcs_economizados / total_pontos * 100.0) if total_pontos > 0 else 0.0

        # Serialização com níveis visuais de alerta e distância calculada
        incidentes_formatados = []
        for inc in quad_results:
            nivel = inc.calcular_nivel_alerta(self.current_time)
            dist_m = haversine_meters(lat, lon, inc.latitude, inc.longitude)
            incidentes_formatados.append({
                "id": inc.id,
                "tipo": inc.tipo.value,
                "latitude": inc.latitude,
                "longitude": inc.longitude,
                "distancia_metros": round(dist_m, 1),
                "created_at": inc.created_at.isoformat(),
                "expires_at": inc.expires_at.isoformat(),
                "upvotes": inc.upvotes,
                "nivel_alerta": nivel,
                "titulo": inc.titulo,
                "descricao": inc.descricao,
            })

        # Ordena os incidentes por proximidade do ponto central clicado
        incidentes_formatados.sort(key=lambda x: x["distancia_metros"])

        return {
            "incidents": incidentes_formatados,
            "telemetry": {
                "quadtree_nodes_visited": metrics["nodes_visited"],
                "quadtree_calcs": metrics["distance_calculations"],
                "linear_calcs": linear_count,
                "quadtree_ms": round(t_quad_ms, 3),
                "linear_ms": round(t_lin_ms, 3),
                "pruning_ratio_percent": round(pruning_ratio, 1),
                "speedup_factor": round((t_lin_ms / t_quad_ms), 1) if t_quad_ms > 0.001 else 1.0,
            },
        }

    def inject_bulk(self, count: int) -> int:
        """Injeta múltiplos incidentes simulados para teste de estresse ao vivo."""
        seed_incidents = generate_realistic_incidents(
            count,
            base_time=self.current_time,
            seed=int(time.time()),
        )
        for inc in seed_incidents:
            if self.boundary.contains(inc.latitude, inc.longitude):
                self.hash_table.put(inc.id, inc)
                self.min_heap.push(inc)
                self.quadtree.insert(inc)
                self.grid_graph.add_incident(inc)
                self.storage.save_incident(inc)
        return len(seed_incidents)

    def reset_simulation(self, seed_count: int = 150) -> None:
        """Reinicia a simulação limpando os dados e gerando novo conjunto controlado."""
        self.storage.clear_all()
        self.quadtree = Quadtree(boundary=self.boundary, capacity=4, max_depth=10)
        self.min_heap = IndexedMinHeap()
        self.hash_table = HashTable(initial_capacity=101)
        self.grid_graph = GridGraph(boundary=self.boundary, rows=30, cols=30)
        self.current_time = datetime(2026, 11, 5, 22, 0, tzinfo=timezone.utc)
        self._rehydrate_or_seed(seed_count)

    def get_system_state(self) -> Dict[str, Any]:
        """Retorna o estado global consolidado para consumo da API e renderização no frontend."""
        all_incidents = []
        for inc in self.hash_table.values():
            all_incidents.append({
                "id": inc.id,
                "tipo": inc.tipo.value,
                "latitude": inc.latitude,
                "longitude": inc.longitude,
                "created_at": inc.created_at.isoformat(),
                "expires_at": inc.expires_at.isoformat(),
                "upvotes": inc.upvotes,
                "nivel_alerta": inc.calcular_nivel_alerta(self.current_time),
                "titulo": inc.titulo,
                "descricao": inc.descricao,
            })

        # Zonas Vermelhas agrupadas pelo BFS do Grafo
        red_zones = self.grid_graph.find_red_zones_bfs(threshold=10)
        formatted_red_zones = []
        for rz in red_zones:
            box = rz["bounding_box"]
            formatted_red_zones.append({
                "cells_count": len(rz["cells"]),
                "total_score": rz["total_score"],
                "incident_count": rz["incident_count"],
                "min_lat": box.min_lat,
                "max_lat": box.max_lat,
                "min_lon": box.min_lon,
                "max_lon": box.max_lon,
            })

        next_expire = self.min_heap.peek()

        return {
            "current_time": self.current_time.isoformat(),
            "total_incidents": len(self.hash_table),
            "incidents": all_incidents,
            "quadtree": {
                "total_points": len(self.quadtree),
                "quadrants": self.quadtree.get_all_quadrants(),
            },
            "min_heap": {
                "size": len(self.min_heap),
                "next_to_expire": {
                    "id": next_expire.id,
                    "expires_at": next_expire.expires_at.isoformat(),
                    "tipo": next_expire.tipo.value,
                    "titulo": next_expire.titulo,
                } if next_expire else None,
            },
            "hash_table": {
                "capacity": self.hash_table.capacity,
                "size": self.hash_table.size,
                "tombstones": self.hash_table.tombstones,
                "load_factor": round(self.hash_table.load_factor, 3),
                "rehash_count": self.hash_table.rehash_count,
                "total_collisions": self.hash_table.total_collisions,
            },
            "grid_graph": {
                "active_cells": self.grid_graph.get_active_cells(),
                "red_zones": formatted_red_zones,
                "red_zones_count": len(formatted_red_zones),
            },
        }

