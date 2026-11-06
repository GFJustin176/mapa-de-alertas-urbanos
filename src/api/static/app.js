/* Aplicação Frontend Sentinela SP - Controle do Mapa Leaflet e Telemetria */

// Estado da aplicação
let map;
let quadtreeLayer;
let redzonesLayer;
let incidentsLayer;
let searchLayer;
let currentRadiusMeters = 2000;
let lastSearchCenter = null;

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  setupEventListeners();
  refreshState();
});

function initMap() {
  // Centro de São Paulo (Praça da Sé)
  const spCenter = [-23.5505, -46.6333];

  map = L.map("map-viewport", {
    center: spCenter,
    zoom: 12,
    minZoom: 10,
    maxZoom: 18,
    zoomControl: false,
  });

  // Reposiciona o controle de zoom para o canto inferior esquerdo
  L.control.zoom({ position: "bottomleft" }).addTo(map);

  // Camada de tiles gratuita sem necessidade de chave de API (OpenStreetMap padrão)
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);

  // Inicializa os grupos de camadas
  quadtreeLayer = L.layerGroup().addTo(map);
  redzonesLayer = L.layerGroup().addTo(map);
  incidentsLayer = L.layerGroup().addTo(map);
  searchLayer = L.layerGroup().addTo(map);

  // Evento de clique no mapa
  map.on("click", (e) => {
    const lat = e.latlng.lat;
    const lon = e.latlng.lng;
    lastSearchCenter = { lat, lon };

    // Atualiza os inputs do modal caso esteja visível
    document.getElementById("input-lat").value = lat.toFixed(6);
    document.getElementById("input-lon").value = lon.toFixed(6);

    // Dispara a busca espacial no raio configurado
    executeRadiusSearch(lat, lon, currentRadiusMeters);
  });
}

function setupEventListeners() {
  // Toggles de camadas
  document.getElementById("toggle-incidents").addEventListener("change", (e) => {
    if (e.target.checked) map.addLayer(incidentsLayer);
    else map.removeLayer(incidentsLayer);
  });

  document.getElementById("toggle-quadtree").addEventListener("change", (e) => {
    if (e.target.checked) map.addLayer(quadtreeLayer);
    else map.removeLayer(quadtreeLayer);
  });

  document.getElementById("toggle-redzones").addEventListener("change", (e) => {
    if (e.target.checked) map.addLayer(redzonesLayer);
    else map.removeLayer(redzonesLayer);
  });

  document.getElementById("select-radius").addEventListener("change", (e) => {
    currentRadiusMeters = parseFloat(e.target.value);
    if (lastSearchCenter) {
      executeRadiusSearch(lastSearchCenter.lat, lastSearchCenter.lon, currentRadiusMeters);
    }
  });

  // Ações de Time Travel e Simulação
  document.getElementById("btn-time-1h").addEventListener("click", () => advanceSimulationTime(1.0));
  document.getElementById("btn-time-6h").addEventListener("click", () => advanceSimulationTime(6.0));
  document.getElementById("btn-inject-seed").addEventListener("click", () => injectBulkIncidents(500));
  document.getElementById("btn-reset-sim").addEventListener("click", () => resetSimulation(120));

  // Modal de cadastro
  const modal = document.getElementById("modal-report");
  document.getElementById("btn-open-report").addEventListener("click", () => {
    modal.classList.add("active");
    if (!document.getElementById("input-lat").value) {
      document.getElementById("input-lat").value = "-23.550500";
      document.getElementById("input-lon").value = "-46.633300";
    }
  });

  document.getElementById("btn-close-modal").addEventListener("click", () => {
    modal.classList.remove("active");
  });

  document.getElementById("form-report").addEventListener("submit", async (e) => {
    e.preventDefault();
    const success = await submitNewIncident();
    if (success) {
      modal.classList.remove("active");
      document.getElementById("input-titulo").value = "";
      document.getElementById("input-desc").value = "";
    }
  });
}

async function refreshState() {
  try {
    const res = await fetch("/api/state");
    const data = await res.json();
    renderState(data);
  } catch (err) {
    console.error("Erro ao atualizar o estado da aplicação:", err);
  }
}

function renderState(data) {
  // 1. Relógio virtual
  const dateObj = new Date(data.current_time);
  document.getElementById("clock-display").textContent = dateObj.toUTCString();

  // 2. Renderizar Quadrantes da Quadtree
  quadtreeLayer.clearLayers();
  if (data.quadtree && data.quadtree.quadrants) {
    data.quadtree.quadrants.forEach((q) => {
      const bounds = [
        [q.min_lat, q.min_lon],
        [q.max_lat, q.max_lon],
      ];
      const isLeaf = !q.is_divided;
      L.rectangle(bounds, {
        color: "#2E90FA",
        weight: isLeaf ? 1 : 1.5,
        fillColor: "#2E90FA",
        fillOpacity: isLeaf ? 0.04 : 0.01,
        dashArray: isLeaf ? "2, 3" : undefined,
      }).addTo(quadtreeLayer);
    });
  }

  // 3. Renderizar Zonas Vermelhas (BFS Grid Graph)
  redzonesLayer.clearLayers();
  if (data.grid_graph && data.grid_graph.red_zones) {
    data.grid_graph.red_zones.forEach((rz) => {
      const bounds = [
        [rz.min_lat, rz.min_lon],
        [rz.max_lat, rz.max_lon],
      ];
      L.rectangle(bounds, {
        color: "#E5484D",
        weight: 2,
        fillColor: "#E5484D",
        fillOpacity: 0.22,
        dashArray: "4, 4",
      })
      .bindPopup(`
        <div style="font-family: var(--font-ui);">
          <div style="font-weight: 700; color: #E5484D; font-size: 13px;">Zona Vermelha (Cluster BFS)</div>
          <div style="font-size: 12px; margin-top: 4px;">Gravidade Acumulada: <b>${rz.total_score} pts</b></div>
          <div style="font-size: 12px;">Células Conectadas: <b>${rz.cells_count}</b></div>
          <div style="font-size: 12px;">Total de Incidentes: <b>${rz.incident_count}</b></div>
        </div>
      `)
      .addTo(redzonesLayer);
    });
  }

  // 4. Renderizar Marcadores de Incidentes
  incidentsLayer.clearLayers();
  if (data.incidents) {
    data.incidents.forEach((inc) => {
      let markerColor = "#E5484D"; // Crítico
      if (inc.nivel_alerta === "MODERADO") markerColor = "#F5A623";
      if (inc.nivel_alerta === "BAIXO") markerColor = "#30A46C";

      const circle = L.circleMarker([inc.latitude, inc.longitude], {
        radius: 6,
        fillColor: markerColor,
        color: "#0E1013",
        weight: 1.5,
        opacity: 1,
        fillOpacity: 0.9,
      });

      const safeTitulo = escapeHtml(inc.titulo || inc.tipo);
      const safeDesc = escapeHtml(inc.descricao || '');
      const popupContent = `
        <div style="font-family: var(--font-ui); min-width: 220px;">
          <div class="popup-title">${safeTitulo}</div>
          <div class="popup-desc">${safeDesc}</div>
          <div style="display: flex; gap: 6px; align-items: center; margin-bottom: 8px;">
            <span class="badge-nivel badge-${inc.nivel_alerta}">${inc.nivel_alerta}</span>
            <span style="font-size: 11px; color: var(--muted); font-family: var(--font-mono);">${inc.upvotes} confirmações</span>
          </div>
          <div class="popup-meta">
            Expira em: ${new Date(inc.expires_at).toLocaleTimeString()}<br>
            ID: ${escapeHtml(inc.id)}
          </div>
          <button class="btn btn-secondary" style="width: 100%; justify-content: center; font-size: 11px; padding: 5px 8px;" onclick="upvoteIncident('${escapeHtml(inc.id)}')">
            &#9650; Confirmar / Upvote (+2h de vida)
          </button>
        </div>
      `;

      circle.bindPopup(popupContent);
      circle.addTo(incidentsLayer);
    });
  }

  // 5. Atualizar Indicadores dos Cards Laterais
  // Quadtree
  document.getElementById("qt-total-points").textContent = data.quadtree ? data.quadtree.total_points : 0;
  document.getElementById("qt-quadrants-count").textContent = data.quadtree && data.quadtree.quadrants ? data.quadtree.quadrants.length : 0;

  // Min-Heap
  document.getElementById("heap-size").textContent = data.min_heap ? data.min_heap.size : 0;
  if (data.min_heap && data.min_heap.next_to_expire) {
    const next = data.min_heap.next_to_expire;
    document.getElementById("heap-next-id").textContent = next.id;
    document.getElementById("heap-next-time").textContent = new Date(next.expires_at).toLocaleTimeString();
  } else {
    document.getElementById("heap-next-id").textContent = "Nenhum";
    document.getElementById("heap-next-time").textContent = "--";
  }

  // Hash Table
  if (data.hash_table) {
    const ht = data.hash_table;
    document.getElementById("ht-load-val").textContent = `${ht.load_factor.toFixed(3)} / 0.50`;
    const pct = Math.min(100, Math.round((ht.load_factor / 0.50) * 100));
    document.getElementById("ht-progress-fill").style.width = `${pct}%`;
    document.getElementById("ht-capacity").textContent = ht.capacity;
    document.getElementById("ht-size").textContent = ht.size;
    document.getElementById("ht-tombstones").textContent = ht.tombstones;
    document.getElementById("ht-rehashes").textContent = ht.rehash_count;
  }

  // Grid Graph
  if (data.grid_graph) {
    const gg = data.grid_graph;
    document.getElementById("gg-active-cells").textContent = gg.active_cells ? gg.active_cells.length : 0;
    document.getElementById("gg-redzones-count").textContent = gg.red_zones_count || 0;
  }
}

async function executeRadiusSearch(lat, lon, radiusMeters) {
  try {
    const res = await fetch(`/api/search?lat=${lat}&lon=${lon}&radius_m=${radiusMeters}`);
    const data = await res.json();

    // Desenhar círculo de raio e destaque visual
    searchLayer.clearLayers();

    L.circle([lat, lon], {
      radius: radiusMeters,
      color: "#2E90FA",
      weight: 2,
      fillColor: "#2E90FA",
      fillOpacity: 0.12,
    }).addTo(searchLayer);

    L.circleMarker([lat, lon], {
      radius: 5,
      color: "#2E90FA",
      fillColor: "#fff",
      fillOpacity: 1,
    }).addTo(searchLayer);

    // Atualizar o comparador de performance no sidebar
    const tel = data.telemetry;
    document.getElementById("metric-quad-calcs").textContent = `${tel.quadtree_calcs} calcs`;
    document.getElementById("metric-quad-ms").textContent = `${tel.quadtree_ms} ms`;

    document.getElementById("metric-linear-calcs").textContent = `${tel.linear_calcs} calcs`;
    document.getElementById("metric-linear-ms").textContent = `${tel.linear_ms} ms`;

    document.getElementById("metric-pruning-pct").textContent = `${tel.pruning_ratio_percent}%`;
    document.getElementById("metric-nodes-visited").textContent = `${tel.quadtree_nodes_visited} nós`;
    document.getElementById("metric-speedup").textContent = `${tel.speedup_factor}x mais rápido`;

    // Renderizar a lista textual de alertas no raio encontrado
    const container = document.getElementById("radius-incidents-container");
    const countBadge = document.getElementById("radius-incidents-count");
    const listEl = document.getElementById("radius-incidents-list");

    container.style.display = "block";
    const incidents = data.incidents || [];
    countBadge.textContent = `${incidents.length} no raio`;

    if (incidents.length === 0) {
      listEl.innerHTML = `<div style="font-size: 11px; color: var(--muted); padding: 8px 0;">Nenhum alerta ativo encontrado neste raio de ${(radiusMeters / 1000).toFixed(1)} km.</div>`;
    } else {
      listEl.innerHTML = incidents.map((inc) => {
        const distKm = (inc.distancia_metros / 1000).toFixed(2);
        const safeTitulo = escapeHtml(inc.titulo || inc.tipo);
        return `
          <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--line); border-radius: var(--r-input); padding: 8px; display: flex; flex-direction: column; gap: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: 600; font-size: 12px; color: var(--ink);">${safeTitulo}</span>
              <span class="badge-nivel badge-${inc.nivel_alerta}" style="font-size: 10px; padding: 1px 5px;">${inc.nivel_alerta}</span>
            </div>
            <div style="font-size: 11px; color: var(--muted); display: flex; justify-content: space-between;">
              <span>Aprox. <b>${inc.distancia_metros < 1000 ? Math.round(inc.distancia_metros) + ' m' : distKm + ' km'}</b> de distância</span>
              <span>${inc.upvotes} &bull; upvotes</span>
            </div>
          </div>
        `;
      }).join("");
    }

  } catch (err) {
    console.error("Erro na busca espacial por raio:", err);
  }
}

async function advanceSimulationTime(hours) {
  try {
    const res = await fetch("/api/simulate/time", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hours }),
    });
    const result = await res.json();
    console.log(`Tempo avançado em ${hours}h. Incidentes expirados: ${result.expired_count}`);
    await refreshState();
  } catch (err) {
    console.error("Erro ao avançar tempo:", err);
  }
}

async function injectBulkIncidents(count) {
  try {
    await fetch("/api/simulate/seed", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count }),
    });
    await refreshState();
  } catch (err) {
    console.error("Erro ao injetar incidentes:", err);
  }
}

async function resetSimulation(count) {
  try {
    await fetch("/api/simulate/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count }),
    });
    searchLayer.clearLayers();
    await refreshState();
  } catch (err) {
    console.error("Erro ao resetar simulação:", err);
  }
}

async function submitNewIncident() {
  const tipo = document.getElementById("input-tipo").value;
  const titulo = document.getElementById("input-titulo").value;
  const descricao = document.getElementById("input-desc").value;
  const latitude = parseFloat(document.getElementById("input-lat").value);
  const longitude = parseFloat(document.getElementById("input-lon").value);

  try {
    const res = await fetch("/api/incidents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tipo, titulo, descricao, latitude, longitude }),
    });
    if (res.ok) {
      await refreshState();
      map.setView([latitude, longitude], 14);
      return true;
    } else {
      const errData = await res.json();
      alert(`Erro: ${errData.detail || "Falha ao cadastrar"}`);
      return false;
    }
  } catch (err) {
    console.error("Erro ao enviar novo incidente:", err);
    return false;
  }
}

// Função global para upvote disparada do popup do Leaflet
window.upvoteIncident = async function(id) {
  try {
    const res = await fetch(`/api/incidents/${id}/upvote`, { method: "POST" });
    if (res.ok) {
      await refreshState();
      map.closePopup();
    } else {
      const err = await res.json();
      alert(`Não foi possível confirmar: ${err.detail || "Incidente não localizado."}`);
    }
  } catch (err) {
    console.error("Erro ao dar upvote:", err);
  }
};

