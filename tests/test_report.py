"""Pruebas de las tablas y gráficas (specs/protocolo-experimental.md, PE-B09 y PE-B10)."""

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

from rutas.report import format_ms, markdown_table

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "make_figures.py"
EXACT_COLUMNS = ["k", "tiempo_fuerza_bruta_ms", "tiempo_held_karp_ms", "completado_fb",
                 "completado_hk", "costo_fb_s", "costo_hk_s", "memoria_tabla_hk_mb", "semilla"]


def load_make_figures():
    spec = importlib.util.spec_from_file_location("make_figures", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module          # dataclasses lo busca ahí.
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(("value", "expected"), [
    (0.056333, "0,0563"),
    (155982.79, "155 983"),
    (7.5655, "7,57"),
    (0.5003, "0,500"),
])
def test_PE_C08_format_ms(value, expected):
    assert format_ms(value) == expected


def test_PE_C09_markdown_table():
    table = markdown_table(["k", "Tiempo (ms)"], [["5", "0,0563"], ["12", "155 983"]])
    assert table.splitlines() == [
        "| k | Tiempo (ms) |",
        "| ---: | ---: |",
        "| 5 | 0,0563 |",
        "| 12 | 155 983 |",
    ]


def test_PE_C10_r4_figure_skips_not_completed_k(tmp_path):
    rows = [
        {"k": 11, "tiempo_fuerza_bruta_ms": 13000.0, "tiempo_held_karp_ms": 9.9,
         "completado_fb": True, "completado_hk": True, "memoria_tabla_hk_mb": 0.270336},
        {"k": 12, "tiempo_fuerza_bruta_ms": "", "tiempo_held_karp_ms": 23.4,
         "completado_fb": False, "completado_hk": True, "memoria_tabla_hk_mb": 0.589824},
    ]
    r4_dir = tmp_path / "r4"
    r4_dir.mkdir()
    with open(r4_dir / "exactas_tiempos.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=EXACT_COLUMNS, restval="")
        writer.writeheader()
        writer.writerows(rows)

    plot = load_make_figures().figuras_r4(r4_dir, tmp_path / "tablas", tmp_path / "no.csv")

    assert (r4_dir / "exactas_tiempo_vs_k.png").stat().st_size > 0
    assert plot.series_k["Fuerza bruta"] == [11]
    assert plot.series_k["Held-Karp"] == [11, 12]
    assert any("no completada: k = 12" in label for label in plot.legend_labels)
