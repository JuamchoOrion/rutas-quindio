"""R2 — Verifica y mide Dijkstra (lineal y con cola de prioridad) y calcula la matriz de tiempos.

Spec: specs/R2-caminos-minimos.md (R2-B11 a R2-B15) y specs/protocolo-experimental.md.

Uso (desde la raíz del repositorio, después de ``scripts/build_network.py``):

    python scripts/run_r2.py

No descarga nada: lee ``data/processed/`` (R1-B18).
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from rutas import paths
from rutas.benchmark import SEED, machine_info, measure, median
from rutas.data_io import (
    ProcessedNetwork,
    load_processed_network,
    write_csv,
    write_json,
    write_travel_time_matrix,
)
from rutas.graph import Graph
from rutas.shortest_paths import (
    PathResult,
    dijkstra_all,
    dijkstra_heap,
    dijkstra_linear,
    travel_time_matrix,
)

N_NEAR_PAIRS = 10                  # Medidos con las dos versiones (R2-B12).
N_FAR_PAIRS = 10                   # Solo cola de prioridad; 10 + 10 = 20 pares.
MAX_NEAR_PAIRS_PER_MUNICIPALITY = 3
FAR_SEED_OFFSET = 1                # Los lejanos se barajan con SEED + 1 (R2-B12).
REL_TOL = 1e-9                     # Tolerancia relativa de la verificación (R2-B11).
LINEAR, HEAP = "lineal", "cola_prioridad"
NEAR, FAR = "cercano", "lejano"


@dataclass(frozen=True)
class Pair:
    origin: str
    destination: str
    kind: str                      # NEAR o FAR


# --------------------------------------------------------------------------- #
# Elección de los pares (R2-B12)
# --------------------------------------------------------------------------- #
def candidate_pairs(
    network: ProcessedNetwork, same_municipality: bool
) -> list[tuple[str, str]]:
    """Pares ordenados de lugares en nodos distintos, del mismo municipio o de distintos."""
    node, places = network.place_node, network.places
    return [
        (a.id, b.id)
        for a in places
        for b in places
        if node[a.id] != node[b.id]
        and (a.municipality == b.municipality) == same_municipality
    ]


def choose_near_pairs(network: ProcessedNetwork) -> list[Pair]:
    """10 pares del mismo municipio, barajados con SEED y a lo sumo 3 por municipio."""
    municipality = {place.id: place.municipality for place in network.places}
    candidates = candidate_pairs(network, same_municipality=True)
    random.Random(SEED).shuffle(candidates)
    per_municipality: Counter = Counter()
    chosen: list[Pair] = []
    for origin, destination in candidates:
        town = municipality[origin]
        if per_municipality[town] < MAX_NEAR_PAIRS_PER_MUNICIPALITY:
            per_municipality[town] += 1
            chosen.append(Pair(origin, destination, NEAR))
        if len(chosen) == N_NEAR_PAIRS:
            return chosen
    raise SystemExit("No hay suficientes pares cercanos para R2-B12")


def choose_far_pairs(network: ProcessedNetwork) -> list[Pair]:
    """10 pares de municipios distintos, barajados con SEED + 1."""
    candidates = candidate_pairs(network, same_municipality=False)
    random.Random(SEED + FAR_SEED_OFFSET).shuffle(candidates)
    return [Pair(origin, destination, FAR) for origin, destination in candidates[:N_FAR_PAIRS]]


# --------------------------------------------------------------------------- #
# Verificación (R2-B13, PE-B06)
# --------------------------------------------------------------------------- #
def same_cost(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL_TOL)


def path_errors(graph: Graph, result: PathResult, source: int, target: int) -> list[str]:
    """Condición 3 de R2-B13: la ruta es un camino real de ``source`` a ``target`` con ese costo."""
    path = result.path
    if not path or path[0] != source or path[-1] != target:
        return ["la ruta no empieza en el origen o no termina en el destino"]
    weights = [graph.edge_weight(u, v) for u, v in zip(path, path[1:])]
    if any(math.isinf(w) for w in weights):
        return ["la ruta usa una arista que no existe"]
    if not same_cost(math.fsum(weights), result.cost):
        return [f"la suma de la ruta ({math.fsum(weights)}) no es el costo ({result.cost})"]
    return []


def verify(
    network: ProcessedNetwork,
    pairs: Sequence[Pair],
    ids: Sequence[str],
    matrix: Sequence[Sequence[float]],
) -> None:
    """Aborta (SystemExit) si falla alguna de las cuatro condiciones de R2-B13."""
    graph, node = network.graph, network.place_node
    position = {place_id: i for i, place_id in enumerate(ids)}
    all_dist: dict[int, list[float]] = {}
    errors: list[str] = []

    for pair in pairs:
        source, target = node[pair.origin], node[pair.destination]
        label = f"{pair.origin} → {pair.destination}"
        heap = dijkstra_heap(graph, source, target)
        dist = all_dist.setdefault(source, dijkstra_all(graph, source))
        if not same_cost(heap.cost, dist[target]):                                 # 1
            errors.append(f"{label}: cola {heap.cost} ≠ dijkstra_all {dist[target]}")
        errors += [f"{label} (cola): {e}" for e in path_errors(graph, heap, source, target)]
        if pair.kind == NEAR:                                                      # 2
            linear = dijkstra_linear(graph, source, target)
            if not same_cost(linear.cost, heap.cost):
                errors.append(f"{label}: lineal {linear.cost} ≠ cola {heap.cost}")
            errors += [f"{label} (lineal): {e}"
                       for e in path_errors(graph, linear, source, target)]
        cell = matrix[position[pair.origin]][position[pair.destination]]           # 4
        if not same_cost(cell, heap.cost):
            errors.append(f"{label}: matriz {cell} ≠ cola {heap.cost}")

    for i, row in enumerate(matrix):                                               # 4
        if row[i] != 0.0:
            errors.append(f"diagonal de {ids[i]} = {row[i]}")
        if not all(math.isfinite(value) for value in row):
            errors.append(f"la fila de {ids[i]} tiene celdas infinitas")

    if errors:
        raise SystemExit("Verificación de R2 fallida:\n  - " + "\n  - ".join(errors))
    print(f"   verificación correcta en {len(pairs)} pares y en la matriz {len(ids)}×{len(ids)}")


# --------------------------------------------------------------------------- #
# Medición (R2-B14, PE-B02 a PE-B04)
# --------------------------------------------------------------------------- #
def measure_pairs(network: ProcessedNetwork, pairs: Sequence[Pair]) -> list[dict]:
    """Una fila por consulta y versión: cola en los 20 pares, lineal en los cercanos."""
    graph, node = network.graph, network.place_node
    rows = []
    for pair in pairs:
        source, target = node[pair.origin], node[pair.destination]
        versions = [(HEAP, dijkstra_heap)]
        if pair.kind == NEAR:
            versions.append((LINEAR, dijkstra_linear))
        for version, dijkstra in versions:
            measurement = measure(lambda f=dijkstra, s=source, t=target: f(graph, s, t))
            result: PathResult = measurement.result
            rows.append({
                "origen": pair.origin,
                "destino": pair.destination,
                "version": version,
                "tiempo_viaje_s": result.cost,
                "nodos_explorados": result.explored,
                "tiempo_ms": measurement.median_ms,
                "tipo_par": pair.kind,
                "semilla": SEED,
            })
            print(f"   {version:15} {pair.origin} → {pair.destination}: "
                  f"{measurement.median_ms:.2f} ms, {result.explored} nodos")
    return rows


def ratio_rows(measurements: Sequence[dict]) -> list[dict]:
    """Cociente tiempo lineal / tiempo cola en los pares medidos con las dos versiones."""
    by_pair: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for row in measurements:
        by_pair[(row["origen"], row["destino"])][row["version"]] = row
    rows = []
    for (origin, destination), versions in by_pair.items():
        if LINEAR not in versions:
            continue
        linear, heap = versions[LINEAR], versions[HEAP]
        rows.append({
            "origen": origin,
            "destino": destination,
            "explorados_lineal": linear["nodos_explorados"],
            "explorados_cola": heap["nodos_explorados"],
            "tiempo_lineal_ms": linear["tiempo_ms"],
            "tiempo_cola_ms": heap["tiempo_ms"],
            "cociente": linear["tiempo_ms"] / heap["tiempo_ms"],
        })
    return rows


def ratio_summary(ratios: Sequence[dict]) -> dict:
    values = [row["cociente"] for row in ratios]
    return {"pares": len(values), "mediana": median(values),
            "minimo": min(values), "maximo": max(values)}


def matrix_summary(
    network: ProcessedNetwork, ids: Sequence[str], matrix: Sequence[Sequence[float]],
    elapsed_ms: float,
) -> dict:
    """Asimetría de la matriz y lugares que comparten nodo (R2-B14)."""
    asymmetric, worst = 0, (0.0, "", "")
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if not same_cost(matrix[i][j], matrix[j][i]):
                asymmetric += 1
            difference = abs(matrix[i][j] - matrix[j][i])
            if difference > worst[0]:
                worst = (difference, ids[i], ids[j])
    groups: dict[int, list[str]] = defaultdict(list)
    for place_id in ids:
        groups[network.place_node[place_id]].append(place_id)
    return {
        "n": len(ids),
        "tiempo_ms": elapsed_ms,
        "pares_asimetricos": asymmetric,
        "pares_totales": len(ids) * (len(ids) - 1) // 2,
        "max_diferencia_s": {"valor": worst[0], "lugar_a": worst[1], "lugar_b": worst[2]},
        "lugares_mismo_nodo": [group for group in groups.values() if len(group) > 1],
    }


def main() -> None:
    paths.R2.mkdir(parents=True, exist_ok=True)
    print("1/4 Cargando la red procesada de R1…")
    network = load_processed_network()
    write_json(paths.R2 / "maquina.json", machine_info())

    pairs = choose_near_pairs(network) + choose_far_pairs(network)
    ids = [place.id for place in network.places]
    sources = [network.place_node[place_id] for place_id in ids]

    print("2/4 Calculando la matriz de tiempos y verificando (R2-B13)…")
    matrix_measurement = measure(lambda: travel_time_matrix(network.graph, sources))
    matrix = matrix_measurement.result
    verify(network, pairs, ids, matrix)

    print("3/4 Midiendo Dijkstra…")
    measurements = measure_pairs(network, pairs)
    ratios = ratio_rows(measurements)

    print("4/4 Guardando resultados…")
    write_csv(paths.R2 / "dijkstra_mediciones.csv", measurements)
    write_csv(paths.R2 / "dijkstra_cociente.csv", ratios)
    summary = ratio_summary(ratios)
    write_csv(paths.R2 / "dijkstra_cociente_resumen.csv", [summary])
    write_travel_time_matrix(paths.R2 / "matriz_tiempos.csv", ids, matrix)
    write_json(paths.R2 / "matriz_resumen.json",
               matrix_summary(network, ids, matrix, matrix_measurement.median_ms))
    print(f"Listo. Cociente lineal/cola: mediana {summary['mediana']:.0f}, "
          f"mínimo {summary['minimo']:.0f}, máximo {summary['maximo']:.0f}")


if __name__ == "__main__":
    main()
