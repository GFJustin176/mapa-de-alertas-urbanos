"""Fila de Prioridade (Min-Heap) indexada para gerenciamento dinâmico de expiração e upvotes."""

from datetime import datetime
from typing import List, Optional
from src.core.models import Incidente
from src.structures.hash_table import HashTable


class IndexedMinHeap:
    """
    Min-Heap binária onde o elemento de menor timestamp de expiração (expires_at)
    reside na raiz (heap[0]).
    Mantém uma HashTable interna (id -> índice) para localizar qualquer nó em O(1),
    permitindo rebaixar ou promover prioridades (Upvotes/Decay) em tempo O(log n).
    """

    def __init__(self):
        # Array contíguo representando a árvore binária completa
        self._heap: List[Incidente] = []
        # Tabela hash interna para mapear o id do incidente ao seu índice na lista
        self._pos_map: HashTable = HashTable(initial_capacity=31)

    def __len__(self) -> int:
        return len(self._heap)

    def contains(self, incidente_id: str) -> bool:
        """Verifica em O(1) se um incidente está presente na heap."""
        return self._pos_map.contains(incidente_id)

    def __contains__(self, incidente_id: str) -> bool:
        return self.contains(incidente_id)

    def get(self, incidente_id: str) -> Optional[Incidente]:
        """Recupera o incidente pelo ID em O(1) consultando a posição na heap."""
        idx = self._pos_map.get(incidente_id)
        if idx is not None and 0 <= idx < len(self._heap):
            return self._heap[idx]
        return None

    def peek(self) -> Optional[Incidente]:
        """Retorna o próximo incidente prestes a expirar sem removê-lo em O(1)."""
        return self._heap[0] if self._heap else None

    def push(self, incidente: Incidente) -> None:
        """Insere um novo incidente na heap em O(log n)."""
        idx = len(self._heap)
        self._heap.append(incidente)
        self._pos_map.put(incidente.id, idx)
        self._sift_up(idx)

    def pop_min(self) -> Incidente:
        """Remove e retorna o incidente com menor tempo de expiração em O(log n)."""
        if not self._heap:
            raise IndexError("A Min-Heap está vazia.")

        min_item = self._heap[0]
        last_item = self._heap.pop()
        self._pos_map.remove(min_item.id)

        if self._heap:
            self._heap[0] = last_item
            self._pos_map.put(last_item.id, 0)
            self._sift_down(0)

        return min_item

    def pop_expired(self, current_time: datetime) -> List[Incidente]:
        """
        Varre e remove em lote todos os incidentes cujo expires_at seja <= current_time.
        Como o menor timestamp está sempre no topo, para imediatamente ao encontrar um item ativo.
        """
        expired: List[Incidente] = []
        while self._heap and self._heap[0].expires_at <= current_time:
            expired.append(self.pop_min())
        return expired

    def update_expiration(self, incidente_id: str, new_expires_at: datetime) -> None:
        """
        Atualiza o tempo de expiração de um incidente (ex: após upvote) e restaura
        a propriedade da Min-Heap em tempo O(log n).
        """
        idx = self._pos_map.get(incidente_id)
        if idx is None:
            raise KeyError(f"Incidente '{incidente_id}' não encontrado na heap.")

        old_expires_at = self._heap[idx].expires_at
        self._heap[idx].expires_at = new_expires_at

        if new_expires_at > old_expires_at:
            # Tempo de vida aumentou: prioridade de expiração diminui (desce na Min-Heap)
            self._sift_down(idx)
        elif new_expires_at < old_expires_at:
            # Tempo de vida diminuiu: prioridade de expiração aumenta (sobe na Min-Heap)
            self._sift_up(idx)

    def remove(self, incidente_id: str) -> Incidente:
        """
        Remove um incidente arbitrário pelo ID em tempo O(log n).
        Substitui o nó pelo último elemento do array e ajusta sua posição.
        """
        idx = self._pos_map.get(incidente_id)
        if idx is None:
            raise KeyError(f"Incidente '{incidente_id}' não encontrado na heap.")

        target = self._heap[idx]
        last_idx = len(self._heap) - 1

        if idx == last_idx:
            self._heap.pop()
            self._pos_map.remove(incidente_id)
            return target

        # Move o último elemento para a posição vaga
        last_item = self._heap.pop()
        self._pos_map.remove(incidente_id)

        self._heap[idx] = last_item
        self._pos_map.put(last_item.id, idx)

        # Ajusta a posição para cima ou para baixo
        parent_idx = (idx - 1) // 2
        if idx > 0 and self._heap[idx].expires_at < self._heap[parent_idx].expires_at:
            self._sift_up(idx)
        else:
            self._sift_down(idx)

        return target

    def _swap(self, i: int, j: int) -> None:
        """Troca dois nós na heap e atualiza os índices correspondentes na HashTable."""
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]
        self._pos_map.put(self._heap[i].id, i)
        self._pos_map.put(self._heap[j].id, j)

    def _sift_up(self, idx: int) -> None:
        """Move o nó na posição idx para cima até restabelecer a ordem da Min-Heap."""
        while idx > 0:
            parent_idx = (idx - 1) // 2
            if self._heap[idx].expires_at < self._heap[parent_idx].expires_at:
                self._swap(idx, parent_idx)
                idx = parent_idx
            else:
                break

    def _sift_down(self, idx: int) -> None:
        """Move o nó na posição idx para baixo comparando com seus dois filhos."""
        heap_len = len(self._heap)
        while True:
            left_child = 2 * idx + 1
            right_child = 2 * idx + 2
            smallest = idx

            if left_child < heap_len and self._heap[left_child].expires_at < self._heap[smallest].expires_at:
                smallest = left_child

            if right_child < heap_len and self._heap[right_child].expires_at < self._heap[smallest].expires_at:
                smallest = right_child

            if smallest != idx:
                self._swap(idx, smallest)
                idx = smallest
            else:
                break
