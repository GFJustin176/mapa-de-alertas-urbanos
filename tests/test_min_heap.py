"""Testes unitários exaustivos para a IndexedMinHeap com suporte a Upvotes e Expiração Dinâmica."""

import pytest
from datetime import datetime, timezone, timedelta
from src.core.models import Incidente, TipoIncidente
from src.structures.min_heap import IndexedMinHeap


def _criar_incidente(id_inc: str, expires_at: datetime) -> Incidente:
    created = expires_at - timedelta(hours=24)
    return Incidente(
        id=id_inc,
        tipo=TipoIncidente.FURTO,
        latitude=-23.55,
        longitude=-46.63,
        created_at=created,
        expires_at=expires_at,
    )


def test_indexed_min_heap_push_and_pop_order():
    heap = IndexedMinHeap()
    base_time = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)

    # Inserção em ordem não cronológica
    i3 = _criar_incidente("inc-3", base_time + timedelta(hours=3))
    i1 = _criar_incidente("inc-1", base_time + timedelta(hours=1))
    i4 = _criar_incidente("inc-4", base_time + timedelta(hours=4))
    i2 = _criar_incidente("inc-2", base_time + timedelta(hours=2))

    heap.push(i3)
    heap.push(i1)
    heap.push(i4)
    heap.push(i2)

    assert len(heap) == 4
    assert heap.peek().id == "inc-1"

    # Remoção sequencial deve respeitar o menor expires_at
    assert heap.pop_min().id == "inc-1"
    assert heap.pop_min().id == "inc-2"
    assert heap.pop_min().id == "inc-3"
    assert heap.pop_min().id == "inc-4"
    assert len(heap) == 0


def test_indexed_min_heap_update_expiration_upvote():
    """Valida que aumentar o tempo de expiração após um upvote faz o nó descer (sift_down) na Min-Heap."""
    heap = IndexedMinHeap()
    base_time = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)

    i1 = _criar_incidente("inc-1", base_time + timedelta(hours=1))
    i2 = _criar_incidente("inc-2", base_time + timedelta(hours=2))
    i3 = _criar_incidente("inc-3", base_time + timedelta(hours=3))

    heap.push(i1)
    heap.push(i2)
    heap.push(i3)

    assert heap.peek().id == "inc-1"

    # Incidente 1 recebe confirmações/upvotes e ganha +10 horas de vida
    novo_expires_at = base_time + timedelta(hours=11)
    heap.update_expiration("inc-1", novo_expires_at)

    # Agora o menor expires_at deve ser o inc-2!
    assert heap.peek().id == "inc-2"
    assert heap.get("inc-1").expires_at == novo_expires_at


def test_indexed_min_heap_pop_expired():
    heap = IndexedMinHeap()
    base_time = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)

    i1 = _criar_incidente("inc-1", base_time + timedelta(hours=1))
    i2 = _criar_incidente("inc-2", base_time + timedelta(hours=2))
    i3 = _criar_incidente("inc-3", base_time + timedelta(hours=5))

    heap.push(i1)
    heap.push(i2)
    heap.push(i3)

    # Avança o tempo para base_time + 3 horas: inc-1 e inc-2 devem expirar
    simulated_now = base_time + timedelta(hours=3)
    expirados = heap.pop_expired(simulated_now)

    assert len(expirados) == 2
    assert [e.id for e in expirados] == ["inc-1", "inc-2"]
    assert len(heap) == 1
    assert heap.peek().id == "inc-3"


def test_indexed_min_heap_remove_arbitrary_node():
    heap = IndexedMinHeap()
    base_time = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)

    i1 = _criar_incidente("inc-1", base_time + timedelta(hours=1))
    i2 = _criar_incidente("inc-2", base_time + timedelta(hours=2))
    i3 = _criar_incidente("inc-3", base_time + timedelta(hours=3))

    heap.push(i1)
    heap.push(i2)
    heap.push(i3)

    # Remove o nó do meio
    removido = heap.remove("inc-2")
    assert removido.id == "inc-2"
    assert len(heap) == 2
    assert "inc-2" not in heap

    # Verifica que a heap continua ordenada
    assert heap.pop_min().id == "inc-1"
    assert heap.pop_min().id == "inc-3"
