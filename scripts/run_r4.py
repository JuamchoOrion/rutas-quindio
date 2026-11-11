"""R4 — Verifica y mide el ATSP exacto, la calidad de la heurística y el itinerario de un día.

Spec: specs/R4-ruta-optima.md (sección Experimentos) y specs/protocolo-experimental.md.

Uso (desde la raíz del repositorio, después de ``scripts/run_r2.py``):

    python scripts/run_r4.py

Lee ``results/r2/matriz_tiempos.csv`` y ``data/catalogo.csv``. Todos los resultados se
escriben al final, solo si todas las verificaciones pasan (PE-B06).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path

from rutas import paths
from rutas.benchmark import SEED, machine_info, measure_with_timeout
from rutas.catalog import DEFAULT_START_ID, Place, load_catalog
from rutas.data_io import load_travel_time_matrix, write_csv, write_json
from rutas.itinerary import DayPlan, plan_day
from rutas.tsp import (
    Matrix,
    Tour,
    brute_force_tsp,
    gap_percent,
    held_karp,
    held_karp_table_bytes,
    instance_matrix,
    nearest_neighbor_tour,
    tour_cost,
)

MATRIX_CSV = paths.R2 / "matriz_tiempos.csv"
MATRIX_SUMMARY_JSON = paths.R2 / "matriz_resumen.json"

EXACT_KS = range(5, 13)                # k = 5..12
QUALITY_KS = (5, 8, 10, 12)
QUALITY_INSTANCES = 5
QUALITY_SEED_STEP = 100                # Semilla de calidad: SEED + 100·k + i.
ITINERARY_ATTRACTIONS = 8
ATTRACTION_CATEGORY = "atractivo"

REL_TOL = 1e-9                         # Tolerancia relativa al comparar costos.
BYTES_PER_MB = 1_000_000
SECONDS_PER_MINUTE = 60.0
SECONDS_PER_HOUR = 3600.0
HASH_CHUNK_BYTES = 1 << 16

EXACT_COLUMNS = ["k", "tiempo_fuerza_bruta_ms", "tiempo_held_karp_ms", "completado_fb",
                 "completado_hk", "costo_fb_s", "costo_hk_s", "memoria_tabla_hk_mb", "semilla"]
QUALITY_COLUMNS = ["k", "instancia", "costo_optimo_s", "costo_heuristica_s", "brecha_pct",
                   "semilla"]
SUMMARY_COLUMNS = ["k", "instancias", "brecha_promedio_pct", "brecha_maxima_pct"]
ITINERARY_COLUMNS = ["orden", "lugar", "desplazamiento_min", "visita_min", "acumulado_h", "id"]


@dataclass(frozen=True)
class Inputs:
    ids: list[str]
    matrix: list[list[float]]
    places: dict[str, Place]

    @property
    def start(self) -> int:
        return self.ids.index(DEFAULT_START_ID)


@dataclass(frozen=True)
class MethodRun:
    """Resultado de un método exacto en un ``k``; ``None`` si no se ejecutó o no completó."""

    completed: bool
    median_ms: float | None = None
    tour: Tour | None = None


# --------------------------------------------------------------------------- #
# Entradas
# --------------------------------------------------------------------------- #
def load_inputs() -> Inputs:
    """Matriz de R2 y catálogo; aborta si sus ids no coinciden (spec R4, Experimentos)."""
    ids, matrix = load_travel_time_matrix(MATRIX_CSV)
    catalog = {place.id: place for place in load_catalog(paths.CATALOG_CSV)}
    if set(ids) != set(catalog) or len(ids) != len(catalog):
        raise SystemExit(
            "Los ids de la matriz de R2 no son los del catálogo; vuelva a correr "
            f"scripts/run_r2.py. Diferencia: {sorted(set(ids) ^ set(catalog))}"
        )
    return Inputs(ids, matrix, catalog)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def matrix_record() -> dict:
    """Contenido de ``matriz_usada.json``: qué matriz de R2 se usó."""
    return {
        "archivo": str(MATRIX_CSV.relative_to(paths.ROOT)),
        "sha256": file_sha256(MATRIX_CSV),
        "fecha_corrida": datetime.now().astimezone().isoformat(timespec="seconds"),
        "resumen_r2": json.loads(MATRIX_SUMMARY_JSON.read_text(encoding="utf-8")),
    }


def random_instance(inputs: Inputs, k: int, seed: int) -> list[list[float]]:
    """``k`` lugares sin Armenia, en el orden de la matriz, con ``rng.sample`` (spec R4)."""
    candidates = [i for i in range(len(inputs.ids)) if i != inputs.start]
    chosen = random.Random(seed).sample(candidates, k)
    return instance_matrix(inputs.matrix, inputs.start, chosen)


# --------------------------------------------------------------------------- #
# Verificación (PE-B06)
# --------------------------------------------------------------------------- #
def same_cost(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL_TOL)


def check_tour(costs: Matrix, tour: Tour, label: str) -> None:
    """Aborta si el recorrido no cumple R4-B03."""
    k = len(costs) - 1
    order = tour.order
    valid = (
        order[0] == 0 and order[-1] == 0
        and sorted(order[1:-1]) == list(range(1, k + 1))
        and same_cost(tour.cost, tour_cost(costs, order))
    )
    if not valid:
        raise SystemExit(f"Verificación de R4-B03 fallida en {label}: {tour}")


def check_exact_costs(k: int, brute: MethodRun, dynamic: MethodRun) -> None:
    """Aborta si fuerza bruta y Held-Karp completan con costos distintos."""
    if brute.completed and dynamic.completed and not same_cost(brute.tour.cost,
                                                               dynamic.tour.cost):
        raise SystemExit(
            f"Verificación fallida en k = {k}: fuerza bruta {brute.tour.cost} s, "
            f"Held-Karp {dynamic.tour.cost} s"
        )


def check_heuristic(k: int, instance: int, optimal: float, heuristic: float) -> None:
    """Aborta si la heurística queda por debajo del óptimo (spec R4, Calidad)."""
    if heuristic < optimal * (1 - REL_TOL):
        raise SystemExit(
            f"Verificación fallida en calidad k = {k}, instancia {instance}: "
            f"heurística {heuristic} s < óptimo {optimal} s"
        )


# --------------------------------------------------------------------------- #
# Exactas (PE-B03, PE-B07)
# --------------------------------------------------------------------------- #
def run_method(
    solver: Callable[[Matrix], Tour], costs: Matrix, label: str, enabled: bool
) -> MethodRun:
    """Mide ``solver(costs)`` en un proceso hijo con límite de 5 min y verifica R4-B03.

    Si ``enabled`` es falso (el método no completó un ``k`` menor), no se ejecuta.
    """
    if not enabled:
        print(f"   {label}: no se ejecuta (no completó un k menor)")
        return MethodRun(completed=False)
    measurement = measure_with_timeout(partial(solver, costs))
    if not measurement.completed:
        print(f"   {label}: no completado (límite de 5 min)")
        return MethodRun(completed=False)
    check_tour(costs, measurement.result, label)
    print(f"   {label}: {measurement.median_ms:.3f} ms "
          f"({len(measurement.samples_ms)} ejecuciones)")
    return MethodRun(True, measurement.median_ms, measurement.result)


def exact_row(k: int, brute: MethodRun, dynamic: MethodRun) -> dict:
    def cost(run: MethodRun) -> float | str:
        return run.tour.cost if run.completed else ""

    return {
        "k": k,
        "tiempo_fuerza_bruta_ms": brute.median_ms if brute.completed else "",
        "tiempo_held_karp_ms": dynamic.median_ms if dynamic.completed else "",
        "completado_fb": brute.completed,
        "completado_hk": dynamic.completed,
        "costo_fb_s": cost(brute),
        "costo_hk_s": cost(dynamic),
        "memoria_tabla_hk_mb": held_karp_table_bytes(k) / BYTES_PER_MB,
        "semilla": SEED,
    }


def run_exact(inputs: Inputs) -> list[dict]:
    """``k = 5..12``; un método que no completa un ``k`` no corre los mayores (PE-B07)."""
    rows: list[dict] = []
    brute_alive = dynamic_alive = True
    for k in EXACT_KS:
        costs = random_instance(inputs, k, SEED + k)
        brute = run_method(brute_force_tsp, costs, f"k={k} fuerza bruta", brute_alive)
        dynamic = run_method(held_karp, costs, f"k={k} Held-Karp", dynamic_alive)
        check_exact_costs(k, brute, dynamic)
        brute_alive, dynamic_alive = brute.completed, dynamic.completed
        rows.append(exact_row(k, brute, dynamic))
    return rows


# --------------------------------------------------------------------------- #
# Calidad de la heurística (R4-B14)
# --------------------------------------------------------------------------- #
def run_quality(inputs: Inputs) -> list[dict]:
    rows: list[dict] = []
    for k in QUALITY_KS:
        for instance in range(1, QUALITY_INSTANCES + 1):
            costs = random_instance(inputs, k, SEED + QUALITY_SEED_STEP * k + instance)
            optimal = held_karp(costs)
            heuristic = nearest_neighbor_tour(costs)
            label = f"calidad k={k} instancia {instance}"
            check_tour(costs, optimal, label)
            check_tour(costs, heuristic, label)
            check_heuristic(k, instance, optimal.cost, heuristic.cost)
            rows.append({
                "k": k,
                "instancia": instance,
                "costo_optimo_s": optimal.cost,
                "costo_heuristica_s": heuristic.cost,
                "brecha_pct": gap_percent(heuristic.cost, optimal.cost),
                "semilla": SEED,
            })
    return rows


def quality_summary(rows: Sequence[dict]) -> list[dict]:
    """Resumen generado desde las filas de ``heuristica_calidad.csv`` (spec R4)."""
    summary: list[dict] = []
    for k in QUALITY_KS:
        gaps = [row["brecha_pct"] for row in rows if row["k"] == k]
        summary.append({
            "k": k,
            "instancias": len(gaps),
            "brecha_promedio_pct": sum(gaps) / len(gaps),
            "brecha_maxima_pct": max(gaps),
        })
    return summary


# --------------------------------------------------------------------------- #
# Itinerario de un día (R4-B15 a R4-B18)
# --------------------------------------------------------------------------- #
def choose_attractions(inputs: Inputs) -> list[str]:
    """8 atractivos en el orden del catálogo con ``Random(SEED).sample`` (spec R4)."""
    attractions = [p.id for p in inputs.places.values() if p.category == ATTRACTION_CATEGORY]
    chosen = random.Random(SEED).sample(attractions, ITINERARY_ATTRACTIONS)
    missing = [pid for pid in chosen if inputs.places[pid].visit_min is None]
    if missing:
        raise SystemExit(f"Atractivos sin duración de visita en el catálogo: {missing}")
    return chosen


def run_itinerary(inputs: Inputs) -> tuple[list[str], DayPlan]:
    chosen = choose_attractions(inputs)
    labels = [DEFAULT_START_ID, *chosen]
    costs = instance_matrix(inputs.matrix, inputs.start, [inputs.ids.index(p) for p in chosen])
    visit_min = [0.0] + [inputs.places[p].visit_min for p in chosen]
    plan = plan_day(costs, labels, visit_min)
    check_itinerary(costs, labels, plan)
    return chosen, plan


def check_itinerary(costs: Matrix, labels: Sequence[str], plan: DayPlan) -> None:
    """Aborta si el plan no visita una vez cada atractivo no quitado (R4-B03, R4-B17)."""
    removed = {labels.index(removal.place) for removal in plan.removed}
    expected = sorted(set(range(1, len(labels))) - removed)
    order = plan.order
    valid = (
        order[0] == 0 and order[-1] == 0
        and sorted(order[1:-1]) == expected
        and same_cost(plan.travel_total_s, tour_cost(costs, order))
    )
    if not valid:
        raise SystemExit(f"Verificación fallida en el itinerario: orden {order}, "
                         f"quitados {[r.place for r in plan.removed]}")


def itinerary_rows(inputs: Inputs, plan: DayPlan) -> list[dict]:
    """Formato del anexo; ``lugar`` es el nombre y ``id`` va al final (R4-B18)."""
    return [
        {
            "orden": row.position,
            "lugar": inputs.places[row.place].name,
            "desplazamiento_min": row.travel_min,
            "visita_min": "" if row.visit_min is None else row.visit_min,
            "acumulado_h": row.cumulative_h,
            "id": row.place,
        }
        for row in plan.rows
    ]


def itinerary_summary(chosen: list[str], plan: DayPlan) -> dict:
    """``itinerario_resumen.json``; partida, elegidos y quitados con ids (spec R4)."""
    return {
        "partida": DEFAULT_START_ID,
        "atractivos_elegidos": chosen,
        "visitas_total_min": plan.visit_total_s / SECONDS_PER_MINUTE,
        "desplazamientos_total_min": plan.travel_total_s / SECONDS_PER_MINUTE,
        "jornada_total_h": plan.total_s / SECONDS_PER_HOUR,
        "cabe": plan.fits(),
        "quitados": [
            {
                "lugar": removal.place,
                "ahorro_min": removal.saving_s / SECONDS_PER_MINUTE,
                "jornada_antes_h": removal.day_before_s / SECONDS_PER_HOUR,
            }
            for removal in plan.removed
        ],
    }


# --------------------------------------------------------------------------- #
def main() -> None:
    print("1/4 Leyendo la matriz de R2 y el catálogo…")
    inputs = load_inputs()
    record = matrix_record()
    print(f"   {len(inputs.ids)} lugares; matriz sha256 {record['sha256'][:12]}…")

    print("2/4 Métodos exactos (verificación y medición, k = 5..12)…")
    exact = run_exact(inputs)

    print("3/4 Calidad de la heurística…")
    quality = run_quality(inputs)

    print("4/4 Itinerario de un día…")
    chosen, plan = run_itinerary(inputs)

    paths.R4.mkdir(parents=True, exist_ok=True)
    write_json(paths.R4 / "maquina.json", machine_info())
    write_json(paths.R4 / "matriz_usada.json", record)
    write_csv(paths.R4 / "exactas_tiempos.csv", exact, EXACT_COLUMNS)
    write_csv(paths.R4 / "heuristica_calidad.csv", quality, QUALITY_COLUMNS)
    write_csv(paths.R4 / "heuristica_resumen.csv", quality_summary(quality), SUMMARY_COLUMNS)
    write_csv(paths.R4 / "itinerario.csv", itinerary_rows(inputs, plan), ITINERARY_COLUMNS)
    write_json(paths.R4 / "itinerario_resumen.json", itinerary_summary(chosen, plan))
    print(f"   listo: {paths.R4.relative_to(paths.ROOT)}/")


if __name__ == "__main__":
    main()
