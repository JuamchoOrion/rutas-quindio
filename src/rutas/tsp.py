"""Problema del viajante asimétrico (ATSP): métodos exactos y heurística voraz.

Spec: specs/R4-ruta-optima.md

Convención de una instancia: ``costs`` es una matriz cuadrada de tamaño ``n = k + 1``;
el índice 0 es el lugar de partida y ``1..k`` son los lugares a visitar.
Un recorrido es ``[0, v1, ..., vk, 0]``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

Matrix = Sequence[Sequence[float]]
START = 0


@dataclass(frozen=True)
class Tour:
    """Recorrido cerrado que sale de 0 y vuelve a 0, con su costo total en segundos."""

    order: list[int]
    cost: float


def validate_matrix(costs: Matrix) -> int:
    """Valida R4-B01 y devuelve ``k`` (lugares a visitar sin contar el inicio).

    Raises:
        ValueError: si la matriz está vacía, no es cuadrada o tiene valores negativos o NaN.
    """
    n = len(costs)
    if n == 0:
        raise ValueError("La matriz de costos está vacía")
    for i, row in enumerate(costs):
        if len(row) != n:
            raise ValueError(f"La matriz no es cuadrada: la fila {i} tiene {len(row)} columnas")
        for j, value in enumerate(row):
            if math.isnan(value) or value < 0:
                raise ValueError(f"Costo inválido costs[{i}][{j}] = {value}")
    return n - 1


def tour_cost(costs: Matrix, order: Sequence[int]) -> float:
    """Suma de ``costs[order[i]][order[i+1]]``. O(longitud del recorrido)."""
    return sum(costs[a][b] for a, b in zip(order, order[1:]))


def _trivial_tour(costs: Matrix, k: int) -> Tour | None:
    """Casos ``k = 0`` y ``k = 1`` (R4-B02): un único recorrido posible."""
    if k == 0:
        return Tour([START, START], 0.0)
    if k == 1:
        order = [START, 1, START]
        return Tour(order, tour_cost(costs, order))
    return None


# --------------------------------------------------------------------------- #
# Fuerza bruta
# --------------------------------------------------------------------------- #
def brute_force_tsp(costs: Matrix) -> Tour:
    """Evalúa las k! permutaciones de ``1..k`` (inicio fijo) por backtracking.

    No hay poda (R4-B05): cada permutación se recorre completa. El costo del prefijo
    se acumula al descender para no recalcularlo, por lo que el árbol tiene
    ≈ e·k! nodos y el tiempo es Θ(k!). Memoria O(k) (la pila de la recursión).
    """
    k = validate_matrix(costs)
    trivial = _trivial_tour(costs, k)
    if trivial is not None:
        return trivial

    best_cost = math.inf
    best_order: list[int] = []
    current = [START]
    used = [False] * (k + 1)
    used[START] = True

    def extend(prefix_cost: float) -> None:
        nonlocal best_cost, best_order
        last = current[-1]
        if len(current) == k + 1:  # Permutación completa: cerrar el ciclo.
            total = prefix_cost + costs[last][START]
            if total < best_cost:
                best_cost = total
                best_order = current + [START]
            return
        for place in range(1, k + 1):
            if not used[place]:
                used[place] = True
                current.append(place)
                extend(prefix_cost + costs[last][place])
                current.pop()
                used[place] = False

    extend(0.0)
    return Tour(best_order, best_cost)


# --------------------------------------------------------------------------- #
# Held-Karp
# --------------------------------------------------------------------------- #
def held_karp_table_bytes(k: int, value_bytes: int = 8, parent_bytes: int = 4) -> int:
    """Bytes de las tablas ``C`` y ``P``: 2^k · k celdas cada una (R4-B11)."""
    return (1 << k) * k * (value_bytes + parent_bytes)


def held_karp(costs: Matrix) -> Tour:
    """Programación dinámica sobre subconjuntos. Tiempo Θ(2^k·k²), memoria Θ(2^k·k).

    Estado ``(S, j)``: ``S`` es una máscara de bits sobre los lugares ``1..k`` (el bit
    ``j-1`` representa al lugar ``j``) y ``j ∈ S`` es el último visitado.

        C({j}, j) = d(0, j)
        C(S, j)   = min_{i ∈ S \\ {j}} C(S \\ {j}, i) + d(i, j)
        óptimo    = min_j C(todos, j) + d(j, 0)

    Las tablas se guardan aplanadas: la celda ``(S, j)`` está en ``S * k + (j - 1)``.
    """
    k = validate_matrix(costs)
    trivial = _trivial_tour(costs, k)
    if trivial is not None:
        return trivial

    n_masks = 1 << k
    best = [math.inf] * (n_masks * k)       # C(S, j)
    parent = [-1] * (n_masks * k)           # P(S, j): lugar anterior a j en el óptimo

    for j in range(1, k + 1):               # Casos base: S = {j}.
        best[(1 << (j - 1)) * k + (j - 1)] = costs[START][j]

    # Orden numérico creciente: S \ {j} < S, así que ya está calculado (R4-B09).
    for mask in range(1, n_masks):
        if mask & (mask - 1) == 0:          # Un solo bit: caso base ya cargado.
            continue
        for j in range(1, k + 1):
            bit_j = 1 << (j - 1)
            if not mask & bit_j:
                continue
            previous_mask = mask ^ bit_j
            best_value = math.inf
            best_parent = -1
            for i in range(1, k + 1):
                if previous_mask & (1 << (i - 1)):
                    value = best[previous_mask * k + (i - 1)] + costs[i][j]
                    if value < best_value:
                        best_value = value
                        best_parent = i
            best[mask * k + (j - 1)] = best_value
            parent[mask * k + (j - 1)] = best_parent

    full = n_masks - 1
    best_cost = math.inf
    last = -1
    for j in range(1, k + 1):
        value = best[full * k + (j - 1)] + costs[j][START]
        if value < best_cost:
            best_cost = value
            last = j

    return Tour(_held_karp_path(parent, k, full, last), best_cost)


def _held_karp_path(parent: list[int], k: int, full_mask: int, last: int) -> list[int]:
    """Reconstruye el recorrido siguiendo los predecesores ``P(S, j)`` (R4-B10)."""
    reversed_places = []
    mask, place = full_mask, last
    while place != -1:
        reversed_places.append(place)
        previous = parent[mask * k + (place - 1)]
        mask ^= 1 << (place - 1)
        place = previous
    return [START, *reversed(reversed_places), START]


# --------------------------------------------------------------------------- #
# Heurística voraz
# --------------------------------------------------------------------------- #
def nearest_neighbor_tour(costs: Matrix) -> Tour:
    """Vecino más cercano: siempre al lugar no visitado más rápido de alcanzar (R4-B12).

    Empate → menor índice. Tiempo Θ(k²), memoria O(k).
    """
    k = validate_matrix(costs)
    visited = [False] * (k + 1)
    visited[START] = True
    order = [START]
    current = START

    for _ in range(k):
        next_place = -1
        next_cost = math.inf
        for place in range(1, k + 1):
            if not visited[place] and costs[current][place] < next_cost:
                next_cost = costs[current][place]
                next_place = place
        if next_place == -1:  # Todos inalcanzables (inf): no ocurre dentro de la CFC.
            next_place = visited.index(False)
        visited[next_place] = True
        order.append(next_place)
        current = next_place

    order.append(START)
    return Tour(order, tour_cost(costs, order))


def gap_percent(heuristic_cost: float, optimal_cost: float) -> float:
    """Brecha porcentual de la heurística frente al óptimo (R4-B14)."""
    if optimal_cost == 0:
        return 0.0 if heuristic_cost == 0 else math.inf
    return 100.0 * (heuristic_cost - optimal_cost) / optimal_cost


def instance_matrix(
    full_matrix: Matrix, start: int, places: Sequence[int]
) -> list[list[float]]:
    """Submatriz de una instancia: fila/columna 0 = ``start``; 1..k = ``places``.

    ``start`` y ``places`` son posiciones dentro de ``full_matrix`` (la matriz de R2).
    """
    selection = [start, *places]
    return [[full_matrix[a][b] for b in selection] for a in selection]
