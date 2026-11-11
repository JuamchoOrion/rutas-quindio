"""R1 — Repite solo la medición de la CFC en las cinco redes (R1-B13), sin tocar la red.

Spec: specs/R1-modelo-red.md (R1-B13, R1-B14 y R1-B26) y specs/protocolo-experimental.md.

Uso (desde la raíz del repositorio, con el equipo en reposo):

    python scripts/measure_scc.py

El departamento sale de ``data/raw/quindio.graphml`` y los radios, de la caché de OSMnx
(``cache/``) con el servidor guardado en ``data/processed/red_resumen.json``. Si V o E
de alguna red no coinciden con ``results/r1/scc_tiempos.csv``, aborta sin escribir nada.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

import osmnx as ox
from build_network import (
    RAW_GRAPHML,
    add_weights,
    load_valid_catalog,
    scc_timing_table,
    start_point,
)

from rutas import paths
from rutas.benchmark import machine_info
from rutas.data_io import write_csv, write_json
from rutas.report import read_csv, read_json

SCC_CSV = paths.R1 / "scc_tiempos.csv"
SIZE_COLUMNS = ("V", "E")


def size_mismatches(expected: Sequence[dict], measured: Sequence[dict]) -> list[str]:
    """Redes cuyo V o E cambió frente a ``scc_tiempos.csv`` vigente (R1-B26, R1-C15)."""
    measured_by_name = {str(row["red"]): row for row in measured}
    problems = []
    for row in expected:
        name = str(row["red"])
        new = measured_by_name.get(name)
        if new is None:
            problems.append(f"{name}: no se midió")
            continue
        for column in SIZE_COLUMNS:
            if int(row[column]) != int(new[column]):
                problems.append(f"{name}: {column} pasó de {row[column]} a {new[column]}")
    return problems


def main() -> None:
    center = start_point(load_valid_catalog())
    ox.settings.use_cache = True
    ox.settings.overpass_url = read_json(paths.NETWORK_SUMMARY_JSON)["overpass_radios_scc"]

    print("Cargando el departamento y asignando pesos…")
    department = ox.load_graphml(RAW_GRAPHML)
    add_weights(department)

    print("Midiendo largest_component en las cinco redes…")
    rows = scc_timing_table(department, center)
    problems = size_mismatches(read_csv(SCC_CSV), rows)
    if problems:
        print("ABORTA: la red no es la misma de R2–R4 (R1-B26):", *problems, sep="\n  ")
        sys.exit(1)

    write_csv(SCC_CSV, rows)
    write_json(paths.R1 / "maquina.json", machine_info())
    for row in rows:
        print(f"  {row['red']}: V+E = {row['V_mas_E']}, {row['tiempo_ms']:.1f} ms")
    print(f"Listo: {SCC_CSV.relative_to(paths.ROOT)}")


if __name__ == "__main__":
    main()
