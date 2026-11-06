"""Testes unitários exaustivos para a HashTable com Endereçamento Aberto e Sondagem Quadrática."""

import pytest
from src.structures.hash_table import HashTable, TOMBSTONE


def test_hash_table_put_and_get():
    ht = HashTable(initial_capacity=11)
    ht.put("inc-1", "Assalto na Paulista")
    ht.put("inc-2", "Furto na Sé")

    assert ht.get("inc-1") == "Assalto na Paulista"
    assert ht.get("inc-2") == "Furto na Sé"
    assert ht.get("inc-999") is None
    assert ht.get("inc-999", "padrao") == "padrao"
    assert len(ht) == 2


def test_hash_table_update_existing_key():
    ht = HashTable(initial_capacity=11)
    ht.put("inc-1", "Versao 1")
    assert ht.get("inc-1") == "Versao 1"
    assert len(ht) == 1

    ht.put("inc-1", "Versao 2")
    assert ht.get("inc-1") == "Versao 2"
    assert len(ht) == 1  # Tamanho não deve duplicar


def test_hash_table_remove_creates_tombstone():
    ht = HashTable(initial_capacity=11)
    ht.put("chave-a", 100)
    ht.put("chave-b", 200)

    assert "chave-a" in ht
    val = ht.remove("chave-a")
    assert val == 100
    assert "chave-a" not in ht
    assert ht.get("chave-a") is None
    assert len(ht) == 1
    assert ht.tombstones == 1


def test_hash_table_collision_resolution_and_tombstone_chaining():
    # Usamos uma capacidade inicial de 11 (número primo)
    ht = HashTable(initial_capacity=11)

    # Inserimos chaves e verificamos que colisões são resolvidas por sondagem quadrática
    ht.put("k1", "v1")
    ht.put("k2", "v2")
    ht.put("k3", "v3")

    # Remove o primeiro da cadeia
    ht.remove("k1")

    # As chaves posteriores na cadeia ainda devem ser encontradas atravessando o TOMBSTONE
    assert ht.get("k2") == "v2"
    assert ht.get("k3") == "v3"

    # Nova inserção pode reutilizar o slot da TOMBSTONE
    ht.put("k4", "v4")
    assert ht.get("k4") == "v4"


def test_hash_table_rehash_at_50_percent_load():
    # Inicial com 7 (primo)
    ht = HashTable(initial_capacity=7)
    # Limiar: ocupados / 7 > 0.50 -> 4 / 7 = 0.571 > 0.50 dispara rehash
    ht.put("c1", 1)
    ht.put("c2", 2)
    ht.put("c3", 3)
    assert ht.rehash_count == 0
    assert ht.capacity == 7

    # 4º elemento: (3 + 1) / 7 = 0.5714 > 0.50 -> Dispara rehash!
    ht.put("c4", 4)
    assert ht.rehash_count == 1
    assert ht.capacity > 7
    # Todos os valores devem estar acessíveis
    for i in range(1, 5):
        assert ht.get(f"c{i}") == i


def test_hash_table_rehash_clears_tombstones():
    # Inserir e remover para acumular tombstones
    ht = HashTable(initial_capacity=7)
    ht.put("a", 1)
    ht.put("b", 2)
    ht.remove("a")  # tamanho = 1, tombstones = 1, ocupacao = 2/7
    ht.remove("b")  # tamanho = 0, tombstones = 2, ocupacao = 2/7

    assert ht.tombstones == 2
    # Inserir novos itens até (0 + 2 + novos) / 7 > 0.50 -> novos > 1.5 -> ao inserir 2 itens
    ht.put("c", 3)
    ht.put("d", 4)

    # Disparou rehash: tombstones devem ter sido limpas
    assert ht.tombstones == 0
    assert ht.get("c") == 3
    assert ht.get("d") == 4


def test_hash_table_keys_values_items():
    ht = HashTable(initial_capacity=11)
    ht.put("x", 10)
    ht.put("y", 20)
    ht.put("z", 30)

    assert set(ht.keys()) == {"x", "y", "z"}
    assert set(ht.values()) == {10, 20, 30}
    assert set(ht.items()) == {("x", 10), ("y", 20), ("z", 30)}
