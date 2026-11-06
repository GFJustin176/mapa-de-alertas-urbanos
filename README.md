# Sentinela SP — Mapa de Alertas Urbanos
Plataforma colaborativa de monitoramento e análise de segurança urbana em São Paulo, desenvolvida para a disciplina de **Estruturas de Dados Avançadas**.

O projeto demonstra a implementação manual (*from scratch*) e a sincronização em tempo real de **4 Estruturas de Dados Avançadas**:
1. **Quadtree Espacial 2D** (`capacity=4`, `max_depth=10`): Poda retangular de ramos + filtro esférico de Haversine para consultas por raio em $O(\log n)$ e desfragmentação por *merge* de quadrantes irmãos na remoção.
2. **Indexed Min-Heap**: Fila de prioridade de expiração temporal e decaimento dinâmico (Decay) com suporte a *Upvotes* e atualizações de prioridade em $O(\log n)$ via indexação direta.
3. **Hash Table com Endereçamento Aberto**: Sondagem Quadrática, marcadores sentinela `TOMBSTONE` e garantia matemática de convergência com redimensionamento para números primos em $\alpha > 0.50$.
4. **Grid Graph 30x30**: Malha espacial de 900 nós com agregação de gravidade em $O(1)$ e algoritmo de **Busca em Largura (BFS)** em 8 direções para clusterização de Componentes Conectados de alto risco ("Zonas Vermelhas").

---

## 🚀 Como Executar

### 1. Pré-requisitos
- Python 3.10+ (testado no Python 3.14)
- Pip

### 2. Instalação das Dependências
```powershell
pip install -r requirements.txt
```

### 3. Execução dos Testes Automatizados (32 Testes)
```powershell
python -m pytest tests/ -v
```

### 4. Inicialização do Servidor Web
```powershell
uvicorn src.api.app:app --reload --port 8000
```
Acesse no navegador: **[http://localhost:8000](http://localhost:8000)**

---

## 📚 Material para Apresentação e Defesa
Para o roteiro de apresentação e a preparação individual de cada um dos 4 integrantes do grupo, consulte o arquivo:
👉 **[`GUIA_DEFESA_GRUPO.md`](GUIA_DEFESA_GRUPO.md)**
