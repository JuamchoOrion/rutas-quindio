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


MEASUREMENT_COLUMNS = ["origen", "destino", "version", "tiempo_viaje_s", "nodos_explorados",
                       "tiempo_ms", "tipo_par", "semilla"]
CATALOG_COLUMNS = ["id", "nombre", "municipio", "categoria", "lat", "lon",
                   "duracion_visita_min", "fuente_duracion"]


def write_rows(path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns, restval="")
        writer.writeheader()
        writer.writerows(rows)


def test_PE_C11_r2_scatter_and_ratio_table(tmp_path):
    def row(origin, version, explored, ms):
        return {"origen": origin, "destino": "b", "version": version, "tiempo_viaje_s": 60.0,
                "nodos_explorados": explored, "tiempo_ms": ms, "tipo_par": "cercano",
                "semilla": 1}
    rows = [row("a", "cola_prioridad", 10, 0.01), row("a", "lineal", 10, 2.0),
            row("c", "cola_prioridad", 100, 0.1), row("c", "lineal", 100, 20.0),
            row("d", "cola_prioridad", 1000, 1.0)]
    r2_dir = tmp_path / "r2"
    r2_dir.mkdir()
    write_rows(r2_dir / "dijkstra_mediciones.csv", MEASUREMENT_COLUMNS, rows)
    write_rows(r2_dir / "dijkstra_cociente_resumen.csv", ["pares", "mediana", "minimo", "maximo"],
               [{"pares": 2, "mediana": 200.0, "minimo": 200.0, "maximo": 200.0}])

    plot = load_make_figures().figuras_r2(r2_dir, tmp_path / "tablas")

    assert (r2_dir / "dijkstra_tiempo_vs_nodos.png").stat().st_size > 0
    assert plot.series_points == {"Cola de prioridad": 3, "Lineal": 2}
    text = (tmp_path / "tablas" / "r2.md").read_text(encoding="utf-8")
    assert "| Mediana | Mínimo | Máximo |" in text
    assert "| 200,0 | 200,0 | 200,0 |" in text


def test_PE_C12_r1_far_places_table(tmp_path):
    catalog = tmp_path / "catalogo.csv"
    write_rows(catalog, CATALOG_COLUMNS, [
        {"id": "cocora", "nombre": "Valle de Cocora", "municipio": "Salento",
         "categoria": "atractivo", "lat": 4.6, "lon": -75.5, "duracion_visita_min": 180,
         "fuente_duracion": "criterio del grupo"}])
    r1_dir = tmp_path / "r1"
    r1_dir.mkdir()
    far_columns = ["id", "nodo_osm", "distancia_m", "lejano"]
    figures = load_make_figures()

    write_rows(r1_dir / "lugares_lejanos.csv", far_columns, [])
    figures.figuras_r1(r1_dir, tmp_path / "tablas", catalog)
    assert "ninguno" in (tmp_path / "tablas" / "r1.md").read_text(encoding="utf-8")

    write_rows(r1_dir / "lugares_lejanos.csv", far_columns,
               [{"id": "cocora", "nodo_osm": 123, "distancia_m": 1050.9, "lejano": True}])
    figures.figuras_r1(r1_dir, tmp_path / "tablas", catalog)
    text = (tmp_path / "tablas" / "r1.md").read_text(encoding="utf-8")
    assert "| Valle de Cocora | cocora | 123 | 1 051 |" in text
