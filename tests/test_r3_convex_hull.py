"""Pruebas de specs/R3-envolvente-convexa.md. Cada prueba cita el ID del caso."""

import math
import random

import numpy as np
import pytest
from scipy.spatial import ConvexHull

from rutas.convex_hull import cross, prepare_points, quickhull


def scipy_vertices(points):
    hull = ConvexHull(np.array(points, dtype=np.int64))
    return {points[i] for i in hull.vertices}


def test_R3_C01_square_with_interior_point():
    points = [(2, 2), (4, 4), (0, 0), (4, 0), (0, 4)]
    assert quickhull(points) == [(0, 0), (4, 0), (4, 4), (0, 4)]


def test_R3_C02_collinear_points_on_edges_are_not_vertices():
    square = [(0, 0), (4, 0), (4, 4), (0, 4)]
    midpoints = [(2, 0), (4, 2), (2, 4), (0, 2), (1, 0), (3, 4)]
    assert quickhull(square + midpoints) == square


def test_R3_C03_degenerate_sizes():
    assert quickhull([]) == []
    assert quickhull([(1, 1)]) == [(1, 1)]


def test_R3_C04_all_collinear_returns_extremes():
    assert quickhull([(2, 2), (0, 0), (3, 3), (1, 1)]) == [(0, 0), (3, 3)]


def test_R3_C05_triangle():
    assert quickhull([(0, 0), (5, 1), (2, 6)]) == [(0, 0), (5, 1), (2, 6)]


def test_R3_C06_prepare_rounds_and_deduplicates():
    assert prepare_points([1.4, 1.6, 1.4], [2.4, 0.2, 2.3]) == [(1, 2), (2, 0)]


def test_R3_C10_prepare_rounds_ties_up():
    assert prepare_points([0.5, -0.5], [2.5, -2.5]) == [(1, 3), (0, -2)]


@pytest.mark.parametrize("seed", range(50))
def test_R3_C07_C09_random_clouds_match_scipy(seed):
    rng = random.Random(seed)
    n = rng.randint(10, 2000)
    points = prepare_points(
        [rng.uniform(0, 10_000) for _ in range(n)], [rng.uniform(0, 10_000) for _ in range(n)]
    )
    hull = quickhull(points)
    assert set(hull) == scipy_vertices(points)
    # R3-C09: recorrido antihorario estricto (todo giro a la izquierda).
    for i in range(len(hull)):
        a, b, c = hull[i], hull[(i + 1) % len(hull)], hull[(i + 2) % len(hull)]
        assert cross(a, b, c) > 0


def test_R3_C07_clustered_cloud_like_a_road_network():
    """Puntos agrupados en "cascos urbanos" unidos por "vías": la forma de los datos reales."""
    rng = random.Random(7)
    xs, ys = [], []
    for cx, cy in [(0, 0), (8_000, 3_000), (15_000, -2_000), (5_000, 12_000)]:
        for _ in range(800):
            xs.append(rng.gauss(cx, 600))
            ys.append(rng.gauss(cy, 600))
    for t in range(2_000):
        xs.append(t * 7.5)
        ys.append(t * 1.5 + rng.uniform(-30, 30))
    points = prepare_points(xs, ys)
    assert set(quickhull(points)) == scipy_vertices(points)


def test_R3_C08_points_on_circle_worst_case_no_recursion_error():
    radius = 1_000_000
    points = prepare_points(
        [radius * math.cos(2 * math.pi * i / 360) for i in range(360)],
        [radius * math.sin(2 * math.pi * i / 360) for i in range(360)],
    )
    hull = quickhull(points)
    assert len(hull) == len(points)
    assert set(hull) == scipy_vertices(points)
