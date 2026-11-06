"""Servidor FastAPI expondo a API REST e a interface web estática do Sentinela SP."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.core.models import TipoIncidente
from src.engine import AlertEngine

# Diretórios estáticos
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Sentinela SP - Mapa de Alertas Urbanos",
    description="Plataforma de mapeamento colaborativo com Quadtree, Min-Heap, HashTable e GridGraph",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instância compartilhada do motor de estruturas de dados
_engine_instance: Optional[AlertEngine] = None


def get_engine() -> AlertEngine:
    global _engine_instance
    if _engine_instance is None:
        db_path = os.getenv("DATABASE_PATH", "mapa_alertas.db")
        _engine_instance = AlertEngine(db_path=db_path, auto_seed_count=120)
    return _engine_instance


# Modelos Pydantic para validação de entrada
class ReportIncidentRequest(BaseModel):
    tipo: TipoIncidente
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    usuario_id: str = "anonimo"


class AdvanceTimeRequest(BaseModel):
    hours: float = Field(..., gt=0)


class SeedRequest(BaseModel):
    count: int = Field(default=50, ge=1, le=5000)


@app.get("/")
def read_root():
    """Serve a aplicação web frontend em tela única."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return {"status": "ok", "message": "Frontend index.html não localizado ainda."}
    return FileResponse(index_file)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Evita log de erro 404 no console do navegador."""
    return Response(status_code=204)


@app.get("/api/state")
def get_state() -> Dict[str, Any]:
    """Retorna o estado global consolidado das 4 estruturas e incidentes ativos."""
    engine = get_engine()
    return engine.get_system_state()


@app.get("/api/search")
def search_incidents(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0),
    radius_m: float = Query(default=2000.0, gt=0, le=50000.0),
) -> Dict[str, Any]:
    """
    Executa a busca por raio combinando a Quadtree espacial com o comparativo
    de desempenho da busca linear tradicional.
    """
    engine = get_engine()
    return engine.search_radius(lat=lat, lon=lon, radius_meters=radius_m)


@app.post("/api/incidents", status_code=status.HTTP_201_CREATED)
def report_incident(payload: ReportIncidentRequest) -> Dict[str, Any]:
    """Cadastra um novo alerta urbano inserindo atomicamente nas 4 estruturas."""
    engine = get_engine()
    try:
        inc = engine.report_incident(
            tipo=payload.tipo,
            latitude=payload.latitude,
            longitude=payload.longitude,
            titulo=payload.titulo,
            descricao=payload.descricao,
            usuario_id=payload.usuario_id,
        )
        return {
            "id": inc.id,
            "tipo": inc.tipo.value,
            "latitude": inc.latitude,
            "longitude": inc.longitude,
            "created_at": inc.created_at.isoformat(),
            "expires_at": inc.expires_at.isoformat(),
            "upvotes": inc.upvotes,
            "titulo": inc.titulo,
            "descricao": inc.descricao,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/incidents/{incidente_id}/upvote")
def upvote_incident(incidente_id: str) -> Dict[str, Any]:
    """Confirma um incidente e estende seu tempo de vida útil (+2h), atualizando a Min-Heap em O(log n)."""
    engine = get_engine()
    try:
        updated = engine.upvote_incident(incidente_id, bonus_hours=2.0)
        return {
            "id": updated.id,
            "upvotes": updated.upvotes,
            "expires_at": updated.expires_at.isoformat(),
            "nivel_alerta": updated.calcular_nivel_alerta(engine.current_time),
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/simulate/time")
def simulate_time(payload: AdvanceTimeRequest) -> Dict[str, Any]:
    """Avança o relógio do sistema em X horas e purga alertas expirados (Decay)."""
    engine = get_engine()
    expired_count = engine.advance_time(payload.hours)
    return {
        "advanced_hours": payload.hours,
        "current_time": engine.current_time.isoformat(),
        "expired_count": expired_count,
        "active_incidents": len(engine),
    }


@app.post("/api/simulate/seed")
def simulate_seed(payload: SeedRequest) -> Dict[str, Any]:
    """Injeta incidentes adicionais em bairros reais de São Paulo para teste de carga."""
    engine = get_engine()
    injected = engine.inject_bulk(payload.count)
    return {
        "injected": injected,
        "total_active": len(engine),
    }


@app.post("/api/simulate/reset")
def simulate_reset(payload: SeedRequest) -> Dict[str, Any]:
    """Restaura o estado inicial do sistema com uma nova semente de dados."""
    engine = get_engine()
    engine.reset_simulation(seed_count=payload.count)
    return {
        "status": "reset",
        "total_active": len(engine),
        "current_time": engine.current_time.isoformat(),
    }


# Montagem dos arquivos estáticos para CSS e JS
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

