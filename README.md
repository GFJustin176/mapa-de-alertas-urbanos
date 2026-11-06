# Sentinela SP — Plataforma Geoespacial de Monitoramento Urbano

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-32%20Passed-success?logo=pytest&logoColor=white)](#testes-automatizados)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Plataforma de alta performance para mapeamento colaborativo, indexação espacial e análise preditiva de manchas de calor em áreas urbanas de alta densidade (centrada na Região Metropolitana de São Paulo).

O núcleo do projeto consiste na concepção e implementação manual (*from scratch*) de **4 Estruturas de Dados Avançadas e Algoritmos Clássicos de Otimização**, garantindo escalabilidade sub-linear para milhares de ocorrências simultâneas sem dependência de bibliotecas de terceiros para o processamento de dados em memória.

---

## 📐 Arquitetura do Sistema

```text
                               ┌─────────────────────────────┐
                               │   Interface Web Interativa  │
                               │   (Leaflet.js + CartoDB)    │
                               └──────────────┬──────────────┘
                                              │ HTTP / JSON
                               ┌──────────────▼──────────────┐
                               │      FastAPI REST API       │
                               │     (Endpoints & CORS)      │
                               └──────────────┬──────────────┘
                                              │
                               ┌──────────────▼──────────────┐
                               │        AlertEngine          │
                               │  (Fachada de Orquestração)  │
                               └──────┬───────┬───────┬──────┘
                                      │       │       │
            ┌─────────────────────────┼───────┴───────┼─────────────────────────┐
            ▼                         ▼               ▼                         ▼
  ┌───────────────────┐    ┌────────────────────┐   ┌───────────────────┐   ┌─────────────────────┐
  │ 1. Quadtree 2D    │    │ 2. IndexedMinHeap  │   │ 3. HashTable      │   │ 4. GridGraph 30x30  │
  │ • Busca O(log n)  │    │ • TTL Dinâmico     │   │ • Open Addressing │   │ • Agregação O(1)    │
  │ • Poda BoundingBox│    │ • Upvote em O(log n│   │ • Sondagem Quad.  │   │ • BFS 8-Direcional  │
  │ • Merge Recursivo │    │ • Mapa reverso O(1)│   │ • Tombstones / α  │   │ • Zonas Vermelhas   │
  └─────────┬─────────┘    └──────────┬─────────┘   └─────────┬─────────┘   └──────────┬──────────┘
            │                         │                       │                        │
            └─────────────────────────┼───────────────────────┴────────────────────────┘
                                      │ Persistência Durável
                               ┌──────▼──────┐
                               │ SQLite DB   │
                               └─────────────┘
```

---

## 🧠 Estruturas de Dados Avançadas (Implementações Manuais)

### 1. Quadtree Espacial 2D (`src/structures/quadtree.py`)
- **Objetivo:** Reduzir a complexidade de buscas por proximidade de $O(n)$ para tempo logarítmico $O(\log n)$.
- **Poda Espacial (*Bounding Box Pruning*):** Circunscreve o raio de busca esférico em um retângulo geodésico. Subárvores que não intersectam a região de interesse são descartadas sem avaliar os pontos internos.
- **Cálculo Geodésico Fino:** A fórmula de **Haversine** (raio terrestre $R = 6.371\text{ km}$) é computada estritamente sobre os candidatos remanescentes nas folhas interceptadas.
- **Prevenção de Estouro de Pilha:** Implementação de `capacity = 4` e profundidade máxima estrita `max_depth = 10`, prevenindo recursão infinita no caso de alta densidade em coordenadas GPS idênticas.
- **Desfragmentação com Merge Recursivo:** Ao expirar ou deletar incidentes, o método `_try_merge` inspeciona a soma de nós irmãos. Se $\sum \text{pontos} \le 4$, colapsa os 4 quadrantes de volta para o nó pai, mantendo a árvore enxuta.

### 2. Indexed Min-Heap (`src/structures/min_heap.py`)
- **Objetivo:** Gestão temporal de expiração (Decay) e reordenação prioritária em $O(\log n)$.
- **TTL Dinâmico:** Cada tipo de incidente possui tempo de vida base (Assalto = 48h, Furto = 24h, Via Perigosa = 36h). Confirmações comunitárias (*upvotes*) concedem bônus de extensão de vida útil (+2h).
- **Indexação Reversa $O(1)$:** Heaps convencionais demandam varredura linear $O(n)$ para localizar um nó arbitrário. A `IndexedMinHeap` mantém internamente uma instância da `HashTable` mapeando `id -> indice_no_array`. Ao atualizar o TTL, o nó é localizado em $O(1)$ e sua nova posição é corrigida via `_sift_down` em $O(\log n)$.

### 3. Hash Table com Endereçamento Aberto (`src/structures/hash_table.py`)
- **Objetivo:** Indexação primária e resolução de chaves em tempo esperado $O(1)$ com alta localidade de cache.
- **Sondagem Quadrática:** Tratamento de colisão por dispersão quadrática $h(k, i) = (h(k) + i^2) \bmod m$.
- **Marcador `TOMBSTONE`:** Deleções físicas rompem a cadeia de sondagem para chaves subsequentes. O sentinela `TOMBSTONE` preserva o encadeamento de busca enquanto permite a reutilização do slot em inserções posteriores.
- **Garantia Matemática de Convergência:** O redimensionamento (*rehashing*) ocorre para o próximo número primo assim que `(tamanho + tombstones) / capacidade > 0.50`. Pelo teorema da sondagem quadrática, se $m$ for primo e $\alpha \le 0.50$, garante-se a visita de pelo menos $(m+1)/2$ posições livres sem entrar em loop.

### 4. Grid Graph 2D & BFS Heatmaps (`src/structures/grid_graph.py`)
- **Objetivo:** Detecção em tempo real de manchas de calor (*Heatmaps*) e agrupamento de regiões críticas sem sobrecarga computacional.
- **Discretização em Grade:** Malha bidimensional $30 \times 30$ cobrindo a região de São Paulo (`[-23.70, -23.45]` Lat, `[-46.80, -46.45]` Lon). Mapeamento de coordenadas GPS para células em tempo $O(1)$.
- **Pesos de Risco Cumulativos:** Assaltos (+5 pts), Furtos (+3 pts) e Vias Perigosas (+2 pts).
- **Busca em Largura (BFS 8-Direcional):** Algoritmo de identificação de **Componentes Conectados** executado sobre células com score $\ge 10$ pontos (*Threshold*), agrupando vizinhos ortogonais e diagonais em polígonos contínuos de "Zonas Vermelhas". Complexidade $O(V + E)$ com $V = 900$.

---

## ⚡ Telemetria & Comparativo de Desempenho

O sistema conta com um motor de benchmarking em tempo real integrado ao painel da interface. A cada consulta espacial por raio, executa-se simultaneamente a busca na **Quadtree** e uma varredura completa por **Busca Linear $O(n)$**:

| Métrica | Busca Linear $O(n)$ | Quadtree $O(\log n)$ | Ganho / Otimização |
|---|---|---|---|
| **Cálculos de Distância (500 alertas)** | 500 cálculos | 8 a 18 cálculos | **96% a 98% de redução** |
| **Nós / Elementos Inspecionados** | 100% da base | 5 a 8 nós da árvore | **Poda de 90%+ do espaço** |
| **Tempo de Execução** | ~3.5 ms a 8.0 ms | ~0.15 ms a 0.40 ms | **Aceleração de até 20x** |

---

## 🛠️ Stack Tecnológica

- **Linguagem:** Python 3.10+
- **Framework Web:** FastAPI (ASGI assíncrono de alto rendimento)
- **Servidor:** Uvicorn
- **Persistência:** SQLite3 (Driver nativo, transações ACID e reidratação em memória)
- **Frontend:** Vanilla JavaScript (ES6+), CSS3 moderno estruturado por Design Tokens, e Leaflet.js 1.9 com tiles técnicos CartoDB Dark Matter.
- **Suíte de Testes:** Pytest (32 testes unitários e de integração cobrindo 100% dos requisitos).

---

## 🚀 Como Executar

### 1. Clonar o Repositório
```bash
git clone https://github.com/seu-usuario/sentinela-sp.git
cd sentinela-sp
```

### 2. Ativar o Ambiente Virtual Isolado
```powershell
# No Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# No Linux / macOS:
source .venv/bin/activate
```
*(Caso deseje recriar o ambiente do zero: `python -m venv .venv` e `pip install -r requirements.txt`)*

### 3. Executar os Testes Automatizados
```bash
pytest tests/ -v
```
*Saída esperada: 32 passed em menos de 2.5 segundos.*

### 4. Iniciar o Servidor de Aplicação
```bash
uvicorn src.api.app:app --reload --port 8000
```
Abra o navegador em: **[http://localhost:8000](http://localhost:8000)**

---

## 📁 Estrutura de Diretórios

```text
├── src/
│   ├── core/
│   │   ├── models.py         # Entidades de domínio (Incidente, BoundingBox, Usuario)
│   │   └── geo.py            # Geometria esférica (Haversine e transformações retangulares)
│   ├── structures/           # Estruturas implementadas from scratch
│   │   ├── quadtree.py       # Quadtree 2D com poda e merge dinâmico
│   │   ├── min_heap.py       # IndexedMinHeap com sincronização O(1) e Decay
│   │   ├── hash_table.py     # HashTable Open Addressing com Quadratic Probing e Tombstones
│   │   └── grid_graph.py     # GridGraph 30x30 e BFS de Componentes Conectados
│   ├── storage/
│   │   ├── database.py       # Camada de persistência relacional SQLite
│   │   └── seed.py           # Gerador determinístico de incidentes em São Paulo
│   ├── engine.py             # AlertEngine (Fachada de orquestração atômica)
│   └── api/
│       ├── app.py            # Endpoints REST e injeção de dependências
│       └── static/           # Aplicação frontend web (HTML5 / CSS3 / Leaflet)
├── tests/                    # Suíte de testes automatizados com Pytest
├── SPEC.md                   # Especificação técnica e arquitetural do projeto
└── requirements.txt          # Dependências mínimas
```

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte `LICENSE` para mais informações.
