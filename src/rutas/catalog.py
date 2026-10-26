"""Catálogo de lugares del Quindío: carga y validación.

Spec: specs/R1-modelo-red.md (R1-B20 a R1-B24, casos R1-C11 y R1-C12).
"""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

DEFAULT_START_ID = "armenia"

MIN_PER_CATEGORY: dict[str, int] = {
    "cabecera": 12,
    "atractivo": 15,
    "finca_hotel": 8,
    "acopio": 5,
}
MIN_TOTAL = 40

# Recuadro grueso del departamento (R1-B24). No reemplaza la verificación en un mapa.
LAT_RANGE = (4.05, 4.75)
LON_RANGE = (-75.95, -75.35)

COLUMNS = ("id", "nombre", "municipio", "categoria", "lat", "lon",
           "duracion_visita_min", "fuente_duracion")


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    municipality: str
    category: str
    lat: float
    lon: float
    visit_min: float | None = None
    visit_source: str = ""


def load_catalog(path: str | Path) -> list[Place]:
    """Lee ``data/catalogo.csv`` (columnas en :data:`COLUMNS`)."""
    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        missing = set(COLUMNS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Faltan columnas en el catálogo: {sorted(missing)}")
        return [_row_to_place(row) for row in reader]


def _row_to_place(row: dict[str, str]) -> Place:
    duration = row["duracion_visita_min"].strip()
    return Place(
        id=row["id"].strip(),
        name=row["nombre"].strip(),
        municipality=row["municipio"].strip(),
        category=row["categoria"].strip(),
        lat=float(row["lat"]),
        lon=float(row["lon"]),
        visit_min=float(duration) if duration else None,
        visit_source=row["fuente_duracion"].strip(),
    )


def validate_catalog(places: Iterable[Place]) -> list[str]:
    """Lista de errores del catálogo; vacía si cumple R1-B21 a R1-B24."""
    places = list(places)
    errors: list[str] = []

    if len(places) < MIN_TOTAL:
        errors.append(f"El catálogo tiene {len(places)} lugares; se requieren al menos {MIN_TOTAL}")

    counts = Counter(place.category for place in places)
    for category, minimum in MIN_PER_CATEGORY.items():
        if counts[category] < minimum:
            errors.append(f"Categoría '{category}': {counts[category]} lugares, mínimo {minimum}")
    for category in counts.keys() - MIN_PER_CATEGORY.keys():
        errors.append(f"Categoría desconocida '{category}'")

    duplicated = [pid for pid, n in Counter(p.id for p in places).items() if n > 1]
    if duplicated:
        errors.append(f"Identificadores repetidos: {sorted(duplicated)}")
    if all(place.id != DEFAULT_START_ID for place in places):
        errors.append(f"Falta el lugar de partida por defecto '{DEFAULT_START_ID}'")

    for place in places:
        if not (LAT_RANGE[0] <= place.lat <= LAT_RANGE[1] and LON_RANGE[0] <= place.lon <= LON_RANGE[1]):
            errors.append(f"'{place.id}' tiene coordenadas fuera del Quindío: ({place.lat}, {place.lon})")
        if place.category == "atractivo":
            if place.visit_min is None or place.visit_min <= 0:
                errors.append(f"El atractivo '{place.id}' no tiene duración de visita válida")
            if not place.visit_source:
                errors.append(f"El atractivo '{place.id}' no tiene fuente de la duración")
    return errors
