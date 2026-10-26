"""Pruebas de specs/R1-modelo-red.md. Cada prueba cita el ID del caso."""

import numpy as np
import pytest

from rutas.catalog import MIN_PER_CATEGORY, Place, validate_catalog
from rutas.geo import nearest_node, to_latlon, to_utm
from rutas.graph import Graph
from rutas.network_model import (
    DEFAULT_SPEED_KMH,
    edge_speed_kmh,
    estimate_memory,
    parse_maxspeed,
    travel_time_s,
)

PLAZA_BOLIVAR_ARMENIA = (4.5339, -75.6811)  # Aproximada; solo para la prueba de proyección.


def test_R1_C01_plain_number():
    assert parse_maxspeed("50") == 50.0


def test_R1_C02_mph():
    assert parse_maxspeed("30 mph") == pytest.approx(48.28, abs=0.01)


def test_R1_C03_list_takes_minimum():
    assert parse_maxspeed(["60", "40"]) == 40.0


@pytest.mark.parametrize("raw", ["signals", None, "0", "500"])
def test_R1_C04_unparseable_or_implausible(raw):
    assert parse_maxspeed(raw) is None


def test_R1_C05_default_by_highway_type():
    assert edge_speed_kmh(None, "residential") == (DEFAULT_SPEED_KMH["residential"], "highway_default")
    assert edge_speed_kmh(None, ["tipo_raro", "primary"]) == (DEFAULT_SPEED_KMH["primary"], "highway_default")
    assert edge_speed_kmh("45", "primary") == (45.0, "maxspeed")


def test_R1_C06_fallback():
    assert edge_speed_kmh(None, "tipo_raro") == (30.0, "fallback")


def test_R1_C07_travel_time():
    assert travel_time_s(1000, 36) == pytest.approx(100.0)


def test_R1_C08_memory_estimate():
    estimate = estimate_memory(1000, 2500)
    assert estimate.matrix_mb == pytest.approx(8.0)
    assert estimate.lists_mb == pytest.approx(0.068)
    assert estimate.density == pytest.approx(0.0025)


def test_R1_C09_utm_projection_of_armenia():
    x, y = to_utm(*PLAZA_BOLIVAR_ARMENIA)
    assert x == pytest.approx(4.24e5, abs=2_000)
    assert y == pytest.approx(5.01e5, abs=2_000)
    lat, lon = to_latlon(x, y)  # Ida y vuelta.
    assert (lat, lon) == pytest.approx(PLAZA_BOLIVAR_ARMENIA, abs=1e-7)


def test_R1_C10_nearest_node():
    xs, ys = np.array([0.0, 10.0, 100.0]), np.array([0.0, 10.0, 100.0])
    assert nearest_node(13.0, 14.0, xs, ys) == (1, 5.0)


def test_R1_C13_parallel_edges_are_kept():
    graph = Graph.from_edges(["a", "b"], [("a", "b", 3.0), ("a", "b", 1.0)])
    assert graph.n_edges == 2
    assert graph.edge_weight(0, 1) == 1.0


# --------------------------------------------------------------------------- #
# Catálogo
# --------------------------------------------------------------------------- #
def valid_catalog() -> list[Place]:
    places = [Place("armenia", "Armenia", "Armenia", "cabecera", 4.53, -75.68)]
    for category, minimum in MIN_PER_CATEGORY.items():
        start = 1 if category == "cabecera" else 0
        for i in range(start, minimum):
            places.append(
                Place(
                    f"{category}_{i}", f"{category} {i}", "Armenia", category, 4.5, -75.7,
                    visit_min=60 if category == "atractivo" else None,
                    visit_source="criterio del grupo" if category == "atractivo" else "",
                )
            )
    return places


def test_valid_catalog_has_no_errors():
    assert validate_catalog(valid_catalog()) == []


def test_R1_C11_missing_place():
    places = [p for p in valid_catalog() if p.id != "acopio_0"]
    errors = validate_catalog(places)
    assert any("39" in e for e in errors)
    assert any("acopio" in e for e in errors)


def test_R1_C12_attraction_without_duration():
    places = valid_catalog()
    index = next(i for i, p in enumerate(places) if p.category == "atractivo")
    original = places[index]
    places[index] = Place(original.id, original.name, original.municipality, "atractivo",
                          original.lat, original.lon, None, "")
    errors = validate_catalog(places)
    assert any(original.id in e and "duración" in e for e in errors)


def test_catalog_coordinates_outside_quindio():
    places = valid_catalog()
    places.append(Place("bogota", "Bogotá", "Bogotá", "acopio", 4.71, -74.07))
    assert any("bogota" in e for e in validate_catalog(places))
