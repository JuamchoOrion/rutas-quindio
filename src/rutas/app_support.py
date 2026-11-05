"""Lógica de la aplicación demostrativa, sin Streamlit, para poder probarla con pytest.

Spec: specs/R5-aplicacion.md (R5-B03, R5-B06 a R5-B09; casos R5-C06 a R5-C10).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rutas.geo import UTM_18N, to_latlon
from rutas.graph import Graph
from rutas.shortest_paths import dijkstra_heap
from rutas.tsp import Matrix, gap_percent, held_karp, nearest_neighbor_tour

SECONDS_PER_MINUTE = 60.0
LatLon = tuple[float, float]


@dataclass(frozen=True)
class TourSummary:
    """Un recorrido de la comparación: orden (índices de la instancia) y tiempos en segundos."""

    method: str
    order: list[int]
    travel_s: float
    visit_s: float

    @property
    def total_s(self) -> float:
        return self.travel_s + self.visit_s


@dataclass(frozen=True)
class TourComparison:
    """Held-Karp frente al vecino más cercano sobre el mismo conjunto (R5-B03, punto 1)."""

    optimal: TourSummary
    heuristic: TourSummary

    @property
    def difference_s(self) -> float:
        """Diferencia de desplazamientos (igual a la de los totales: mismas visitas)."""
        return self.heuristic.travel_s - self.optimal.travel_s

    @property
    def gap_pct(self) -> float:
        """Brecha sobre los desplazamientos, como R4-B14."""
        return gap_percent(self.heuristic.travel_s, self.optimal.travel_s)


def compare_tours(costs: Matrix, visit_min: Sequence[float]) -> TourComparison:
    """Ejecuta Held-Karp y el vecino más cercano en el momento sobre ``costs`` (R5-B03).

    ``costs`` es la submatriz de la instancia (índice 0 = partida) y ``visit_min`` la
    duración de la visita de cada índice; la del índice 0 se ignora.
    """
    visit_s = SECONDS_PER_MINUTE * sum(visit_min[1:])
    optimal = held_karp(costs)
    heuristic = nearest_neighbor_tour(costs)
    return TourComparison(
        optimal=TourSummary("Held-Karp", optimal.order, optimal.cost, visit_s),
        heuristic=TourSummary("Vecino más cercano", heuristic.order, heuristic.cost, visit_s),
    )


def route_latlons(nx_graph, graph: Graph, path: Sequence[int]) -> list[LatLon]:
    """(lat, lon) de cada nodo de una ruta de índices de ``graph``, en orden (R5-B07)."""
    nodes = nx_graph.nodes
    return [(nodes[node_id]["y"], nodes[node_id]["x"]) for node_id in graph.ids_of(path)]


def tour_legs(graph: Graph, nodes: Sequence[int]) -> list[list[int]]:
    """Ruta de ``dijkstra_heap`` de cada tramo consecutivo de un recorrido de nodos."""
    return [dijkstra_heap(graph, a, b).path for a, b in zip(nodes, nodes[1:])]


def hull_latlons(path: str | Path) -> list[LatLon] | None:
    """Vértices de ``envolvente_red.json`` en (lat, lon) (R5-B08); ``None`` si no existe.

    Raises:
        ValueError: si el archivo no está en UTM 18N (formato de la spec de R3).
    """
    path = Path(path)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("crs") != UTM_18N:
        raise ValueError(f"{path.name} está en {data.get('crs')!r}; se esperaba {UTM_18N}")
    return [to_latlon(x, y) for x, y in data["vertices"]]


def result_files(folder: str | Path, suffix: str) -> list[Path]:
    """Archivos ``*suffix`` de ``folder`` sin subcarpetas, en orden alfabético (R5-B09)."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix == suffix)
