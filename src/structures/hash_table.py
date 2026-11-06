"""Tabela Hash com Endereçamento Aberto, Sondagem Quadrática e Rehashing em alpha > 0.50."""

from typing import Any, Generator, List, Optional, Tuple

# Sentinela única para marcar slots de chaves deletadas (Tombstone)
TOMBSTONE = object()


def _is_prime(n: int) -> bool:
    """Verifica se um número inteiro positivo é primo."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def _next_prime(n: int) -> int:
    """Retorna o menor número primo estritamente maior que n."""
    candidate = n + 1 if n % 2 == 0 else n + 2
    while not _is_prime(candidate):
        candidate += 2
    return candidate


class HashTable:
    """
    Implementação de Tabela Hash com Endereçamento Aberto (Open Addressing).
    Utiliza Sondagem Quadrática h(k, i) = (h(k) + i^2) mod m, marcador TOMBSTONE
    e redimensionamento automático para o próximo primo quando (tamanho + tombstones) / capacidade > 0.50.
    """

    def __init__(self, initial_capacity: int = 17):
        # Garante capacidade inicial prima para assegurar a cobertura da sondagem quadrática
        self._capacity = initial_capacity if _is_prime(initial_capacity) else _next_prime(initial_capacity)
        self._slots: List[Optional[Any]] = [None] * self._capacity
        self._size = 0
        self._tombstones = 0
        self._rehash_count = 0
        self._total_collisions = 0

    @property
    def capacity(self) -> int:
        """Capacidade total de slots da tabela."""
        return self._capacity

    @property
    def size(self) -> int:
        """Quantidade de elementos ativos atualmente na tabela."""
        return self._size

    @property
    def tombstones(self) -> int:
        """Quantidade de marcadores de deleção ocupando slots."""
        return self._tombstones

    @property
    def load_factor(self) -> float:
        """Fator de carga bruto considerando elementos ativos e tombstones."""
        return (self._size + self._tombstones) / self._capacity

    @property
    def rehash_count(self) -> int:
        """Contador de rehashes realizados ao longo do ciclo de vida."""
        return self._rehash_count

    @property
    def total_collisions(self) -> int:
        """Contador acumulado de colisões resolvidas durante inserções e buscas."""
        return self._total_collisions

    def _hash(self, key: Any) -> int:
        """Função hash determinística mapeando a chave para o índice base."""
        # Usa a função hash padrão de Python garantindo valor não-negativo
        return abs(hash(key)) % self._capacity

    def put(self, key: Any, value: Any) -> None:
        """
        Insere ou atualiza o par (chave, valor) na tabela.
        Se a ocupação ultrapassar 0.50, aciona o rehashing antes de inserir.
        """
        # Verifica limiar de 50% de ocupação antes da inserção
        if (self._size + self._tombstones + 1) / self._capacity > 0.50:
            self._rehash(_next_prime(self._capacity * 2))

        base_idx = self._hash(key)
        first_tombstone_idx: Optional[int] = None
        i = 0

        while i < self._capacity:
            idx = (base_idx + i * i) % self._capacity
            slot = self._slots[idx]

            if slot is None:
                # Encontrou slot vazio final: insere no primeiro tombstone encontrado ou aqui
                target_idx = first_tombstone_idx if first_tombstone_idx is not None else idx
                if target_idx == first_tombstone_idx:
                    self._tombstones -= 1
                self._slots[target_idx] = (key, value)
                self._size += 1
                return

            if slot is TOMBSTONE:
                # Guarda o primeiro tombstone para reutilizar caso a chave não exista mais adiante
                if first_tombstone_idx is None:
                    first_tombstone_idx = idx
            elif slot[0] == key:
                # Chave já existente: apenas atualiza o valor
                self._slots[idx] = (key, value)
                return
            else:
                self._total_collisions += 1

            i += 1

        # Caso extremo de não achar slot em capacidade cheia (impossível com alfa <= 0.50 e primo)
        if first_tombstone_idx is not None:
            self._slots[first_tombstone_idx] = (key, value)
            self._tombstones -= 1
            self._size += 1
        else:
            self._rehash(_next_prime(self._capacity * 2))
            self.put(key, value)

    def get(self, key: Any, default: Any = None) -> Any:
        """Retorna o valor associado à chave ou o valor default caso não exista."""
        base_idx = self._hash(key)
        i = 0

        while i < self._capacity:
            idx = (base_idx + i * i) % self._capacity
            slot = self._slots[idx]

            if slot is None:
                # Fim da cadeia de colisão sem encontrar a chave
                return default

            if slot is not TOMBSTONE and slot[0] == key:
                return slot[1]

            i += 1

        return default

    def remove(self, key: Any) -> Any:
        """
        Remove a chave da tabela marcando o slot com TOMBSTONE para manter
        a integridade das cadeias de busca subsequentes.
        """
        base_idx = self._hash(key)
        i = 0

        while i < self._capacity:
            idx = (base_idx + i * i) % self._capacity
            slot = self._slots[idx]

            if slot is None:
                raise KeyError(f"Chave '{key}' não encontrada na tabela.")

            if slot is not TOMBSTONE and slot[0] == key:
                value = slot[1]
                self._slots[idx] = TOMBSTONE
                self._size -= 1
                self._tombstones += 1
                return value

            i += 1

        raise KeyError(f"Chave '{key}' não encontrada na tabela.")

    def contains(self, key: Any) -> bool:
        """Verifica se uma chave está presente e ativa na tabela."""
        return self.get(key) is not None

    def __contains__(self, key: Any) -> bool:
        return self.contains(key)

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Generator[Any, None, None]:
        return self.keys()

    def keys(self) -> Generator[Any, None, None]:
        """Gera as chaves ativas presentes na tabela."""
        for slot in self._slots:
            if slot is not None and slot is not TOMBSTONE:
                yield slot[0]

    def values(self) -> Generator[Any, None, None]:
        """Gera os valores ativos presentes na tabela."""
        for slot in self._slots:
            if slot is not None and slot is not TOMBSTONE:
                yield slot[1]

    def items(self) -> Generator[Tuple[Any, Any], None, None]:
        """Gera os pares (chave, valor) ativos presentes na tabela."""
        for slot in self._slots:
            if slot is not None and slot is not TOMBSTONE:
                yield (slot[0], slot[1])

    def _rehash(self, new_capacity: int) -> None:
        """
        Aloca um novo array de capacidade prima expandida, reinserindo
        apenas os elementos ativos e purgando todas as TOMBSTONEs acumuladas.
        """
        old_slots = self._slots
        self._capacity = new_capacity
        self._slots = [None] * self._capacity
        self._size = 0
        self._tombstones = 0
        self._rehash_count += 1

        for slot in old_slots:
            if slot is not None and slot is not TOMBSTONE:
                self.put(slot[0], slot[1])

