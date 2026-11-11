"""R3 — Verifica y mide QuickHull (propio) frente a SciPy en la red y en cuadrados aleatorios.

Spec: specs/R3-envolvente-convexa.md (sección Experimento, R3-B07) y
specs/protocolo-experimental.md.

Uso (desde la raíz del repositorio, después de ``scripts/build_network.py``):

    python scripts/run_r3.py

No descarga nada: lee solo los nodos de ``data/processed/red_cfc.graphml``.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.spatial import ConvexHull

from rutas import paths
from rutas.benchmark import SEED, machine_info, measure
from rutas.convex_hull import Point, prepare_points, quickhull
from rutas.data_io import write_csv, write_json
from rutas.geo import UTM_18N, to_utm_many

NETWORK_SET = "red_vial"
SQUARE_SIZES = (1_000, 10_000, 50_000)
SQUARE_SIDE = 100_000              # Coordenadas enteras en [0, 100 000)².
CSV_COLUMNS = ["conjunto", "n", "vertices", "tiempo_propio_ms", "tiempo_scipy_ms",
               "cociente", "semilla"]


@dataclass(frozen=True)
class PointSet:
    name: str
    points: list[Point]


@dataclass(frozen=True)
class HullMeasurement:
    point_set: PointSet
    hull: list[Point]
    own_ms: float
    scipy_ms: float


# --------------------------------------------------------------------------- #
# Conjuntos de puntos
# --------------------------------------------------------------------------- #
def network_points() -> list[Point]:
    """Nodos de la CFC de R1 en UTM 18N, redondeados y sin duplicados (R3-B01).

    ``to_utm_many`` recibe primero las latitudes (``y`` de OSMnx) y luego las
    longitudes (``x``), igual que ``associate_places`` en ``build_network.py``.
    """
    import osmnx as ox  # Import local, como en data_io: solo se necesita para leer la red.

    graph = ox.load_graphml(paths.NETWORK_GRAPHML)
    node_ids = list(graph.nodes)
    xs, ys = to_utm_many(
        [graph.nodes[n]["y"] for n in node_ids], [graph.nodes[n]["x"] for n in node_ids]
    )
    return prepare_points(xs.tolist(), ys.tolist())


def square_points(n: int) -> list[Point]:
    """``n`` puntos enteros distintos, uniformes en el cuadrado, con su propio Random(SEED)."""
    rng = random.Random(SEED)
    seen: set[Point] = set()
    points: list[Point] = []
    while len(points) < n:
        point = (rng.randrange(SQUARE_SIDE), rng.randrange(SQUARE_SIDE))
        if point not in seen:
            seen.add(point)
            points.append(point)
    return points


# --------------------------------------------------------------------------- #
# Verificación (R3-B07, PE-B06) y medición (PE-B02, PE-B03)
# --------------------------------------------------------------------------- #
def to_array(points: Sequence[Point]) -> np.ndarray:
    return np.asarray(points, dtype=np.float64)


def scipy_vertices(points: Sequence[Point], arr: np.ndarray) -> set[Point]:
    return {points[i] for i in ConvexHull(arr).vertices}


def verify(point_set: PointSet, arr: np.ndarray) -> list[Point]:
    """Aborta (SystemExit) si los vértices propios no son los de SciPy (R3-B07)."""
    hull = quickhull(point_set.points)
    expected = scipy_vertices(point_set.points, arr)
    if set(hull) != expected or len(hull) != len(expected):
        raise SystemExit(
            f"Verificación de R3 fallida en {point_set.name}: propio {len(hull)} vértices, "
            f"SciPy {len(expected)}; diferencia {sorted(set(hull) ^ expected)[:10]}"
        )
    print(f"   {point_set.name}: {len(hull)} vértices, iguales a SciPy")
    return hull


def measure_set(point_set: PointSet) -> HullMeasurement:
    """Verifica y luego mide solo ``quickhull(points)`` y solo ``ConvexHull(arr)``."""
    points = point_set.points
    arr = to_array(points)                      # Fuera de la medición (PE-B02).
    hull = verify(point_set, arr)
    own = measure(lambda: quickhull(points))
    library = measure(lambda: ConvexHull(arr))
    print(f"   {point_set.name}: propio {own.median_ms:.3f} ms, SciPy {library.median_ms:.3f} ms")
    return HullMeasurement(point_set, hull, own.median_ms, library.median_ms)


def csv_row(result: HullMeasurement) -> dict:
    return {
        "conjunto": result.point_set.name,
        "n": len(result.point_set.points),
        "vertices": len(result.hull),
        "tiempo_propio_ms": result.own_ms,
        "tiempo_scipy_ms": result.scipy_ms,
        "cociente": result.own_ms / result.scipy_ms,
        "semilla": SEED,
    }


def hull_json(result: HullMeasurement) -> dict:
    """Formato de ``envolvente_red.json`` (spec R3; lo lee ``app_support.hull_latlons``)."""
    return {
        "crs": UTM_18N,
        "n_puntos": len(result.point_set.points),
        "vertices": [[x, y] for x, y in result.hull],
    }


def main() -> None:
    paths.R3.mkdir(parents=True, exist_ok=True)
    print("1/3 Preparando los conjuntos de puntos…")
    point_sets = [PointSet(NETWORK_SET, network_points())]
    point_sets += [PointSet(f"cuadrado_{n}", square_points(n)) for n in SQUARE_SIZES]
    write_json(paths.R3 / "maquina.json", machine_info())

    print("2/3 Verificando contra SciPy y midiendo…")
    results = [measure_set(point_set) for point_set in point_sets]

    print("3/3 Guardando resultados…")
    write_csv(paths.R3 / "envolvente_tiempos.csv", [csv_row(r) for r in results], CSV_COLUMNS)
    write_json(paths.R3 / "envolvente_red.json", hull_json(results[0]))
    print(f"   listo: {paths.R3.relative_to(paths.ROOT)}/")


if __name__ == "__main__":
    main()
