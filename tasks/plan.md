# Implementation Plan: Mapa de Alertas Urbanos (Sentinela SP)

## Overview

Implementação incremental do sistema colaborativo de mapeamento de incidentes urbanos em São Paulo (`lat: [-23.70, -23.45], lon: [-46.80, -46.45]`), centrado em 4 estruturas de dados avançadas construídas do zero (*from scratch*): `HashTable` (Endereçamento Aberto + Sondagem Quadrática + `TOMBSTONE` + Rehashing em $\alpha > 0.50$), `IndexedMinHeap` (Expiração dinâmica e Decay em $O(\log n)$ indexada pela `HashTable`), `Quadtree` (Busca espacial $O(\log n)$ + colapso/merge de quadrantes na remoção) e `GridGraph` (`30x30` + BFS para detecção de Zonas Vermelhas). O backend expõe métricas comparativas via FastAPI e alimenta uma interface interativa Leaflet.js desenhada sob o sistema `design-taste-frontend` (`software`, superfície neutra em grafite técnico, zero violeta).

## Dependency Graph

```text
[Task 1: Core Domain & Geo (Models, BoundingBox, Haversine)]
       │
       ├───────────────────────────────┐
       ▼                               ▼
[Task 2: HashTable (Open Addr)]  [Task 4: Quadtree (Insert/Query/Merge)]
       │                               │
       ├───────────────┐               │
       ▼               ▼               │
[Task 3: IndexedMinHeap] [Task 5: GridGraph 30x30 + BFS]
       │               │               │
       └───────────────┴───────┬───────┘
                               ▼
            [Task 6: SQLite Storage + SP Seed + Engine]
                               │
                               ▼
            [Task 7: FastAPI REST + Design-Taste Frontend]
                               │
                               ▼
            [Task 8: Documentação Técnica da Arquitetura]
```

## Architecture Decisions

- **HashTable com Rehashing Agressivo ($\alpha > 0.50$) e Capacidade Prima:** A sondagem quadrática ($h(k, i) = (h(k) + i^2) \bmod m$) tem garantia matemática de encontrar um slot vazio se e somente se a capacidade $m$ for um número primo e o fator de carga ocupacional for $\le 0.50$. Por isso, o limiar escolhido ($\alpha = (\text{ativos} + \text{tombstones}) / m > 0.50$) + redimensionamento para o próximo primo garante matematicamente que nenhuma inserção falhará por ciclo na sondagem.
- **IndexedMinHeap acoplada à HashTable:** Evita busca linear $O(n)$ ao atualizar a vida útil de um incidente após um *upvote*. O mapa interno `id -> idx` usa a própria `HashTable`, garantindo independência de bibliotecas externas e mantendo `update_expiration` e `remove` em $O(\log n)$ estrito.
- **Quadtree com Capacidade 4, Max Depth 10 e Merge Recursivo:** Impede *StackOverflowError* se múltiplos relatos caírem na mesma coordenada GPS (parando a subdivisão no nível 10) e executa `_try_merge()` no caminho de volta da remoção para enxugar quadrantes ociosos após o Decay.
- **Comparador Empírico $O(\log n)$ vs. $O(n)$ em Toda Busca:** O motor espacial executa a busca na Quadtree contabilizando nós visitados e distâncias Haversine calculadas, e compara contra a varredura linear sobre a lista de incidentes ativos para exibir o ganho percentual real na tela.
- **Design System Anti-Slop (`design-taste-frontend`):** App-Frame em tela única (`100svh`), fundo grafite neutro (`#0E1013` / `#15181D`), bordas *hairline* de `1px`, tipografia tabular (`JetBrains Mono`) para que os contadores não tremam, acento único vermelho tático (`#E5484D`) e ciano técnico (`#2E90FA`) para o grid da Quadtree. Zero roxo/violeta.

## Task List

| Module id | Responsibility |
|---|---|
| `core-domain` | Entidades `Incidente`, `Usuario`, `BoundingBox` e fórmula geodésica de `Haversine` |
| `hash-engine` | `HashTable` *from scratch* (Endereçamento Aberto, Sondagem Quadrática, `TOMBSTONE`, Rehashing com $\alpha > 0.50$) |
| `temporal-heap` | `IndexedMinHeap` *from scratch* (indexada via `HashTable` em $O(1)$ para updates em $O(\log n)$) + Motor de Decaimento (Decay) e Upvotes |
| `spatial-quadtree` | `Quadtree` *from scratch* (Capacidade = 4, Max Depth = 10, Inserção, Range Query por raio com poda por Bounding Box + Haversine, Remoção com Merge/Colapso automático de irmãos) |
| `graph-heatmap` | `GridGraph` (`30x30` sobre São Paulo) *from scratch* + Algoritmo `BFS` (Componentes Conectados / Flood Fill) para detectar Zonas Vermelhas ($\ge 10$ pts) |
| `persistence-seed` | Repositório `SQLite` + Gerador de carga realista nas zonas de São Paulo e Reidratação em memória das 4 estruturas |
| `api-frontend` | API `FastAPI` + Interface Web interativa (`Leaflet.js`) seguindo o sistema visual `design-taste-frontend` (`software`/`tech`) |

### Phase 1: Fundação & Estruturas de Dados
- [x] **Task 1:** Ambiente, Entidades Core (`Incidente`, `Usuario`, `BoundingBox`) e Geometria (`Haversine`)
- [x] **Task 2:** `HashTable` *from scratch* (Endereçamento Aberto, Sondagem Quadrática, `TOMBSTONE`, Rehash $> 0.50$) + Testes
- [x] **Task 3:** `IndexedMinHeap` *from scratch* (Fila de Prioridade de Expiração + Upvotes + Decay) + Testes

### Checkpoint 1: Estruturas de Indexação e Tempo
- [x] `pytest tests/test_hash_table.py tests/test_min_heap.py` passa 100%

### Phase 2: Estruturas Espaciais e de Grafos
- [x] **Task 4:** `Quadtree` *from scratch* (Subdivisão, Range Query com poda + Haversine, Remoção com Merge) + Testes
- [x] **Task 5:** `GridGraph` `30x30` *from scratch* + Algoritmo `BFS` (Componentes Conectados / Zonas Vermelhas) + Testes

### Checkpoint 2: As 4 Estruturas Validadas
- [x] `pytest tests/` passa 100% nas 4 estruturas isoladas

### Phase 3: Persistência, Orquestração e Interface Web
- [x] **Task 6:** Persistência `SQLite`, Gerador de Carga Realista de São Paulo (Seed) e Orquestrador `AlertEngine`
- [x] **Task 7:** API `FastAPI` + Frontend Interativo (`Leaflet.js` + Sistema Visual `design-taste-frontend`)
- [x] **Task 8:** Documentação Técnica e Validação End-to-End

### Checkpoint Final: Entrega Completa
- [x] Todos os testes unitários e de integração passando
- [x] Servidor FastAPI respondendo e interface renderizando Quadtree, BFS Heatmaps, Time Travel e Telemetria
- [x] Documentação técnica finalizada

## Parallelization Opportunities

- As **Tasks 2, 4 e 5** dependem apenas da **Task 1** (`core-domain`), podendo ser desenvolvidas e testadas de forma modular e independente.
- A **Task 3** (`IndexedMinHeap`) depende apenas da **Task 2** (`HashTable`).

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Ciclo infinito na Sondagem Quadrática se a tabela encher | High | Capacidades estritamente em números primos (`next_prime`) combinadas com Rehashing imediato em $\alpha > 0.50$ garantem matematicamente a convergência. |
| Coordenadas idênticas estourando recursão na Quadtree | High | Limite `max_depth = 10`; no nível 10 o nó folha aceita mais que `capacity = 4` pontos sem subdividir. |
| Dessincronização entre Quadtree, Heap, Hash e Grafo ao expirar itens | High | Centralizar todas as mutações (`report_incident`, `upvote_incident`, `advance_time`) na fachada `AlertEngine` com testes de invariante. |
| Poluição visual no mapa com +1.000 pontos e retângulos da Quadtree | Med | Controles de camadas independentes (toggles para Pinos, Quadrantes da Quadtree, Zonas Vermelhas BFS e Raio) e estilo de linha fina (`1px` ciano com baixa opacidade de preenchimento). |

## Open Questions

Nenhuma. Tudo pronto para execução das tarefas quando autorizado.

