"""Pruebas de specs/R5-aplicacion.md. Cada prueba cita el ID del caso."""

import json

import networkx as nx
import pytest

from rutas import paths
from rutas.app_support import compare_tours, hull_latlons, result_files, route_latlons
from rutas.catalog import load_catalog
from rutas.geo import to_latlon
from rutas.graph import Graph

# Contraejemplo CE de specs/R4-ruta-optima.md (segundos).
CE = [
    [0, 1, 10, 10],
    [10, 0, 2, 1],
    [10, 10, 0, 1],
    [1, 10, 10, 0],
]
VISIT_MIN = 10
APP_TIMEOUT_S = 120
N_ATTRACTIONS = 7          # R5-C04: dentro del rango de 6 a 8.


def test_R5_C06_compare_tours_gap_over_travel():
    """Brecha sobre los desplazamientos (R4-B14); los totales suman las mismas visitas."""
    comparison = compare_tours(CE, [0, VISIT_MIN, VISIT_MIN, VISIT_MIN])
    assert comparison.optimal.travel_s == 5
    assert comparison.heuristic.travel_s == 22
    assert comparison.optimal.total_s == 1805
    assert comparison.heuristic.total_s == 1822
    assert comparison.difference_s == 17
    assert comparison.gap_pct == pytest.approx(340.0)
    assert comparison.optimal.order == [0, 1, 2, 3, 0]
    assert comparison.heuristic.order == [0, 1, 3, 2, 0]


def test_R5_C07_route_latlons_in_path_order():
    nx_graph = nx.MultiDiGraph()
    for node_id, (lat, lon) in {10: (4.5, -75.6), 20: (4.6, -75.7), 30: (4.7, -75.8)}.items():
        nx_graph.add_node(node_id, y=lat, x=lon)
    graph = Graph.from_edges([10, 20, 30], [(10, 20, 1.0), (20, 30, 1.0)])
    path = [graph.index_of(10), graph.index_of(20), graph.index_of(30)]
    assert route_latlons(nx_graph, graph, path) == [(4.5, -75.6), (4.6, -75.7), (4.7, -75.8)]


def test_R5_C08_hull_latlons_from_r3_format(tmp_path):
    vertices = [[420000, 495000], [440000, 495000], [440000, 520000], [420000, 520000]]
    hull = tmp_path / "envolvente_red.json"
    hull.write_text(json.dumps({"crs": "EPSG:32618", "n_puntos": 100, "vertices": vertices}))
    assert hull_latlons(hull) == [to_latlon(x, y) for x, y in vertices]


def test_R5_C09_missing_files_do_not_fail(tmp_path):
    assert hull_latlons(tmp_path / "no_existe.json") is None
    assert result_files(tmp_path / "no_existe", ".csv") == []
    wrong_crs = tmp_path / "envolvente_red.json"
    wrong_crs.write_text(json.dumps({"crs": "EPSG:4326", "vertices": []}))
    with pytest.raises(ValueError, match="EPSG:32618"):
        hull_latlons(wrong_crs)


def test_R5_C10_result_files_skip_subfolders(tmp_path):
    for name in ("b.csv", "a.csv", "grafica.png", "notas.md"):
        (tmp_path / name).write_text("x")
    (tmp_path / "corrida_1").mkdir()
    (tmp_path / "corrida_1" / "c.csv").write_text("x")
    assert [p.name for p in result_files(tmp_path, ".csv")] == ["a.csv", "b.csv"]
    assert [p.name for p in result_files(tmp_path, ".png")] == ["grafica.png"]


@pytest.mark.slow
def test_R5_C11_app_runs_without_exceptions():
    """La app completa se ejecuta, calcula una ruta y un itinerario de 7 atractivos."""
    if not paths.NETWORK_GRAPHML.exists() or not paths.RESULTS.is_dir():
        pytest.skip("Faltan data/processed/ o results/ (ejecutar R1 y R2)")
    testing = pytest.importorskip("streamlit.testing.v1")

    app = testing.AppTest.from_file(str(paths.ROOT / "app" / "app.py"),
                                    default_timeout=APP_TIMEOUT_S).run()
    assert not app.exception

    app.button[0].click().run()                    # Calcular ruta (Armenia → Salento)
    assert not app.exception

    if (paths.R2 / "matriz_tiempos.csv").exists():
        attractions = [place.id for place in load_catalog(paths.CATALOG_CSV)
                       if place.category == "atractivo"][:N_ATTRACTIONS]
        app.multiselect(key="itinerary_places").set_value(attractions).run()
        app.button[1].click().run()                # Calcular itinerario
        assert not app.exception
