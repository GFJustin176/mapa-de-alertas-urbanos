# Capability Map: Sentinela SP — Mapeamento Geoespacial de Incidentes

| Module id | Responsibility | Camada Arquitetural | Depends on |
|---|---|---|---|
| `core-domain` | Entidades `Incidente`, `Usuario`, `BoundingBox` e fórmula geodésica de `Haversine` | Domínio Base | — |
| `hash-engine` | `HashTable` *from scratch* (Endereçamento Aberto, Sondagem Quadrática, `TOMBSTONE`, Rehashing com $\alpha > 0.50$) | Estruturas de Dados | `core-domain` |
| `temporal-heap` | `IndexedMinHeap` *from scratch* (indexada via `HashTable` em $O(1)$ para updates em $O(\log n)$) + Motor de Decaimento (Decay) e Upvotes | Estruturas de Dados | `core-domain`, `hash-engine` |
| `spatial-quadtree` | `Quadtree` *from scratch* (Capacidade = 4, Max Depth = 10, Inserção, Range Query por raio com poda por Bounding Box + Haversine, Remoção com Merge/Colapso automático de irmãos) | Estruturas de Dados | `core-domain` |
| `graph-heatmap` | `GridGraph` (`30x30` sobre São Paulo) *from scratch* + Algoritmo `BFS` (Componentes Conectados / Flood Fill) para detectar Zonas Vermelhas ($\ge 10$ pts) | Estruturas de Dados | `core-domain`, `hash-engine` |
| `persistence-seed` | Repositório `SQLite` + Gerador de carga realista nas zonas de São Paulo e Reidratação em memória das 4 estruturas | Armazenamento & Dados | `core-domain`, `hash-engine`, `temporal-heap`, `spatial-quadtree`, `graph-heatmap` |
| `api-frontend` | API `FastAPI` + Interface Web interativa (`Leaflet.js`) seguindo o sistema visual `design-taste-frontend` (`software`/`tech`) | Interface & Aplicação | Todos os módulos acima |

Build order: `core-domain` → `hash-engine` → `temporal-heap`, `spatial-quadtree`, `graph-heatmap` → `persistence-seed` → `api-frontend`

---

# Spec: Mapa de Alertas Urbanos (Sentinela SP)

## 1. Objective

Construir uma plataforma web interativa de mapeamento colaborativo de incidentes urbanos em **São Paulo** (`lat: [-23.70, -23.45], lon: [-46.80, -46.45]`), projetada para demonstrar a eficiência computacional de **4 Estruturas de Dados Avançadas implementadas do zero (from scratch)**:
1. **Quadtree Espacial 2D** com *merge* dinâmico para busca espacial em $O(\log n)$ vs. busca linear $O(n)$.
2. **Indexed Min-Heap** para expiração dinâmica e decaimento temporal (Decay) em $O(\log n)$.
3. **Hash Table com Endereçamento Aberto** (Sondagem Quadrática + `TOMBSTONE` + Rehashing em $\alpha > 0.50$) para indexação $O(1)$ de incidentes e posições da Heap.
4. **Grid Graph (`30x30`) com BFS (Flood Fill)** para detecção de componentes conectados de alto risco ("Zonas Vermelhas" / Manchas de Calor).

## 2. Tech Stack

- **Linguagem:** Python 3.10+
- **Backend Web:** FastAPI + Uvicorn (API REST JSON + arquivos estáticos)
- **Persistência:** SQLite3 (`sqlite3` nativo da standard library) + Reidratação em memória
- **Frontend Web:** HTML5, CSS3 (Tokens estritos `design-taste-frontend`), Vanilla JS (ES6+) e **Leaflet.js 1.9** (CartoDB Dark Matter tiles)
- **Testes:** `pytest` (validação unitária e de estresse das 4 estruturas de dados)

## 3. Commands

```powershell
# Ativar ambiente virtual
.\.venv\Scripts\Activate.ps1

# Rodar suíte de testes (32 testes)
pytest tests/ -v

# Iniciar servidor de aplicação
uvicorn src.api.app:app --reload --port 8000
```

## 4. Project Structure

```text
mapa-de-alertas-urbanos/
├── SPEC.md                          # Especificação técnica e arquitetural
├── README.md                        # Documentação de arquitetura e instruções
├── requirements.txt                 # Dependências do projeto
├── src/
│   ├── core/
│   │   ├── models.py                # Entidades: Usuario, Incidente, BoundingBox, TipoIncidente
│   │   └── geo.py                   # Fórmula de Haversine e conversão metros <-> graus
│   ├── structures/                  # As 4 estruturas implementadas from scratch
│   │   ├── hash_table.py            # Open Addressing, Quadratic Probing, TOMBSTONE, Rehash > 0.50
│   │   ├── min_heap.py              # IndexedMinHeap usando HashTable interna + Decay Engine
│   │   ├── quadtree.py              # QuadtreeNode, insert, query_radius, remove com merge
│   │   └── grid_graph.py            # GridGraph 30x30 + BFS Connected Components (Zonas Vermelhas)
│   ├── storage/
│   │   ├── database.py              # SQLite persistence + reidratação em memória
│   │   └── seed.py                  # Gerador determinístico de incidentes em São Paulo
│   ├── engine.py                    # Orquestrador AlertEngine sincronizando as estruturas
│   └── api/
│       ├── app.py                   # Endpoints FastAPI REST + Telemetria de performance
│       └── static/                  # Frontend Web (Design Taste System)
│           ├── index.html           # Single-screen App-Frame + Telemetria ao vivo
│           ├── system.css           # Design tokens, tipografia tabular, superfícies neutras
│           └── app.js               # Camadas Leaflet, renderização espacial e simulação temporal
└── tests/
    ├── test_api.py                  # Testes de integração dos endpoints REST
    ├── test_domain_geo.py           # Testes de modelos e cálculos geodésicos
    ├── test_engine.py               # Testes de integração da fachada AlertEngine
    ├── test_grid_graph.py           # Testes de agregação celular e clusterização BFS
    ├── test_hash_table.py           # Testes de colisão, TOMBSTONE e rehashing alpha > 0.50
    ├── test_min_heap.py             # Testes de ordenação, upvotes e decay
    └── test_quadtree.py             # Testes de subdivisão (cap=4), max_depth=10 e merge
```

## 5. Architecture of the 4 Data Structures (From Scratch)

### 5.1. `HashTable` (`src/structures/hash_table.py`)
- **Resolução de Colisões:** Endereçamento Aberto (*Open Addressing*) com **Sondagem Quadrática** ($h(k, i) = (h(k) + i^2) \bmod m$) e capacidades em números primos para garantir cobertura completa dos slots.
- **Remoção Segura:** Uso de objeto sentinela único `TOMBSTONE = object()`. Buscas (`get`) atravessam `TOMBSTONE`s; inserções (`put`) reutilizam o primeiro `TOMBSTONE` encontrado caso a chave ainda não exista.
- **Fator de Carga e Rehashing ($\alpha > 0.50$):** Definido estritamente como `(ativos + tombstones) / capacidade > 0.50`. Ao atingir o limite, a tabela dobra para o próximo primo, reinserindo apenas elementos ativos e **zerando todas as `TOMBSTONE`s**.

### 5.2. `IndexedMinHeap` (`src/structures/min_heap.py`)
- **Ordenação:** Pelo atributo `expires_at` (menor timestamp no topo `heap[0]` = próximo incidente a expirar).
- **Indexação Interna $O(1)$:** Mantém uma instância da `HashTable` mapeando `incidente_id -> indice_no_array`.
- **Operações e Complexidades:**
  - `push(incidente)`: $O(\log n)$
  - `pop_expired(current_time)`: $O(k \log n)$ para os $k$ expirados.
  - `update_expiration(incidente_id, new_expires_at)`: Acha o índice em $O(1)$ via `HashTable` e aplica `_sift_down` / `_sift_up` em $O(\log n)$.
  - `remove(incidente_id)`: Remove arbitrariamente em $O(\log n)$.
- **Níveis de Alerta (Decay Visual):**
  - `CRITICO`: Restam $50\% \text{ a } 100\%$ do TTL.
  - `MODERADO`: Restam $20\% \text{ a } 50\%$ do TTL.
  - `BAIXO`: Restam $< 20\%$ do TTL.
  - `EXPIRADO`: $\le 0\%$ (removido automaticamente da Heap, da Quadtree, da HashTable e do GridGraph).

### 5.3. `Quadtree` (`src/structures/quadtree.py`)
- **Limites Raiz (São Paulo):** `min_lat = -23.70, max_lat = -23.45, min_lon = -46.80, max_lon = -46.45`.
- **Regras do Nó:** `capacity = 4` incidentes, `max_depth = 10`.
- **Subdivisão:** Ao inserir o 5º ponto em uma folha com `depth < 10`, divide em 4 quadrantes (`NW`, `NE`, `SW`, `SE`) e redistribui os pontos.
- **Busca por Raio (`query_radius`):**
  1. Converte `(center_lat, center_lon, radius_meters)` em uma `BoundingBox` retangular em graus.
  2. Poda subárvores cuja `BoundingBox` não intersecta a caixa de busca.
  3. Para os pontos nas folhas visitadas, aplica a distância esférica exata de **Haversine** (`<= radius_meters`).
  4. Registra contadores de telemetria: `nodes_visited` e `distance_calculations` para comparar ao vivo contra os `total_points` da Busca Linear $O(n)$.
- **Remoção com Colapso (`remove` + `_try_merge`):** Ao remover um ponto (por expiração), sobe recursivamente verificando se o nó pai tem 4 filhos folhas e se a soma total de pontos nos 4 filhos é $\le 4$. Se sim, puxa os pontos de volta para o pai e destrói os 4 filhos.

### 5.4. `GridGraph` (`src/structures/grid_graph.py`)
- **Malha Espacial:** Grade $30 \times 30$ cobrindo a Bounding Box de São Paulo (900 vértices/células).
- **Pesos de Risco por Célula:**
  - Assalto à mão armada: `+5 pts` (TTL base: `48h`)
  - Furto: `+3 pts` (TTL base: `24h`)
  - Via perigosa / Sem iluminação: `+2 pts` (TTL base: `36h`)
- **Detecção de Manchas de Calor via BFS:**
  - Limiar de Zona Vermelha: Células com pontuação $\ge 10$ pontos ativos.
  - O algoritmo percorre a grade e executa **Busca em Largura (BFS)** sob demanda (vizinhança de 8 direções) sobre células quentes não visitadas, retornando os **Componentes Conectados** (clusters de perigo) com a lista de coordenadas de suas células, score acumulado e nível de severidade do cluster.

## 6. Frontend Architecture (`design-taste-frontend` System)

Aplicando rigorosamente as diretrizes da skill `design-taste-frontend` para páginas `page-type="software"` e `site-kind="software"`:

1. **Identidade & Paleta Anti-Slop (90–95% Neutra, Zero Violeta/Lavanda):**
   - **Superfícies:** Tema técnico de engenharia de alta precisão. Fundo principal em grafite escuro técnico `#0E1013` (`--g-main`), painéis em `#15181D` (`--g-alt`), bordas hairline de `1px` em `rgba(244, 244, 240, 0.12)` e texto principal em off-white quente `#F4F4F0` (`--ink`, contraste > 12:1).
   - **Cor de Acento Única (`--action`):** Âmbar/Vermelho tático de alerta urbano `#E5484D` + Ciano técnico `#2E90FA` exclusivamente para os quadrantes da Quadtree.
2. **Tipografia & Hierarquia Estrita:**
   - **Display / Títulos:** `Inter` / `Space Grotesk` com *tight tracking* (`-0.02em`), *sentence case*.
   - **Dados, Coordenadas e Telemetria ($O(\log n)$, tempos em `ms`):** `JetBrains Mono` com `font-variant-numeric: tabular-nums` para estabilidade visual dos contadores.
3. **Layout One-Screen App-Frame (`100svh`):**
   - **Header Fixo (`header.nav`, `64px`):** Sólido com *hairline* inferior. Exibe status do relógio virtual, controles de simulação temporal e ação primária de relatório.
   - **Workspace Principal:** Canvas do mapa Leaflet (8 colunas) integrado ao painel lateral de telemetria algorítmica (4 colunas).

## 7. Code Style & Language Conventions

Seguindo a diretriz `comentarios-codigo-ptbr`:
- Código enxuto, sem abstrações desnecessárias, com comentários cirúrgicos em **Português do Brasil** em tom impessoal explicando o **porquê** algorítmico.

## 8. Testing Strategy

- `tests/test_hash_table.py`: Inserção, colisão, `TOMBSTONE`, busca contínua e rehashing $\alpha > 0.50$.
- `tests/test_min_heap.py`: Min-Heap, índice $O(1)$ via HashTable, `update_expiration` e remoção de expirados.
- `tests/test_quadtree.py`: Subdivisão (cap=4), limite de profundidade (max_depth=10), range query com poda e colapso de nós.
- `tests/test_grid_graph.py`: Acumulação de pesos e BFS para componentes conectados de risco.
- `tests/test_engine.py`: Integração atômica entre as 4 estruturas e persistência SQLite.
- `tests/test_api.py`: Contrato e validação dos endpoints REST.

## 9. Boundaries

- **Always do:** Rodar `pytest` antes de commits; manter sincronia atômica entre as 4 estruturas no `engine.py`; manter comentários impessoais em PT-BR.
- **Ask first:** Adicionar qualquer dependência externa além das especificadas.
- **Never do:** Usar estruturas prontas de bibliotecas para substituir a Quadtree, Heap, HashTable ou GridGraph.
