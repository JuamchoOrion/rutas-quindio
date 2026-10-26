"""Pruebas de specs/R4-ruta-optima.md. Cada prueba cita el ID del caso."""

import random

import pytest

from rutas.itinerary import WORKDAY_S, plan_day
from rutas.tsp import (
    Tour,
    brute_force_tsp,
    gap_percent,
    held_karp,
    held_karp_table_bytes,
    instance_matrix,
    nearest_neighbor_tour,
    tour_cost,
)

ALL_METHODS = pytest.mark.parametrize(
    "solve", [brute_force_tsp, held_karp, nearest_neighbor_tour]
)

# Contraejemplo de la spec: el vecino más cercano encuentra 22; el óptimo es 5.
COUNTEREXAMPLE = [
    [0, 1, 10, 10],
    [10, 0, 2, 1],
    [10, 10, 0, 1],
    [1, 10, 10, 0],
]


def random_asymmetric_matrix(rng: random.Random, n: int) -> list[list[float]]:
    return [[0.0 if i == j else round(rng.uniform(60, 3600), 2) for j in range(n)] for i in range(n)]


def assert_valid_tour(tour: Tour, costs) -> None:
    """R4-B03: empieza y termina en 0, visita 1..k una vez y el costo es consistente."""
    k = len(costs) - 1
    assert tour.order[0] == 0 and tour.order[-1] == 0
    assert sorted(tour.order[1:-1]) == list(range(1, k + 1))
    assert tour.cost == pytest.approx(tour_cost(costs, tour.order))


@ALL_METHODS
def test_R4_C01_no_places_to_visit(solve):
    assert solve([[0]]) == Tour([0, 0], 0.0)


@ALL_METHODS
def test_R4_C02_single_place(solve):
    tour = solve([[0, 3], [5, 0]])
    assert tour.order == [0, 1, 0] and tour.cost == 8


def test_R4_C03_counterexample_greedy_is_not_optimal():
    for exact in (brute_force_tsp, held_karp):
        assert exact(COUNTEREXAMPLE) == Tour([0, 1, 2, 3, 0], 5)
    greedy = nearest_neighbor_tour(COUNTEREXAMPLE)
    assert greedy == Tour([0, 1, 3, 2, 0], 22)
    assert gap_percent(greedy.cost, 5) == pytest.approx(340.0)


@pytest.mark.parametrize("seed", range(40))
def test_R4_C04_C05_C06_exact_methods_agree(seed):
    rng = random.Random(seed)
    costs = random_asymmetric_matrix(rng, n=rng.randint(3, 9))  # k = 2..8
    brute, dp, greedy = brute_force_tsp(costs), held_karp(costs), nearest_neighbor_tour(costs)
    assert dp.cost == pytest.approx(brute.cost)          # R4-C04
    for tour in (brute, dp, greedy):                     # R4-C05
        assert_valid_tour(tour, costs)
    assert greedy.cost >= dp.cost - 1e-9                 # R4-C06


def test_R4_C07_held_karp_table_size():
    assert held_karp_table_bytes(12) == 589_824


@pytest.mark.parametrize(
    "bad", [[[0, 1], [1]], [[0, -1], [1, 0]], []]
)
def test_R4_C10_invalid_matrix(bad):
    with pytest.raises(ValueError):
        held_karp(bad)


def test_instance_matrix_selects_start_first():
    full = [[0, 1, 2], [3, 0, 4], [5, 6, 0]]
    assert instance_matrix(full, start=2, places=[0]) == [[0, 5], [2, 0]]


# --------------------------------------------------------------------------- #
# Itinerario de un día
# --------------------------------------------------------------------------- #
def day_instance(travel_s: float, visit_min: float, k: int = 6):
    costs = [[0.0 if i == j else travel_s for j in range(k + 1)] for i in range(k + 1)]
    labels = ["Armenia"] + [f"Atractivo {i}" for i in range(1, k + 1)]
    visits = [0.0] + [visit_min] * k
    return costs, labels, visits


def test_R4_C08_day_that_fits():
    costs, labels, visits = day_instance(travel_s=1_200, visit_min=60)  # 7·20 min + 6·60 min
    plan = plan_day(costs, labels, visits)
    assert plan.removed == []
    assert plan.travel_total_s == 7 * 1_200
    assert plan.visit_total_s == 6 * 3_600
    assert plan.total_s <= WORKDAY_S
    assert plan.rows[-1].position == "Regreso"
    assert plan.rows[-1].cumulative_h == pytest.approx(plan.total_s / 3600)
    assert sum(row.travel_min for row in plan.rows) == pytest.approx(plan.travel_total_s / 60)


def test_R4_C09_day_that_does_not_fit_removes_largest_saving():
    costs, labels, visits = day_instance(travel_s=1_800, visit_min=90)
    visits[3] = 240  # 3.5 h de viaje + 11.5 h de visitas = 15 h; quitar el 3 ahorra 4.5 h.
    plan = plan_day(costs, labels, visits)
    assert plan.removed[0].place == "Atractivo 3"
    assert plan.total_s <= WORKDAY_S
    assert "Atractivo 3" not in [row.place for row in plan.rows]
    assert all(r.day_before_s > WORKDAY_S for r in plan.removed)


def test_plan_day_requires_six_to_eight_attractions():
    costs, labels, visits = day_instance(travel_s=60, visit_min=10, k=5)
    with pytest.raises(ValueError):
        plan_day(costs, labels, visits)
