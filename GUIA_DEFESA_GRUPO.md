# Guia de Apresentação e Defesa Acadêmica — Sentinela SP
**Disciplina:** Estruturas de Dados Avançadas  
**Projeto:** Mapa de Alertas Urbanos (São Paulo)  
**Data Limite de Entrega:** 19/11  
**Integrantes:** 4 Alunos  

---

## 1. Visão Geral da Arquitetura do Projeto

O **Sentinela SP** é uma plataforma de monitoramento urbano colaborativo projetada especificamente para demonstrar a superioridade e a sincronização de **4 Estruturas de Dados Avançadas construídas 100% do zero (*from scratch*)**:

```text
                               [ Interface Web (Leaflet.js) ]
                                             │
                                     [ FastAPI REST ]
                                             │
                                     [ AlertEngine ]
                  ┌──────────────────────────┼──────────────────────────┐
                  ▼                          ▼                          ▼
          [ 1. Quadtree ]           [ 2. IndexedMinHeap ]       [ 3. HashTable ]
     • Busca Espacial O(log n)    • Expiração Dinâmica         • Acesso O(1)
     • Poda Bounding Box          • Upvotes com sift_down      • Open Addressing
     • Merge de Quadrantes        • Index O(1) via HashTable   • Sondagem Quadrática
                  │                          │                 • TOMBSTONES
                  └──────────────────────────┼─────────────────• Alpha > 0.50
                                             ▼
                                     [ 4. GridGraph 30x30 ]
                                   • Agregação Celular O(1)
                                   • BFS Componentes Conectados (Zonas Vermelhas)
```

---

## 2. Divisão Oficial de Defesa entre os 4 Integrantes

---

### 👤 Integrante 1: O Motor Espacial (Quadtree & Geometria)
**Responsabilidade:** Explicar a indexação 2D, a poda de ramos, a Range Query com Haversine e a desfragmentação por Merge.

#### O que você precisa dominar:
1. **O Problema da Busca Linear:** Se o mapa tiver $10.000$ incidentes cadastrados, uma busca ingênua precisa calcular a distância de todos os $10.000$ pontos até o usuário. Isso é $O(n)$ por movimento de tela ou clique. Em um servidor com múltiplos usuários, isso trava o sistema.
2. **A Solução com Quadtree:** O mapa de São Paulo (`lat: [-23.70, -23.45], lon: [-46.80, -46.45]`) é tratado como um plano 2D. A Quadtree subdivide recursivamente o retângulo delimitador (`BoundingBox`) em 4 quadrantes: **Noroeste (NW)**, **Nordeste (NE)**, **Sudoeste (SW)** e **Sudeste (SE)**.
3. **Parâmetros da Árvore:**
   - `capacity = 4`: cada nó folha armazena até 4 pontos. Ao receber o 5º ponto, o nó se divide em 4 filhos e redistribui seus pontos.
   - `max_depth = 10`: impede recursão infinita caso várias pessoas reportem incidentes na mesma coordenada GPS exata (no nível 10, a folha aceita pontos adicionais sem subdividir).
4. **Range Query (Busca por Raio com Poda):**
   - Dada a localização do usuário e um raio $R$ (ex: $2.000\text{ m}$), calculamos a `BoundingBox` retangular que circunscreve esse círculo.
   - Na travessia da árvore, se a `BoundingBox` de um quadrante **não intersecta** a caixa de busca, **o ramo inteiro é descartado sem olhar nenhum ponto** (poda espacial).
   - A fórmula de **Haversine** (distância esférica exata da Terra, $R = 6.371\text{ km}$) só é calculada para os poucos pontos sobreviventes das folhas visitadas.
   - **Complexidade:** $O(\log n)$ no caso médio. Na interface, mostramos que a Quadtree economiza até **90% a 98% dos cálculos de distância**.
5. **Merge Dinâmico (Colapso de Nós na Remoção):**
   - Quando um incidente expira, a Quadtree remove o ponto.
   - Se os 4 quadrantes irmãos forem folhas e a soma dos pontos de todos eles for $\le 4$, o nó pai **funde de volta os 4 filhos em uma única folha**. Isso evita vazamento de memória e previne que a árvore fique esparsa e cheia de nós vazios.

#### 🎯 Perguntas Prováveis da Banca e Como Responder:
> **Professor:** *"Por que você usou Quadtree em vez de calcular a distância de tudo num loop for?"*  
> **Sua resposta:** *"Porque o loop for tem complexidade $O(n)$, o que não escala com milhares de alertas. A Quadtree reduz o espaço de busca descartando regiões inteiras do mapa por poda retangular, atingindo complexidade média $O(\log n)$. No nosso painel de telemetria ao vivo, provamos que para 500 alertas, a Quadtree visita menos de 10 nós e faz menos de 20 cálculos de Haversine, enquanto a busca linear precisa fazer 500."*

> **Professor:** *"O que acontece na sua Quadtree se 10 pessoas registrarem um crime exatamente no mesmo ponto de ônibus?"*  
> **Sua resposta:** *"Implementamos uma proteção de `max_depth = 10`. Sem ela, a Quadtree tentaria subdividir infinitamente porque os pontos nunca se separariam entre os quadrantes, estourando a pilha de recursão. Ao atingir a profundidade 10, o nó folha aceita acumular os pontos adicionais sem subdividir."*

> **Professor:** *"O que é o Merge que vocês implementaram?"*  
> **Sua resposta:** *"É o processo inverso da subdivisão. Quando alertas expiram e são removidos, nós folha podem ficar com 0 ou 1 elemento. Nossa função `_try_merge` sobe a árvore verificando se a soma dos 4 irmãos é menor ou igual à capacidade (4). Se for, eliminamos os 4 filhos e guardamos os pontos no pai, desfragmentando a árvore em tempo real."*

---

### 👤 Integrante 2: O Motor Temporal e Indexação (Min-Heap & Hash Table)
**Responsabilidade:** Explicar o decaimento temporal, a Indexed Min-Heap, o tratamento de colisões com Tombstones e a garantia matemática do $\alpha \le 0.50$.

#### O que você precisa dominar:
1. **Por que uma Fila Comum (FIFO / Deque) NÃO servia:**
   - Em uma fila comum, os itens só podem sair na mesma ordem em que entraram.
   - No nosso sistema, o tempo de vida (TTL) é **dinâmico**:
     - Assalto: base de 48h.
     - Furto: base de 24h.
     - Via Perigosa: base de 36h.
     - **Cada Upvote adiciona +2h de vida.** Um assalto postado ontem pode receber 5 upvotes e expirar depois de um furto postado hoje! Por isso, uma **Min-Heap** ordenada por `expires_at` é a única estrutura correta.
2. **Indexed Min-Heap ($O(\log n)$ em Upvotes):**
   - O incidente que vai expirar primeiro fica sempre no topo: `heap[0]` acessível em $O(1)$.
   - Em uma Heap tradicional, achar um elemento pelo ID para dar Upvote custa $O(n)$ de varredura linear.
   - **Nosso diferencial técnico:** Implementamos uma `IndexedMinHeap`. Ela mantém uma instância da nossa `HashTable` mapeando `id -> indice_no_array`. A cada `swap` de nós na árvore, atualizamos a posição na hash. Assim, achar o incidente custa $O(1)$ e ajustar sua nova prioridade após o upvote (`sift_down`) custa estritamente $O(\log n)$.
3. **HashTable com Endereçamento Aberto (Open Addressing):**
   - Não usamos listas encadeadas para economizar memória e garantir **localidade de cache de CPU** (um único array contíguo).
   - **Sondagem Quadrática:** Em caso de colisão, calculamos a posição com $h(k, i) = (h(k) + i^2) \bmod m$.
4. **O Mecanismo de TOMBSTONE:**
   - Quando um alerta expira e é removido da Hash Table, **não podemos colocar `None` no slot**. Se colocássemos `None`, a busca por chaves que colidiram anteriormente e foram parar nos slots seguintes seria interrompida prematuramente!
   - Por isso, marcamos o slot com o sentinela `TOMBSTONE`. Buscas continuam atravessando tombstones, e novas inserções podem reaproveitar o slot.
5. **Garantia Matemática do Rehashing com $\alpha > 0.50$:**
   - O teorema clássico da sondagem quadrática prova que se a capacidade $m$ for um **número primo** e o fator de carga $\alpha \le 0.50$, **a sondagem tem garantia de visitar pelo menos $(m+1)/2$ slots distintos sem entrar em loop infinito**.
   - Por isso, nosso rehashing dispara estritamente quando `(tamanho + tombstones) / capacidade > 0.50`, dobrando para o próximo número primo e limpando todas as `TOMBSTONE`s de uma vez só.

#### 🎯 Perguntas Prováveis da Banca e Como Responder:
> **Professor:** *"Por que vocês usaram Min-Heap e não uma Fila simples para remover alertas antigos?"*  
> **Sua resposta:** *"Porque a ordem de expiração não é FIFO (First-In, First-Out). Cada tipo de crime tem um TTL base diferente e, além disso, usuários podem dar Upvotes que aumentam a vida útil do alerta em +2 horas. A Min-Heap garante que o próximo alerta a expirar está sempre na raiz `heap[0]` em tempo $O(1)$, independentemente da ordem em que foram cadastrados."*

> **Professor:** *"Por que vocês usaram TOMBSTONE na Hash Table em vez de simplesmente esvaziar o slot?"*  
> **Sua resposta:** *"Como usamos Endereçamento Aberto com Sondagem Quadrática, quando duas chaves colidem, a segunda chave é armazenada passos à frente. Se esvaziássemos o slot da primeira chave com `None`, o método `get` interpretaria o slot vazio como 'chave inexistente' e abortaria a busca, quebrando a cadeia e tornando a segunda chave inacessível. O `TOMBSTONE` avisa a busca para continuar caminhando."*

> **Professor:** *"Por que o Rehashing dispara em 0.50 e não em 0.75 ou 0.90?"*  
> **Sua resposta:** *"Por uma garantia matemática da Sondagem Quadrática: se a tabela tiver tamanho primo $m$ e fator de ocupação $\le 0.50$, o algoritmo prova que sempre haverá pelo menos $(m+1)/2$ posições livres visitáveis sem repetição. Se deixássemos passar de 0.50, a sondagem quadrática poderia entrar em ciclo sem encontrar slot livre."*

---

### 👤 Integrante 3: O Motor de Grafos e Persistência (Grid Graph, BFS & SQLite)
**Responsabilidade:** Explicar a discretização do espaço, o algoritmo BFS de componentes conectados para Zonas Vermelhas, os pesos de gravidade e a durabilidade dos dados.

#### O que você precisa dominar:
1. **A Discretização em Grade (Grid Graph 30x30):**
   - O retângulo de São Paulo é particionado em uma malha de $30 \times 30$ células (total de 900 vértices/células).
   - O mapeamento de coordenada GPS `(lat, lon)` para a célula `(linha, coluna)` é uma operação aritmética imediata em $O(1)$:
     $$\text{linha} = \left\lfloor \frac{\text{lat} - \min\text{lat}}{\text{altura\_célula}} \right\rfloor, \quad \text{coluna} = \left\lfloor \frac{\text{lon} - \min\text{lon}}{\text{largura\_célula}} \right\rfloor$$
2. **Pesos de Risco Cumulativos:**
   - Cada tipo de crime injeta uma pontuação na célula:
     - Assalto à mão armada: **+5 pontos**
     - Furto: **+3 pontos**
     - Via Perigosa: **+2 pontos**
   - Ao expirar ou ser removido, o incidente deduz exatamente o seu peso em $O(1)$.
3. **Detecção de Zonas Vermelhas via BFS (Busca em Largura):**
   - **Limiar de Risco (*Threshold*):** Qualquer célula com pontuação acumulada $\ge 10$ pontos é considerada "Célula Quente".
   - **Algoritmo de Componentes Conectados (Flood Fill):**
     - O sistema percorre a grade. Ao encontrar uma célula quente não visitada, inicia uma **Busca em Largura (BFS)** usando uma fila FIFO.
     - Avaliamos a vizinhança de **8 direções** (norte, sul, leste, oeste e as 4 diagonais).
     - Todas as células quentes vizinhas são agrupadas no mesmo cluster de perigo contínuo.
     - O resultado é desenhado na tela como um polígono vermelho translúcido destacando a mancha de criminalidade da região.
4. **Complexidade do Grafo:**
   - Como o número de vértices é $V = 900$ e cada vértice tem no máximo 8 arestas ($E \le 8V$), o BFS roda em $O(V + E)$, o que leva menos de **1 milissegundo** na CPU, permitindo recálculo instantâneo a cada avanço no tempo.
5. **Persistência SQLite:**
   - Usamos SQLite nativo com índices por `expires_at`.
   - Ao iniciar o servidor, o banco reidrata as 4 estruturas em memória de forma consistente.

#### 🎯 Perguntas Prováveis da Banca e Como Responder:
> **Professor:** *"Como vocês usaram Grafos se o sistema não calcula rotas?"*  
> **Sua resposta:** *"Modelamos o espaço como um Grid Graph 2D onde cada célula é um vértice conectado aos seus 8 vizinhos geográficos. Usamos o algoritmo de Busca em Largura (BFS) para encontrar Componentes Conectados de risco. Quando várias células vizinhas ultrapassam 10 pontos de criminalidade, o BFS agrupa essas células em uma 'Zona Vermelha' única no mapa."*

> **Professor:** *"Qual é a complexidade do algoritmo BFS que vocês usaram?"*  
> **Sua resposta:** *"A complexidade de tempo é $O(V + E)$. Como nossa grade é de $30 \times 30$, temos $V = 900$ células e cada uma tem no máximo 8 vizinhos ($E \le 7200$). Na prática, o algoritmo só visita as células que atingiram o limiar de 10 pontos, executando em frações de milissegundo."*

> **Professor:** *"O que acontece com a pontuação do grafo quando um assalto expira?"*  
> **Sua resposta:** *"A fachada `AlertEngine` aciona a função `remove_incident` do `GridGraph`, que deduz os 5 pontos daquela célula em $O(1)$. Se a pontuação da célula cair abaixo de 10, ela deixa de ser quente e a Zona Vermelha encolhe ou desaparece no próximo ciclo do BFS."*

---

### 👤 Integrante 4: Integração, API REST & Visualização Acadêmica
**Responsabilidade:** Explicar a orquestração do `AlertEngine`, a telemetria comparativa ao vivo, a interface gráfica e conduzir a demonstração prática.

#### O que você precisa dominar:
1. **O Orquestrador `AlertEngine` (Fachada Única):**
   - Centraliza todas as mutações para manter as 4 estruturas perfeitamente sincronizadas.
   - Quando um usuário clica em "Reportar Incidente", uma única chamada insere o dado atomicamente na `HashTable`, na `IndexedMinHeap`, na `Quadtree`, no `GridGraph` e no `SQLite`.
2. **Telemetria de Comparação de Bancada ($O(\log n)$ vs. $O(n)$):**
   - A cada clique no mapa para busca por raio, o backend executa **duas buscas em paralelo**:
     1. Na **Quadtree**: registra nós visitados, cálculos de Haversine e tempo em ms.
     2. Na **Lista Linear $O(n)$**: percorre todos os incidentes ativos calculando Haversine para todos.
   - A interface exibe lado a lado o comparativo: tempo em ms, cálculos executados e percentual de operações economizadas pela Quadtree (geralmente acima de **90%**).
3. **Interface Visual Anti-Slop (Padrão de Engenharia de Software):**
   - Implementada com Leaflet.js e CSS customizado seguindo diretrizes rígidas de design de ferramentas técnicas (como Figma e Linear): tela única `100svh`, tipografia monoespaçada tabular (`tabular-nums` para que os números não tremam ao atualizar) e zero cores desnecessárias (zero violeta).
   - Toggles visuais no topo do mapa permitem ligar e desligar:
     - Marcadores de crimes com cores semânticas de decaimento (Vermelho = Crítico, Âmbar = Moderado, Verde = Baixo).
     - Retângulos ciano das subdivisões da **Quadtree**.
     - Polígonos vermelhos das **Zonas Vermelhas (BFS)**.
4. **Mecanismo de "Time Travel" (Simulação Cronológica):**
   - Na banca, o professor não vai esperar 24 horas para ver um alerta sumir.
   - Criamos os botões **"Avançar +1h"** e **"Avançar +6h"** na barra superior. Ao clicar, o relógio virtual avança, a Heap expulsa os expirados, a Quadtree faz o merge dos quadrantes vazios e o Grafo dissolve as Zonas Vermelhas ao vivo.

#### 🎯 Perguntas Prováveis da Banca e Como Responder:
> **Professor:** *"Como vocês provam que a Quadtree é realmente mais rápida que a busca comum?"*  
> **Sua resposta:** *"Colocamos um comparador empírico em tempo real no painel lateral. A cada clique no mapa, o backend mede o tempo e o número de cálculos de distância feitos pela Quadtree versus uma varredura linear completa. Com apenas 120 alertas, a busca linear faz 120 cálculos enquanto a Quadtree faz menos de 10. Se injetarmos 500 ou 1000 alertas pelo nosso botão de teste de estresse, a busca linear aumenta linearmente enquanto a Quadtree se mantém quase estável em tempo logarítmico."*

> **Professor:** *"O que acontece na interface se o usuário der um Upvote em um alerta?"*  
> **Sua resposta:** *"Ao clicar em 'Confirmar / Upvote (+2h)', o backend recupera o alerta na Hash Table em $O(1)$, soma 2 horas no TTL e chama `update_expiration` na Min-Heap em $O(\log n)$. O alerta ganha sobrevida, seu nível de decaimento volta para Crítico e ele não é removido no próximo avanço de tempo."*

---

## 3. Roteiro de Demonstração ao Vivo na Apresentação (Passo a Passo de 8 Minutos)

Siga este roteiro na hora de projetar a tela para o professor:

1. **Passo 1 — Apresentação Inicial (1 min):**
   - Abra o navegador em `http://localhost:8000`.
   - Mostre o mapa de São Paulo carregado com o tema escuro técnico.
   - Aponte os 4 cards no painel lateral: **Comparador**, **Quadtree**, **Min-Heap**, **Hash Table** e **Grid Graph**.

2. **Passo 2 — Demonstração da Quadtree e Poda Espacial (2 min):**
   - Mostre as linhas em ciano no mapa: explique que são os quadrantes reais da Quadtree que se subdividiram onde há concentração de crimes.
   - Clique na região da Sé ou Avenida Paulista.
   - Mostre o painel do Comparador atualizando instantaneamente: aponte a economia de cálculos (ex: *"Vejam professor, a lista linear calculou 120 distâncias, mas a Quadtree visitou apenas 6 nós e calculou 8 distâncias — 93% de economia!"*).

3. **Passo 3 — Teste de Estresse da Quadtree (1 min):**
   - Clique no botão **"+500 Incidentes"** na barra superior.
   - Veja o mapa preencher com centenas de novos pontos e a Quadtree se subdividir automaticamente em novos quadrantes menores.
   - Clique no mapa novamente e mostre que a Quadtree continua respondendo em menos de 1 milissegundo, enquanto o contador linear subiu para mais de 600 cálculos.

4. **Passo 4 — Zonas Vermelhas e BFS no Grafo (1.5 min):**
   - Mostre os polígonos vermelhos tracejados no mapa: explique que foram gerados pelo algoritmo **BFS de Componentes Conectados** no Grid Graph $30 \times 30$, agrupando células adjacentes com score $\ge 10$.
   - Clique em uma Zona Vermelha para exibir o popup com os pontos de gravidade acumulados.

5. **Passo 5 — Time Travel, Decaimento (Decay) e Merge da Quadtree (2 min):**
   - Aponte para o card da **Indexed Min-Heap** no sidebar: mostre o ID e o horário do próximo alerta prestes a expirar no topo `heap[0]`.
   - Clique no botão **"Avançar +6h"** (ou repita duas vezes).
   - Mostre o que acontece ao vivo:
     - O relógio virtual avança.
     - Dezenas de alertas expiram e somem do mapa.
     - Observe os quadrantes ciano da Quadtree: onde os pontos sumiram, os 4 filhos sofreram **Merge (colapso)** voltando a ser um quadrado grande!
     - As Zonas Vermelhas do Grafo diminuem de tamanho ou se dissolvem.

6. **Passo 6 — Upvote e Conclusão (0.5 min):**
   - Clique em um pino que esteja com status "MODERADO" ou "BAIXO".
   - Clique no botão **"Confirmar / Upvote (+2h de vida)"**.
   - Mostre que o pino ganha sobrevida, seu nível volta a "CRÍTICO" e sua posição na Min-Heap é recalculada em $O(\log n)$.
   - Finalize destacando que todas as 4 estruturas foram implementadas sem bibliotecas prontas.

---

## 4. Comandos Essenciais para Rodar no Dia

```powershell
# 1. Rodar os testes automatizados para provar a corretude à banca
python -m pytest tests/ -v

# 2. Iniciar o servidor da aplicação
uvicorn src.api.app:app --reload --port 8000

# 3. Acessar no navegador
http://localhost:8000
```
