"""Gerador de dados realistas de incidentes nos principais bairros de São Paulo."""

import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import List
from src.core.models import Incidente, TipoIncidente

# Centros aproximados de bairros e regiões de São Paulo (Lat, Lon)
PONTOS_NOTAVEIS_SP = [
    ("Praça da Sé / Centro", -23.5505, -46.6333),
    ("Avenida Paulista / Bela Vista", -23.5614, -46.6559),
    ("Pinheiros / Faria Lima", -23.5670, -46.6930),
    ("Itaquera / Zona Leste", -23.5410, -46.4520),
    ("Santo Amaro / Zona Sul", -23.6520, -46.7050),
    ("Vila Mariana", -23.5890, -46.6380),
    ("Tatuapé", -23.5400, -46.5760),
    ("Lapa / Zona Oeste", -23.5220, -46.7030),
    ("Santana / Zona Norte", -23.5040, -46.6260),
    ("Mooca", -23.5560, -46.5980),
    ("República / Santa Ifigênia", -23.5430, -46.6380),
    ("Vila Madalena", -23.5550, -46.6910),
]

TITULOS_EXEMPLO = {
    TipoIncidente.ASSALTO: [
        "Assalto a transeunte com arma de fogo",
        "Abordagem por dois indivíduos em moto",
        "Roubo de celular no ponto de ônibus",
        "Assalto na saída da estação de metrô",
    ],
    TipoIncidente.FURTO: [
        "Furto de celular por distração",
        "Furto de estepe e pertences de veículo",
        "Furto de bicicleta presa em paraciclo",
        "Bolsa aberta e carteira levada em aglomeração",
    ],
    TipoIncidente.VIA_PERIGOSA: [
        "Rua totalmente sem iluminação pública há dias",
        "Ponto cego com baixa visibilidade e pedestres vulneráveis",
        "Trecho com histórico frequente de emboscadas noturnas",
        "Falta de sinalização e calçada danificada em rua deserta",
    ],
}


def generate_realistic_incidents(count: int, base_time: datetime, seed: int = 42) -> List[Incidente]:
    """
    Gera uma lista de incidentes com distribuição realista ao redor de pontos notáveis
    de São Paulo, com pequenas variações gaussianas de coordenadas.
    """
    rng = random.Random(seed)
    tipos = [TipoIncidente.ASSALTO, TipoIncidente.FURTO, TipoIncidente.VIA_PERIGOSA]
    pesos_tipo = [0.45, 0.40, 0.15]  # Assaltos e furtos são mais frequentes

    incidentes: List[Incidente] = []

    for i in range(count):
        bairro, b_lat, b_lon = rng.choice(PONTOS_NOTAVEIS_SP)
        # Desvio gaussiano de aprox. 300m a 1km ao redor do ponto do bairro
        lat = b_lat + rng.gauss(0, 0.007)
        lon = b_lon + rng.gauss(0, 0.007)

        tipo = rng.choices(tipos, weights=pesos_tipo, k=1)[0]
        titulo = rng.choice(TITULOS_EXEMPLO[tipo]) + f" ({bairro})"

        # Criado nas últimas 12 horas antes do base_time
        horas_atras = rng.uniform(0.5, 12.0)
        created_at = base_time - timedelta(hours=horas_atras)

        # TTL base mais bônus aleatório de upvotes iniciais
        upvotes_iniciais = rng.randint(0, 4)
        ttl_horas = tipo.ttl_base_horas + (upvotes_iniciais * 2)
        expires_at = created_at + timedelta(hours=ttl_horas)

        inc = Incidente(
            id=f"sp-{uuid.uuid4().hex[:8]}",
            tipo=tipo,
            latitude=round(lat, 6),
            longitude=round(lon, 6),
            created_at=created_at,
            expires_at=expires_at,
            upvotes=upvotes_iniciais,
            usuario_id=f"cidadao_{rng.randint(10, 99)}",
            titulo=titulo,
            descricao=f"Relato registrado pela comunidade próximo a {bairro}.",
        )
        incidentes.append(inc)

    return incidentes

