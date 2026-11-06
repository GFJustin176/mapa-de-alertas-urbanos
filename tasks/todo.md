# Task Breakdown: Mapa de Alertas Urbanos (Sentinela SP)

## Task 1: Ambiente, Entidades Core e Geometria (Haversine & BoundingBox)

**Description:** Configurar `requirements.txt` e implementar as entidades de domínio (`Incidente`, `Usuario`, `BoundingBox`, `TipoIncidente`) e os utilitários geodésicos (`haversine_meters` e `bounding_box_from_radius`) para a região de São Paulo (`lat: [-23.70, -23.45], lon: [-46.80, -46.45]`).

**Acceptance criteria:**
- [ ] `BoundingBox` suporta verificação de pertinência de ponto (`contains`) e interseção entre retângulos (`intersects`).
- [ ] `haversine_meters` calcula a distância esférica exata em metros entre duas coordenadas GPS.
- [ ] `Incidente` calcula seu nível de alerta dinâmico (`CRITICO`, `MODERADO`, `BAIXO`, `EXPIRADO`) com base no percentual de vida restante.

**Verification:**
- [ ] Tests pass: `pytest tests/test_quadtree.py -k "bounding_box or haversine"`

**Dependencies:** None

**Files likely touched:**
- `requirements.txt`
- `src/__init__.py`
- `src/core/__init__.py`
- `src/core/models.py`
- `src/core/geo.py`

**Estimated scope:** Small (3-5 files)

---

## Task 2: HashTable From Scratch (Open Addressing + Quadratic Probing + Rehash > 0.50)

**Description:** Implementar a `HashTable` do zero sem usar `dict` para armazenamento, empregando Endereçamento Aberto, Sondagem Quadrática ($h(k, i) = (h(k) + i^2) \bmod m$), marcador explícito `TOMBSTONE` para deleções e Rehashing automático para o próximo número primo sempre que `(size + tombstones) / capacity > 0.50`.

**Acceptance criteria:**
- [ ] Suporta `put(key, value)`, `get(key)`, `remove(key)`, `contains(key)` e `values()` em tempo esperado $O(1)$.
- [ ] Remoção marca o slot com `TOMBSTONE`, permitindo que buscas por chaves em cadeia de colisão continuem funcionando.
- [ ] Dispara `_rehash()` imediatamente quando `(size + tombstones) / capacity > 0.50`, zerando todas as `TOMBSTONE`s e mantendo a tabela enxuta.
- [ ] Expõe telemetria (`capacity`, `size`, `tombstones`, `load_factor`, `rehash_count`, `total_collisions`).

**Verification:**
- [ ] Tests pass: `pytest tests/test_hash_table.py -v`

**Dependencies:** Task 1

**Files likely touched:**
- `src/structures/__init__.py`
- `src/structures/hash_table.py`
- `tests/test_hash_table.py`

**Estimated scope:** Small (2-3 files)

---

## Task 3: IndexedMinHeap From Scratch + Motor de Expiração e Upvotes

**Description:** Implementar a `IndexedMinHeap` do zero ordenada por `expires_at` (menor timestamp no topo `heap[0]`), utilizando nossa `HashTable` interna para mapear `incidente_id -> indice_na_heap` em $O(1)$ e permitir atualizações de prioridade (`upvote` aumentando TTL) e remoções arbitrárias em $O(\log n)$.

**Acceptance criteria:**
- [ ] `push(incidente)` e `pop_min()` mantêm a invariante de Min-Heap em $O(\log n)$.
- [ ] `update_expiration(incidente_id, new_expires_at)` localiza o nó em $O(1)$ via `HashTable` interna e aplica `_sift_down` / `_sift_up` em $O(\log n)$.
- [ ] `pop_expired(current_time)` remove e retorna todos os incidentes com `expires_at <= current_time`.

**Verification:**
- [ ] Tests pass: `pytest tests/test_min_heap.py -v`

**Dependencies:** Task 1, Task 2

**Files likely touched:**
- `src/structures/min_heap.py`
- `tests/test_min_heap.py`

**Estimated scope:** Small (2 files)

---

## Checkpoint 1: Após Tasks 1–3
- [ ] `pytest tests/test_hash_table.py tests/test_min_heap.py -v` passa com 100% de sucesso.
- [ ] Zero uso de `dict` ou `heapq` dentro das estruturas implementadas.

---

## Task 4: Quadtree Espacial From Scratch (Insert, Range Query e Merge na Remoção)

**Description:** Implementar a `Quadtree` do zero (`capacity = 4`, `max_depth = 10`) centrada em São Paulo, com subdivisão automática em 4 quadrantes (`NW`, `NE`, `SW`, `SE`), busca espacial por raio (`query_radius` combinando poda de `BoundingBox` com filtro fino de `Haversine` e contadores de telemetria) e remoção com colapso (`_try_merge`) automático quando os 4 filhos folhas somam $\le 4$ pontos.

**Acceptance criteria:**
- [ ] Subdivide exatamente ao receber o 5º ponto até a profundidade máxima 10.
- [ ] `query_radius(lat, lon, radius_m)` retorna exatamente os mesmos pontos que a busca linear $O(n)$, mas visitando uma fração dos nós e registrando `nodes_visited` e `distance_calculations`.
- [ ] `remove(incidente_id, lat, lon)` remove o ponto e funde (colapsa) os 4 subquadrantes de volta no nó pai quando a soma de pontos dos irmãos cai para $\le 4$.
- [ ] `get_all_Quadrants()` exporta os limites de todos os nós ativos para renderização visual no mapa.

**Verification:**
- [ ] Tests pass: `pytest tests/test_quadtree.py -v`

**Dependencies:** Task 1

**Files likely touched:**
- `src/structures/quadtree.py`
- `tests/test_quadtree.py`

**Estimated scope:** Small (2 files)

---

## Task 5: GridGraph 30x30 From Scratch + Clusterização BFS (Zonas Vermelhas)

**Description:** Implementar o grafo em grade `GridGraph` (`30x30` células sobre São Paulo) do zero, acumulando pesos de severidade por célula (Assalto = 5, Furto = 3, Via Perigosa = 2) e executando o algoritmo **BFS (Busca em Largura / Componentes Conectados)** sobre células com score $\ge 10$ para identificar manchas de calor ("Zonas Vermelhas") contínuas.

**Acceptance criteria:**
- [ ] Mapeia coordenadas `(lat, lon)` em índices de célula `(row, col)` em $O(1)$ e atualiza o peso na inserção e na remoção de incidentes.
- [ ] `find_red_zones_bfs(threshold=10)` executa BFS em vizinhança de 8 direções (usando fila própria sem bibliotecas externas de grafos) e retorna os clusters conectados com suas `BoundingBoxes`, pontuação total e quantidade de células.

**Verification:**
- [ ] Tests pass: `pytest tests/test_grid_graph.py -v`

**Dependencies:** Task 1, Task 2

**Files likely touched:**
- `src/structures/grid_graph.py`
- `tests/test_grid_graph.py`

**Estimated scope:** Small (2 files)

---

## Checkpoint 2: Após Tasks 4–5
- [ ] `pytest tests/ -v` passa em todas as 4 estruturas (`HashTable`, `IndexedMinHeap`, `Quadtree`, `GridGraph`).

---

## Task 6: Persistência SQLite, Seed de São Paulo e Orquestrador AlertEngine

**Description:** Implementar a camada `SQLite` (`src/storage/database.py`), o gerador de dados realistas em hotspots de São Paulo (Sé, Paulista, Pinheiros, Itaquera, Santo Amaro, Vila Mariana, Tatuapé, Lapa, etc.) e a fachada `AlertEngine` (`src/engine.py`) que mantém as 4 estruturas sincronizadas em memória, controla o relógio virtual ("Time Travel") e calcula o comparativo ao vivo entre `Quadtree O(log n)` e `Lista Linear O(n)`.

**Acceptance criteria:**
- [ ] Inicializa o banco SQLite com seed inicial de incidentes distribuídos em São Paulo e reconstrói as 4 estruturas em memória no startup.
- [ ] Operações `create_incident`, `upvote_incident`, `advance_time(hours)` e `inject_bulk_incidents(count)` atualizam atomicamente `HashTable`, `IndexedMinHeap`, `Quadtree`, `GridGraph` e `SQLite`.
- [ ] `search_radius(lat, lon, radius_m)` retorna os incidentes + o comparativo completo de telemetria (`quadtree_ms`, `linear_ms`, `quadtree_calcs`, `linear_calcs`, `pruning_ratio`).

**Verification:**
- [ ] Tests pass: `pytest tests/ -v` (incluindo teste de integração do `AlertEngine`)

**Dependencies:** Tasks 1, 2, 3, 4, 5

**Files likely touched:**
- `src/storage/__init__.py`
- `src/storage/database.py`
- `src/engine.py`
- `tests/test_engine.py`

**Estimated scope:** Medium (4 files)

---

## Task 7: API FastAPI + Frontend Interativo (Leaflet.js + Design-Taste System)

**Description:** Criar os endpoints REST no FastAPI (`src/api/app.py`) e a interface web em tela única (`100svh` App-Frame) seguindo a estética `design-taste-frontend` (`system.css`, zero violeta, tipografia tabular `JetBrains Mono`, superfícies neutras `#0E1013` / `#15181D`, acento `#E5484D` e quadrantes `#2E90FA`), permitindo clicar no mapa de São Paulo para consultar raio, reportar incidente, dar upvote, ligar/desligar o desenho dos quadrantes da Quadtree e das Zonas Vermelhas BFS, injetar +500 incidentes e avançar o tempo (+1h / +6h).

**Acceptance criteria:**
- [ ] Endpoints REST funcionais: `GET /api/state`, `GET /api/search`, `POST /api/incidents`, `POST /api/incidents/{id}/upvote`, `POST /api/simulate/time`, `POST /api/simulate/seed`, `POST /api/simulate/reset`.
- [ ] Mapa Leaflet de São Paulo desenha em tempo real os pinos (coloridos por Decay), as subdivisões da Quadtree, os polígonos das Zonas Vermelhas (BFS) e o círculo de Range Query.
- [ ] Painel de telemetria exibe lado a lado `Quadtree O(log n)` vs `Busca Linear O(n)`, topo da `IndexedMinHeap`, e métricas da `HashTable` (`load_factor / 0.50`, `tombstones`, `rehashes`).

**Verification:**
- [ ] Servidor inicia sem erros e responde `200 OK` nos testes de endpoint (`pytest tests/test_api.py -v`).

**Dependencies:** Task 6

**Files likely touched:**
- `src/api/__init__.py`
- `src/api/app.py`
- `src/api/static/index.html`
- `src/api/static/system.css`
- `src/api/static/app.js`
- `tests/test_api.py`

**Estimated scope:** Medium (5 files)

---

## Task 8: Guia de Defesa Acadêmica para os 4 Integrantes (`GUIA_DEFESA_GRUPO.md`)

**Description:** Redigir o documento completo de preparação para a apresentação do dia 19/11, dividindo a explicação técnica, invariantes matemáticas, análise de complexidade Big-O e respostas para prováveis perguntas do professor para cada um dos 4 integrantes do grupo, além de um roteiro passo a passo de demonstração ao vivo na interface.

**Acceptance criteria:**
- [ ] Contém seção individual detalhada para o Integrante 1 (Quadtree + Haversine + Merge), Integrante 2 (HashTable Open Addressing/Tombstone/$\alpha > 0.50$ + IndexedMinHeap/Decay), Integrante 3 (GridGraph 30x30 + BFS Connected Components + SQLite) e Integrante 4 (Arquitetura FastAPI + Visualização e Telemetria Comparativa).
- [ ] Inclui roteiro cronometrado de demonstração ao vivo ("Script de Apresentação de 10 minutos").

**Verification:**
- [ ] Documento gerado e revisado na raiz do repositório (`GUIA_DEFESA_GRUPO.md`).

**Dependencies:** Task 7

**Files likely touched:**
- `GUIA_DEFESA_GRUPO.md`
- `README.md`

**Estimated scope:** Small (2 files)

