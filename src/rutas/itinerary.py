"""Itinerario de un día ordenado con Held-Karp (R4, punto 4).

Spec: specs/R4-ruta-optima.md (R4-B15 a R4-B18, casos R4-C08 y R4-C09).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from rutas.tsp import START, Matrix, held_karp, instance_matrix, validate_matrix

WORKDAY_S = 11 * 3600          # Jornada de 11 h (enunciado R4.4).
MIN_ATTRACTIONS = 6
MAX_ATTRACTIONS = 8


@dataclass(frozen=True)
class ItineraryRow:
    """Una fila de la tabla del anexo (los minutos y horas sin redondear)."""

    position: int | str          # 1, 2, … o "Regreso"
    place: str
    travel_min: float            # desplazamiento desde el lugar anterior
    visit_min: float | None      # None en la fila de regreso
    cumulative_h: float


@dataclass(frozen=True)
class Removal:
    """Atractivo quitado para que la jornada quepa, con la justificación numérica."""

    place: str
    saving_s: float              # cuánto se acortaba la jornada al quitarlo
    day_before_s: float          # duración de la jornada antes de quitarlo


@dataclass
class DayPlan:
    order: list[int]                         # índices de ``costs``; empieza y termina en 0
    rows: list[ItineraryRow]
    travel_total_s: float
    visit_total_s: float
    removed: list[Removal] = field(default_factory=list)

    @property
    def total_s(self) -> float:
        return self.travel_total_s + self.visit_total_s

    def fits(self, budget_s: float = WORKDAY_S) -> bool:
        return self.total_s <= budget_s


def plan_day(
    costs: Matrix,
    labels: Sequence[str],
    visit_min: Sequence[float],
    budget_s: float = WORKDAY_S,
) -> DayPlan:
    """Ordena los atractivos con Held-Karp y quita los necesarios para caber en la jornada.

    Args:
        costs: matriz de la instancia; el índice 0 es el lugar de partida.
        labels: nombre de cada índice de ``costs``.
        visit_min: duración de la visita (minutos) de cada índice; se ignora la del 0.
        budget_s: duración máxima de la jornada en segundos.

    Regla de eliminación (R4-B17): se quita el atractivo con mayor ahorro
    ``d(prev, j) + visita(j) + d(j, next) − d(prev, next)`` en el recorrido actual
    (empate → mayor visita) y se recalcula Held-Karp, hasta que la jornada quepa.
    """
    k = validate_matrix(costs)
    if not MIN_ATTRACTIONS <= k <= MAX_ATTRACTIONS:
        raise ValueError(
            f"Se requieren entre {MIN_ATTRACTIONS} y {MAX_ATTRACTIONS} atractivos; hay {k}"
        )
    if len(labels) != k + 1 or len(visit_min) != k + 1:
        raise ValueError("labels y visit_min deben tener una entrada por fila de costs")

    visit_s = [0.0] + [60.0 * minutes for minutes in visit_min[1:]]
    active = list(range(1, k + 1))
    removed: list[Removal] = []

    while True:
        order = _optimal_order(costs, active)
        travel_s = sum(costs[a][b] for a, b in zip(order, order[1:]))
        visits_s = sum(visit_s[p] for p in active)
        day_s = travel_s + visits_s
        if day_s <= budget_s or not active:
            break

        removal_index, saving = _best_removal(costs, visit_s, order)
        removed.append(Removal(labels[removal_index], saving, day_s))
        active.remove(removal_index)

    return DayPlan(
        order=order,
        rows=_build_rows(costs, labels, visit_s, order),
        travel_total_s=travel_s,
        visit_total_s=visits_s,
        removed=removed,
    )


def _optimal_order(costs: Matrix, active: list[int]) -> list[int]:
    """Recorrido de Held-Karp sobre ``active``, traducido a índices de ``costs``."""
    sub_tour = held_karp(instance_matrix(costs, START, active))
    return [START if t == START else active[t - 1] for t in sub_tour.order]


def _best_removal(costs: Matrix, visit_s: list[float], order: list[int]) -> tuple[int, float]:
    """Atractivo cuyo retiro acorta más la jornada, y ese ahorro en segundos."""
    best_place, best_saving = -1, -1.0
    for position in range(1, len(order) - 1):
        prev, place, nxt = order[position - 1], order[position], order[position + 1]
        saving = costs[prev][place] + visit_s[place] + costs[place][nxt] - costs[prev][nxt]
        is_better = saving > best_saving or (
            saving == best_saving and visit_s[place] > visit_s[best_place]
        )
        if is_better:
            best_place, best_saving = place, saving
    return best_place, best_saving


def _build_rows(
    costs: Matrix, labels: Sequence[str], visit_s: list[float], order: list[int]
) -> list[ItineraryRow]:
    rows: list[ItineraryRow] = []
    elapsed_s = 0.0
    for position, (prev, place) in enumerate(zip(order, order[1:]), start=1):
        travel = costs[prev][place]
        is_return = place == START
        elapsed_s += travel + (0.0 if is_return else visit_s[place])
        rows.append(
            ItineraryRow(
                position="Regreso" if is_return else position,
                place=labels[place],
                travel_min=travel / 60.0,
                visit_min=None if is_return else visit_s[place] / 60.0,
                cumulative_h=elapsed_s / 3600.0,
            )
        )
    return rows
