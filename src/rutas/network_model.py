"""Pesos de las aristas y estimación de memoria de la red (R1, puntos 1 y 2).

Spec: specs/R1-modelo-red.md (R1-B01 a R1-B10).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MPH_TO_KMH = 1.609344
MAX_PLAUSIBLE_KMH = 130.0
FALLBACK_SPEED_KMH = 30.0

# Velocidad por defecto según el tipo de vía de OSM (``highway``), en km/h.
# Criterio del grupo, acotado por los límites legales colombianos (citar la norma
# vigente en el documento técnico): 50 km/h como máximo en zona urbana y valores más
# bajos para vías de acceso. Ajustar aquí y en la spec si se cambia el criterio.
DEFAULT_SPEED_KMH: dict[str, float] = {
    "motorway": 80.0,
    "trunk": 80.0,
    "primary": 60.0,
    "secondary": 50.0,
    "tertiary": 40.0,
    "unclassified": 30.0,
    "residential": 30.0,
    "living_street": 20.0,
    "service": 20.0,
    "road": 30.0,
    "track": 20.0,
    "motorway_link": 50.0,
    "trunk_link": 40.0,
    "primary_link": 40.0,
    "secondary_link": 30.0,
    "tertiary_link": 30.0,
}

_NUMBER = re.compile(r"(\d+(?:\.\d+)?)")


def _parse_single_maxspeed(raw: str) -> float | None:
    match = _NUMBER.search(raw)
    if match is None:
        return None
    speed = float(match.group(1))
    if "mph" in raw.lower():
        speed *= MPH_TO_KMH
    if not 0 < speed <= MAX_PLAUSIBLE_KMH:  # R1-B10
        return None
    return speed


def parse_maxspeed(raw: str | list | None) -> float | None:
    """Interpreta la etiqueta ``maxspeed`` de OSM en km/h (R1-B08, R1-B10).

    Acepta ``"50"``, ``"50 km/h"``, ``"30 mph"`` o una lista de esos valores (OSMnx
    produce listas al simplificar tramos); de una lista se toma la mínima válida.
    Devuelve ``None`` si no hay un valor numérico plausible (por ejemplo ``"signals"``).
    """
    if raw is None:
        return None
    values = raw if isinstance(raw, list) else [raw]
    speeds = [s for s in (_parse_single_maxspeed(str(v)) for v in values) if s is not None]
    return min(speeds) if speeds else None


def edge_speed_kmh(maxspeed_raw: str | list | None, highway_raw: str | list | None) -> tuple[float, str]:
    """Velocidad del tramo y su origen: ``maxspeed``, ``highway_default`` o ``fallback``."""
    speed = parse_maxspeed(maxspeed_raw)
    if speed is not None:
        return speed, "maxspeed"

    highway_types = highway_raw if isinstance(highway_raw, list) else [highway_raw]
    for highway in highway_types:
        if highway in DEFAULT_SPEED_KMH:
            return DEFAULT_SPEED_KMH[highway], "highway_default"
    return FALLBACK_SPEED_KMH, "fallback"


def travel_time_s(length_m: float, speed_kmh: float) -> float:
    """Tiempo del modelo en segundos: distancia / velocidad (R1-B07)."""
    if speed_kmh <= 0:
        raise ValueError("La velocidad debe ser positiva")
    return length_m / (speed_kmh / 3.6)


@dataclass(frozen=True)
class MemoryEstimate:
    n_nodes: int
    n_edges: int
    matrix_mb: float
    lists_mb: float
    density: float          # E / V²: fracción de celdas de la matriz que tendrían una arista
    assumptions: str


def estimate_memory(
    n_nodes: int,
    n_edges: int,
    matrix_cell_bytes: int = 8,
    list_header_bytes: int = 8,
    list_entry_bytes: int = 24,
) -> MemoryEstimate:
    """Memoria de la red como matriz y como listas de adyacencia, en MB (10⁶ B).

    Supuestos por defecto (R1-B02, R1-B03):
      * matriz: una celda ``float64`` (8 B) con el tiempo de viaje;
      * listas: 8 B por cabecera de lista y 24 B por entrada
        (vecino ``int64`` + tiempo ``float64`` + distancia ``float64``).
    """
    matrix_bytes = n_nodes * n_nodes * matrix_cell_bytes
    lists_bytes = n_nodes * list_header_bytes + n_edges * list_entry_bytes
    return MemoryEstimate(
        n_nodes=n_nodes,
        n_edges=n_edges,
        matrix_mb=matrix_bytes / 1e6,
        lists_mb=lists_bytes / 1e6,
        density=n_edges / (n_nodes * n_nodes) if n_nodes else 0.0,
        assumptions=(
            f"matriz: {matrix_cell_bytes} B/celda; listas: {list_header_bytes} B/cabecera "
            f"+ {list_entry_bytes} B/entrada"
        ),
    )
