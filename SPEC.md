# Capability Map: Mapa de Alertas Urbanos (São Paulo)

| Module id | Responsibility | Integrante Responsável | Depends on |
|---|---|---|---|
| `core-domain` | Entidades `Incidente`, `Usuario`, `BoundingBox` e fórmula geodésica de `Haversine` | Todos (Base comum) | — |
| `hash-engine` | `HashTable` *from scratch* (Endereçamento Aberto, Sondagem Quadrática, `TOMBSTONE`, Rehashing com $\alpha > 0.50$) | Integrante 2 | `core-domain` |
| `temporal-heap` | `IndexedMinHeap` *from scratch* (indexada via `HashTable` em $O(1)$ para updates em $O(\log n)$) + Motor de Decaimento (Decay) e Upvotes | Integrante 2 | `core-domain`, `hash-engine` |
| `spatial-quadtree` | `Quadtree` *from scratch* (Capacidade = 4, Max Depth = 10, Inserção, Range Query por raio com poda por Bounding Box + Haversine, Remoção com Merge/Colapso automático de irmãos) | Integrante 1 | `core-domain` |
| `graph-heatmap` | `GridGraph` (`30x30` sobre São Paulo) *from scratch* + Algoritmo `BFS` (Componentes Conectados / Flood Fill) para detectar Zonas Vermelhas ($\ge 10$ pts) | Integrante 3 | `core-domain`, `hash-engine` |
| `persistence-seed` | Repositório `SQLite` + Gerador de carga realista nas zonas de São Paulo e Reidratação em memória das 4 estruturas | Integrante 3 | `core-domain`, `hash-engine`, `temporal-heap`, `spatial-quadtree`, `graph-heatmap` |
| `api-frontend` | API `FastAPI` + Interface Web interativa (`Leaflet.js`) seguindo o sistema visual `design-taste-frontend` (`software`/`tech`) | Integrante 4 | Todos os módulos acima |

Build order: `core-domain` → `hash-engine` → `temporal-heap`, `spatial-quadtree`, `graph-heatmap` → `persistence-seed` → `api-frontend`

---

# Spec: Mapa de Alertas Urbanos

## 1. Objective

Construir uma plataforma web interativa de mapeamento colaborativo de incidentes urbanos em **São Paulo** (`lat: [-23.70, -23.45], lon: [-46.80, -46.45]`), projetada para demonstrar visualmente e matematicamente a eficiência de **4 Estruturas de Dados Avançadas implementadas do zero (from scratch)**:
1. **Quadtree** com *merge* dinâmico para busca espacial em $O(\log n)$ vs. busca linear $O(n)$.
2. **Indexed Min-Heap** para expiração dinâmica e decaimento temporal (Decay) em $O(\log n)$.
3. **Hash Table com Endereçamento Aberto** (Sondagem Quadrática + `TOMBSTONE` + Rehashing em $\alpha > 0.50$) para indexação $O(1)$ de incidentes, sessões e posições da Heap.
4. **Grid Graph (`30x30`) com BFS (Flood Fill)** para detecção de componentes conectados de alto risco ("Zonas Vermelhas" / Manchas de Calor).

## 2. Tech Stack

- **Linguagem:** Python 3.11+
- **Backend Web:** FastAPI + Uvicorn (API REST JSON + arquivos estáticos)
- **Persistência:** SQLite3 (`sqlite3` nativo da standard library) + Reidratação em memória
- **Frontend Web:** HTML5, CSS3 (Tokens estritos `design-taste-frontend`), Vanilla JS (ES6+) e **Leaflet.js 1.9** (OpenStreetMap CartoDB Positron/Dark Matter tiles)
- **Testes:** `pytest` (validação unitária e de estresse das 4 estruturas de dados)

## 3. Commands

```powershell
# Instalar dependências mínimas
pip install fastapi uvicorn pytest httpx

# Rodar suíte de testes das 4 estruturas de dados
pytest tests/ -v

# Iniciar servidor de desenvolvimento
uvicorn src.api.app:app --reload --port 8000
```

## 4. Project Structure

```text
mapa-de-alertas-urbanos/
├── SPEC.md                          # Esta especificação técnica e arquitetural
├── GUIA_DEFESA_GRUPO.md             # Guia de explicação e perguntas de banca para os 4 integrantes
├── requirements.txt                 # Dependências enxutas (fastapi, uvicorn, pytest, httpx)
├── src/
│   ├── core/
│   │   ├── models.py                # Entidades: Usuario, Incidente, BoundingBox, TipoIncidente
│   │   └── geo.py                   # Fórmula de Haversine e conversão metros <-> graus (Bounding Box)
│   ├── structures/                  # As 4 estruturas implementadas 100% FROM SCRATCH
│   │   ├── hash_table.py            # Integrante 2: Open Addressing, Quadratic Probing, TOMBSTONE, Rehash > 0.50
│   │   ├── min_heap.py              # Integrante 2: IndexedMinHeap usando HashTable interna + Decay Engine
│   │   ├── quadtree.py              # Integrante 1: QuadtreeNode, insert, query_radius, remove com merge
│   │   └── grid_graph.py            # Integrante 3: GridGraph 30x30 + BFS Connected Components (Zonas Vermelhas)
│   ├── storage/
│   │   └── database.py              # Integrante 3: SQLite persistence + Gerador de Seed (São Paulo)
│   ├── engine.py                    # Orquestrador em memória sincronizando Quadtree, Heap, Hash e Grafo
│   └── api/
│       ├── app.py                   # Integrante 4: Endpoints FastAPI REST + Telemetria de performance
│       └── static/                  # Integrante 4: Frontend Web (Design Taste System)
│           ├── index.html           # Single-screen App-Frame + Secão de Telemetria Acadêmica
│           ├── system.css           # Design tokens, tipografia, cores neutras, 0% violeta, motion layer
│           └── app.js               # Controle do Leaflet, desenho dos quadrantes da Quadtree, BFS e Time Travel
└── tests/
    ├── test_hash_table.py           # Testes de colisão, TOMBSTONE e rehashing em alpha > 0.50
    ├── test_min_heap.py             # Testes de ordenação, upvote (increase TTL / sift_down) e decay
    ├── test_quadtree.py             # Testes de subdivisão (cap=4), max_depth=10, range query e merge
    └── test_grid_graph.py           # Testes de pesos celulares e clusterização BFS
```

## 5. Architecture of the 4 Data Structures (From Scratch)

### 5.1. `HashTable` (`src/structures/hash_table.py` — Integrante 2)
- **Resolução de Colisões:** Endereçamento Aberto (*Open Addressing*) com **Sondagem Quadrática** ($h(k, i) = (h(k) + i^2) \bmod m$) e capacidades em números primos (ou potências de 2 com função triangular) para garantir cobertura completa dos slots.
- **Remoção Segura:** Uso de objeto sentinela único `TOMBSTONE = object()`. Buscas (`get`) atravessam `TOMBSTONE`s; inserções (`put`) reutilizam o primeiro `TOMBSTONE` encontrado caso a chave ainda não exista.
- **Fator de Carga e Rehashing ($\alpha > 0.50$):** Definido estritamente como `(ativos + tombstones) / capacidade > 0.50`. Ao atingir o limite, a tabela dobra para o próximo primo, reinserindo apenas elementos ativos e **zerando todas as `TOMBSTONE`s**.

### 5.2. `IndexedMinHeap` (`src/structures/min_heap.py` — Integrante 2)
- **Ordenação:** Pelo atributo `expires_at` (menor timestamp no topo `heap[0]` = próximo incidente a expirar).
- **Indexação Interna $O(1)$:** Mantém uma instância da nossa `HashTable` mapeando `incidente_id -> indice_no_array`.
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

### 5.3. `Quadtree` (`src/structures/quadtree.py` — Integrante 1)
- **Limites Raiz (São Paulo):** `min_lat = -23.70, max_lat = -23.45, min_lon = -46.80, max_lon = -46.45`.
- **Regras do Nó:** `capacity = 4` incidentes, `max_depth = 10`.
- **Subdivisão:** Ao inserir o 5º ponto em uma folha com `depth < 10`, divide em 4 quadrantes (`NW`, `NE`, `SW`, `SE`) e redistribui os pontos.
- **Busca por Raio (`query_radius`):**
  1. Converte `(center_lat, center_lon, radius_meters)` em uma `BoundingBox` retangular em graus.
  2. Poda subárvores cuja `BoundingBox` não intersecta a caixa de busca.
  3. Para os pontos nas folhas visitadas, aplica a distância esférica exata de **Haversine** (`<= radius_meters`).
  4. Registra contadores de telemetria: `nodes_visited` e `distance_calculations` para comparar ao vivo contra os `total_points` da Busca Linear $O(n)$.
- **Remoção com Colapso (`remove` + `_try_merge`):** Ao remover um ponto (por expiração), sobe recursivamente verificando se o nó pai tem 4 filhos folhas e se a soma total de pontos nos 4 filhos é $\le 4$. Se sim, puxa os pontos de volta para o pai e destrói os 4 filhos.

### 5.4. `GridGraph` (`src/structures/grid_graph.py` — Integrante 3)
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
   - **Superfícies:** Tema técnico de engenharia de alta precisão (inspirado em Linear / x.ai / Figma). Fundo principal em grafite escuro técnico `#0E1013` (`--g-main`), painéis em `#15181D` (`--g-alt`), bordas hairline de `1px` em `rgba(244, 244, 240, 0.12)` e texto principal em off-white quente `#F4F4F0` (`--ink`, contraste > 12:1).
   - **Cor de Acento Única (`--action`):** Âmbar/Vermelho tático de alerta urbano `#E5484D` (para ações primárias e zonas críticas) + Ciano técnico `#2E90FA` exclusivamente para a camada de debug dos quadrantes da Quadtree. **Proibido qualquer tom de roxo/violeta/lavanda ou gradientes decorativos.**
2. **Tipografia & Hierarquia Estrita:**
   - **Display / Títulos:** `Inter` / `Space Grotesk` com *tight tracking* (`-0.02em`), *sentence case* (sem textos em ALL CAPS espaçados).
   - **Dados, Coordenadas e Telemetria ($O(\log n)$, tempos em `ms`, endereços da Hash):** `JetBrains Mono` com `font-variant-numeric: tabular-nums` para que os números do comparador de performance nunca tremam ao atualizar.
   - Nada abaixo de `13px`; textos de leitura em `16px`.
3. **Layout One-Screen App-Frame (`100svh`) + Equal Edges:**
   - **Header Fixo (`header.nav`, `72px`):** Sólido (sem *glassmorphism* borrado ou pílula flutuante), com *hairline* de `1px` inferior. Na esquerda: marca + nome **Sentinela SP** e status do relógio virtual do sistema. Na direita: botões de simulação acadêmica (`+500 Incidentes`, `Avançar +1h`, `Avançar +6h`) e o botão primário `Reportar incidente`.
   - **Workspace Principal (`App-Frame`):** Divisão limpa dentro do grid alinhado:
     - **Canvas Interativo do Mapa (8 colunas):** Mapa Leaflet de São Paulo com controles de camada no topo do frame:
       - `[x] Incidentes Ativos` (pinos coloridos por estágio de Decay: Crítico, Moderado, Baixo)
       - `[x] Subdivisões da Quadtree` (desenha ao vivo os retângulos `BoundingBox` de cada nó folha/interno para provar a árvore espacial na apresentação)
       - `[x] Zonas Vermelhas (BFS Grid Graph)` (desenha os clusters conectados detectados pelo BFS)
       - `[x] Raio de Busca (Range Query)` (círculo interativo que segue o clique do usuário + destaca a Bounding Box de poda)
     - **Painel de Telemetria & Inspeção de Estruturas (4 colunas):**
       1. **Comparador Ao Vivo (`Quadtree O(log n)` vs. `Lista Linear O(n)`):** Mostra nós visitados, cálculos de Haversine realizados, % de poda espacial e tempo em `ms`.
       2. **Estado da `IndexedMinHeap`:** Próximo incidente a expirar (topo da Heap `heap[0]`), contador regressivo e botão de Upvote (+2h de vida com reordenação instantânea).
       3. **Estado da `HashTable` (Endereçamento Aberto):** Capacidade atual, elementos ativos, contagem de `TOMBSTONE`s, Fator de Carga atual ($\alpha / 0.50$) e contador de *Rehashes* realizados.
       4. **Estado do `GridGraph (BFS)`:** Número de componentes conectados (Zonas Vermelhas) ativos e células quentes.
4. **Micro-interações Silenciosas (`motion.md`):**
   - Cards e botões respondem com transição rápida (`120ms ease-out`), elevação sutil de `2px` em itens interativos e feedback de pressão no clique (`scale(0.99)`), sem animações no scroll, sem *carousels* e sem *modals* intrusivos.

## 7. Code Style & Language Conventions

Seguindo a diretriz `comentarios-codigo-ptbr` e `ponytail (full)`:
- Código enxuto, sem abstrações desnecessárias, com comentários cirúrgicos em **Português do Brasil** em tom impessoal explicando o **porquê** algorítmico (ex: por que a `TOMBSTONE` não pode interromper a sondagem quadrática).

```python
# Exemplo do estilo de código esperado (src/structures/hash_table.py)
class HashTable:
    """Tabela Hash com Endereçamento Aberto, Sondagem Quadrática e Rehashing em alpha > 0.50."""

    def _should_rehash(self) -> bool:
        # Considera ativos + tombstones para evitar degradação da sondagem quadrática em O(n)
        return (self.size + self.tombstones) / self.capacity > 0.50
```

## 8. Testing Strategy

- **`tests/test_hash_table.py`**: Verifica inserção, colisão forçada, remoção criando `TOMBSTONE`, busca atravessando `TOMBSTONE`, reutilização de slot `TOMBSTONE` e disparo exato do `rehash` quando `(size + tombstones) / capacity > 0.50`.
- **`tests/test_min_heap.py`**: Verifica propriedade da Min-Heap, busca de índice em $O(1)$ via `HashTable`, `update_expiration` (upvote movendo o item para baixo na árvore) e remoção de expirados.
- **`tests/test_quadtree.py`**: Verifica subdivisão exata ao 5º elemento, respeito ao `max_depth = 10` para coordenadas idênticas, precisão da `query_radius` (comparando resultado exato contra busca linear de referência) e colapso (`merge`) dos 4 quadrantes ao remover incidentes.
- **`tests/test_grid_graph.py`**: Verifica acumulação de pesos nas células e agrupamento exato de regiões adjacentes via `BFS`.

## 9. Boundaries

- **Always do:** Rodar `pytest` após implementar cada estrutura; manter sincronia atômica entre as 4 estruturas no `engine.py`; manter comentários em PT-BR claros para estudo dos 4 integrantes.
- **Ask first:** Adicionar qualquer biblioteca externa além de `fastapi`, `uvicorn`, `pytest` e `httpx`.
- **Never do:** Usar `dict` nativo do Python para implementar a `HashTable`, usar `heapq` para implementar a `IndexedMinHeap`, ou usar bibliotecas prontas de R-Tree/Quadtree/Grafos (`rtree`, `scipy`, `networkx`); usar cores violeta/roxo na interface.

## 10. Success Criteria

1. As 4 estruturas (`HashTable`, `IndexedMinHeap`, `Quadtree`, `GridGraph`) são implementadas do zero sem estruturas nativas equivalentes e passam em 100% dos testes unitários no `pytest`.
2. A interface web renderiza o mapa de São Paulo permitindo clicar para buscar por raio, inserir incidentes, dar upvote, visualizar as subdivisões da Quadtree, ver as Zonas Vermelhas (BFS) e avançar o tempo (+1h / +6h) para observar o Decay e o Merge da Quadtree ao vivo.
3. O painel lateral exibe métricas reais comparando a Quadtree vs. Busca Linear $O(n)$, o estado do Fator de Carga ($\alpha \le 0.50$) + `TOMBSTONE`s da Hash Table e o topo da Min-Heap.
4. O documento `GUIA_DEFESA_GRUPO.md` entrega o roteiro completo dividido para os 4 integrantes apresentarem no dia 19/11.

## 11. Open Questions

Nenhuma pergunta técnica pendente — todas as 14 decisões do `/grill-me` foram incorporadas.

