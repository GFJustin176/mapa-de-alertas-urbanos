"""Camada de persistência relacional local baseada em SQLite3."""

import sqlite3
from datetime import datetime, timezone
from typing import List, Optional
from src.core.models import Incidente, TipoIncidente


class DatabaseStorage:
    """Repositório SQLite para armazenamento durável de incidentes e reidratação em memória."""

    def __init__(self, db_path: str = "mapa_alertas.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Cria as tabelas necessárias caso ainda não existam."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS incidentes (
                    id TEXT PRIMARY KEY,
                    tipo TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    upvotes INTEGER NOT NULL DEFAULT 0,
                    usuario_id TEXT NOT NULL DEFAULT 'anonimo',
                    titulo TEXT,
                    descricao TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON incidentes(expires_at)")
            conn.commit()

    def save_incident(self, inc: Incidente) -> None:
        """Salva ou atualiza um incidente no banco de dados."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO incidentes (
                    id, tipo, latitude, longitude, created_at, expires_at, upvotes, usuario_id, titulo, descricao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                inc.id,
                inc.tipo.value,
                inc.latitude,
                inc.longitude,
                inc.created_at.isoformat(),
                inc.expires_at.isoformat(),
                inc.upvotes,
                inc.usuario_id,
                inc.titulo,
                inc.descricao,
            ))
            conn.commit()

    def update_incident_upvotes_and_expiration(self, incidente_id: str, upvotes: int, expires_at: datetime) -> None:
        """Atualiza a contagem de upvotes e a nova data de expiração no banco relacional."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE incidentes
                SET upvotes = ?, expires_at = ?
                WHERE id = ?
            """, (upvotes, expires_at.isoformat(), incidente_id))
            conn.commit()

    def delete_incident(self, incidente_id: str) -> None:
        """Remove o incidente do banco relacional após expiração confirmada."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM incidentes WHERE id = ?", (incidente_id,))
            conn.commit()

    def load_by_id(self, incidente_id: str) -> Optional[Incidente]:
        """Carrega um incidente por ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM incidentes WHERE id = ?", (incidente_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_incident(row)
        return None

    def load_all_active(self, current_time: datetime) -> List[Incidente]:
        """Carrega todos os incidentes que ainda não expiraram em relação ao tempo fornecido."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM incidentes WHERE expires_at > ? ORDER BY expires_at ASC",
                (current_time.isoformat(),),
            )
            rows = cursor.fetchall()
            return [self._row_to_incident(r) for r in rows]

    def clear_all(self) -> None:
        """Limpa todos os registros do banco de dados (usado para testes e resets)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM incidentes")
            conn.commit()

    @staticmethod
    def _row_to_incident(row: sqlite3.Row) -> Incidente:
        return Incidente(
            id=row["id"],
            tipo=TipoIncidente(row["tipo"]),
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            upvotes=int(row["upvotes"]),
            usuario_id=row["usuario_id"],
            titulo=row["titulo"],
            descricao=row["descricao"],
        )

