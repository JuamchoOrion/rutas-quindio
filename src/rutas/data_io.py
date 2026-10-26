"""Carga del grafo procesado de R1 para R2–R5 (sin volver a descargar, R1-B18).

Requiere ``osmnx`` (extra ``red``) solo para leer el GraphML con sus tipos.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass

from rutas import paths
from rutas.catalog import Place, load_catalog
from rutas.graph import Graph

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
        place_node = {row["id"]: graph.index_of(int(row["nodo_osm"])) for row in csv.DictReader(file)}
    return ProcessedNetwork(nx_graph, graph, places, place_node)
