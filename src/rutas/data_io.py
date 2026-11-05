"""Carga del grafo procesado de R1 para R2–R5 (sin volver a descargar, R1-B18).

Requiere ``osmnx`` (extra ``red``) solo para leer el GraphML con sus tipos.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rutas import paths
from rutas.catalog import Place, load_catalog
from rutas.graph import Graph

MATRIX_CORNER = "id"   # Celda superior izquierda de matriz_tiempos.csv (R2-B14).

EDGE_DTYPES = {"length_m": float, "speed_kmh": float, "travel_time_s": float}


@dataclass
class ProcessedNetwork:
    nx_graph: object                 # MultiDiGraph de la CFC (para dibujar rutas)
    graph: Graph                     # listas de adyacencia propias, peso = travel_time_s
    places: list[Place]
    place_node: dict[str, int]       # id del lugar → índice del nodo en ``graph``


def load_processed_network() -> ProcessedNetwork:
    import osmnx as ox  # Import local: el resto del paquete no depende de OSMnx.

    nx_graph = ox.load_graphml(paths.NETWORK_GRAPHML, edge_dtypes=EDGE_DTYPES)
    graph = Graph.from_networkx(nx_graph, weight="travel_time_s")
    places = load_catalog(paths.CATALOG_CSV)
    with open(paths.PLACE_NODES_CSV, newline="", encoding="utf-8") as file:
        place_node = {
            row["id"]: graph.index_of(int(row["nodo_osm"])) for row in csv.DictReader(file)
        }
    return ProcessedNetwork(nx_graph, graph, places, place_node)


def write_travel_time_matrix(
    path: str | Path, ids: Sequence[str], matrix: Sequence[Sequence[float]]
) -> None:
    """Escribe la matriz de tiempos con el formato del anexo (R2-B14, R2-B15).

    Primera fila y primera columna: ids; celdas en segundos. ``csv`` escribe cada
    ``float`` con ``repr``, así que la lectura recupera el valor exacto (R2-C11).
    """
    if len(matrix) != len(ids) or any(len(row) != len(ids) for row in matrix):
        raise ValueError("La matriz debe ser cuadrada y tener una fila por id")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([MATRIX_CORNER, *ids])
        for place_id, row in zip(ids, matrix):
            writer.writerow([place_id, *(float(value) for value in row)])


def load_travel_time_matrix(path: str | Path) -> tuple[list[str], list[list[float]]]:
    """Lee ``matriz_tiempos.csv``: devuelve ``(ids, matriz)`` en el orden del archivo (R2-B15).

    Raises:
        ValueError: si la primera fila y la primera columna no tienen los mismos ids.
    """
    with open(path, newline="", encoding="utf-8") as file:
        header, *rows = list(csv.reader(file))
    ids = header[1:]
    if [row[0] for row in rows] != ids:
        raise ValueError("Las filas de la matriz no siguen el orden de las columnas")
    return ids, [[float(value) for value in row[1:]] for row in rows]


def write_csv(
    path: str | Path, rows: Sequence[dict], fieldnames: Sequence[str] | None = None
) -> None:
    """Escribe ``rows`` con encabezado; con ``fieldnames`` lo escribe aunque no haya filas."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(fieldnames) if fieldnames is not None else list(rows[0]) if rows else []
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: str | Path, data: dict) -> None:
    """Escribe ``data`` como JSON legible (UTF-8, sin escapar tildes)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
