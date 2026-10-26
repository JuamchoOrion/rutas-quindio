"""Envolvente convexa con QuickHull (divide y vencerás, implementación propia).

Spec: specs/R3-envolvente-convexa.md

Toda la geometría usa enteros (coordenadas UTM redondeadas a metros), así que los
giros se deciden con un producto cruz exacto, sin errores de redondeo.

Recurrencia: T(n) = T(n₁) + T(n₂) + Θ(n), con n₁ + n₂ ≤ n − 1.
Caso típico Θ(n log n) (o O(n log h)); peor caso Θ(n²) con todos los puntos en el borde.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

Point = tuple[int, int]


def prepare_points(xs_m: Iterable[float], ys_m: Iterable[float]) -> list[Point]:
    """Redondea coordenadas en metros al entero más cercano y elimina duplicados (R3-B01).

    Se usa ``floor(v + 0.5)`` como regla explícita de redondeo. El orden de aparición
    se conserva para que el resultado sea reproducible.
    """
    seen: set[Point] = set()
    points: list[Point] = []
    for x, y in zip(xs_m, ys_m, strict=True):
        point = (math.floor(x + 0.5), math.floor(y + 0.5))
        if point not in seen:
            seen.add(point)
            points.append(point)
    return points


def cross(a: Point, b: Point, p: Point) -> int:
    """Producto cruz de (b − a) × (p − a).

    > 0: ``p`` está a la izquierda del segmento dirigido a → b (giro antihorario).
    = 0: colineales.
    < 0: ``p`` está a la derecha.
    """
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _points_right_of(a: Point, b: Point, candidates: Iterable[Point]) -> list[Point]:
    """Puntos estrictamente a la derecha de a → b; los colineales se descartan (R3-B03)."""
    return [p for p in candidates if cross(a, b, p) < 0]


def quickhull(points: Sequence[Point]) -> list[Point]:
    """Vértices de la envolvente convexa en sentido antihorario (R3-B04).

    Empieza en el punto de menor ``x`` (menor ``y`` en empate). Los puntos colineales
    sobre un lado no son vértices. Se asume que no hay puntos repetidos
    (usar :func:`prepare_points`).

    Divide: la recta entre los extremos izquierdo ``A`` y derecho ``B`` separa los
    puntos en la cadena inferior (derecha de A → B) y la superior (derecha de B → A).
    En cada cadena, el punto ``C`` más lejano de la recta es vértice; los puntos dentro
    del triángulo se descartan y se resuelven los subproblemas (a, C) y (C, b).

    La recursión se simula con una pila explícita (R3-B06): no hay límite de
    profundidad aunque todos los puntos sean vértices.
    """
    if len(points) <= 1:
        return list(points)

    leftmost = min(points)   # tuplas: compara x y luego y
    rightmost = max(points)
    if leftmost == rightmost:
        return [leftmost]

    hull: list[Point] = [leftmost]
    _hull_chain(leftmost, rightmost, _points_right_of(leftmost, rightmost, points), hull)
    hull.append(rightmost)
    _hull_chain(rightmost, leftmost, _points_right_of(rightmost, leftmost, points), hull)
    return hull


def _hull_chain(a: Point, b: Point, outside: list[Point], hull: list[Point]) -> None:
    """Agrega a ``hull``, en orden, los vértices estrictamente entre ``a`` y ``b``.

    ``outside`` son los puntos a la derecha de a → b. La pila contiene dos tipos de
    tareas: resolver un segmento ``(a, b, puntos)`` o emitir un vértice. Se apilan en
    orden inverso (segmento derecho, vértice, segmento izquierdo) para que al
    desapilar se produzca el recorrido antihorario a → … → C → … → b.
    """
    solve, emit = "solve", "emit"
    stack: list[tuple] = [(solve, a, b, outside)]
    while stack:
        task = stack.pop()
        if task[0] == emit:
            hull.append(task[1])
            continue

        _, seg_a, seg_b, candidates = task
        if not candidates:
            continue

        # El más lejano a la recta es el de |cross| máximo (cross < 0 aquí).
        farthest = min(candidates, key=lambda p: cross(seg_a, seg_b, p))
        right_of_a_c = _points_right_of(seg_a, farthest, candidates)
        right_of_c_b = _points_right_of(farthest, seg_b, candidates)

        stack.append((solve, farthest, seg_b, right_of_c_b))
        stack.append((emit, farthest))
        stack.append((solve, seg_a, farthest, right_of_a_c))
