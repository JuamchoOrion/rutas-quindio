"""Caminos mínimos con Dijkstra (implementación propia).

Spec: specs/R2-caminos-minimos.md

Dos versiones con la misma interfaz:

* :func:`dijkstra_linear` busca el mínimo recorriendo los V nodos: O(V²).
* :func:`dijkstra_heap` usa ``heapq`` (heap binario) con eliminación perezosa:
  O((V + E) log V).

Invariante (R2): al extraer un nodo ``u``, ``dist[u]`` es la distancia mínima real
desde el origen. Requiere pesos no negativos, que :class:`~rutas.graph.Graph`
garantiza al construirse.
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Sequence
from dataclasses import dataclass

from rutas.graph import Graph

NO_PREDECESSOR = -1


@dataclass(frozen=True)
class PathResult:
    """Resultado de una consulta origen-destino.

    Attributes:
        cost: tiempo total en segundos; ``math.inf`` si el destino es inalcanzable.
        path: índices de nodos desde el origen hasta el destino (``[]`` si no hay camino).
        explored: nodos extraídos como definitivos (cada uno se cuenta una vez).
    """

    cost: float
    path: list[int]
    explored: int


def _reconstruct_path(predecessor: Sequence[int], source: int, target: int) -> list[int]:
    """Recorre los predecesores desde ``target`` hasta ``source`` (R2-B04). O(longitud)."""
    path = [target]
    while path[-1] != source:
        path.append(predecessor[path[-1]])
    path.reverse()
    return path


def _check_node(graph: Graph, node: int, role: str) -> None:
    if not 0 <= node < graph.n_nodes:
        raise IndexError(f"El {role} {node} no está en el grafo (V = {graph.n_nodes})")


def dijkstra_linear(graph: Graph, source: int, target: int) -> PathResult:
    """Dijkstra buscando el mínimo con un recorrido lineal. Tiempo O(V²), memoria O(V).

    Se detiene al extraer ``target`` (R2-B03).
    """
    _check_node(graph, source, "origen")
    _check_node(graph, target, "destino")

    n = graph.n_nodes
    dist = [math.inf] * n
    predecessor = [NO_PREDECESSOR] * n
    settled = [False] * n
    dist[source] = 0.0
    explored = 0

    while True:
        # Selección del mínimo: recorrido lineal de los V nodos (R2-B07).
        u = NO_PREDECESSOR
        best = math.inf
        for v in range(n):
            if not settled[v] and dist[v] < best:
                best = dist[v]
                u = v
        if u == NO_PREDECESSOR:  # No quedan nodos alcanzables sin extraer.
            return PathResult(math.inf, [], explored)

        settled[u] = True
        explored += 1
        if u == target:
            return PathResult(dist[u], _reconstruct_path(predecessor, source, target), explored)

        for v, weight in graph.adjacency[u]:
            candidate = dist[u] + weight
            if candidate < dist[v]:
                dist[v] = candidate
                predecessor[v] = u


def _dijkstra_heap_core(
    graph: Graph, source: int, target: int | None
) -> tuple[list[float], list[int], int]:
    """Núcleo con cola de prioridad. Si ``target`` es None recorre todo el grafo.

    Devuelve ``(dist, predecessor, explored)``.
    """
    n = graph.n_nodes
    dist = [math.inf] * n
    predecessor = [NO_PREDECESSOR] * n
    settled = [False] * n
    dist[source] = 0.0
    explored = 0
    heap: list[tuple[float, int]] = [(0.0, source)]

    while heap:
        d_u, u = heapq.heappop(heap)
        if settled[u]:
            continue  # Entrada obsoleta (eliminación perezosa, R2-B08): no se cuenta.
        settled[u] = True
        explored += 1
        if u == target:
            break

        for v, weight in graph.adjacency[u]:
            candidate = d_u + weight
            if candidate < dist[v]:
                dist[v] = candidate
                predecessor[v] = u
                heapq.heappush(heap, (candidate, v))

    return dist, predecessor, explored


def dijkstra_heap(graph: Graph, source: int, target: int) -> PathResult:
    """Dijkstra con cola de prioridad. Tiempo O((V + E) log V), memoria O(V + E).

    Se detiene al extraer ``target`` (R2-B03).
    """
    _check_node(graph, source, "origen")
    _check_node(graph, target, "destino")

    dist, predecessor, explored = _dijkstra_heap_core(graph, source, target)
    if math.isinf(dist[target]):
        return PathResult(math.inf, [], explored)
    return PathResult(dist[target], _reconstruct_path(predecessor, source, target), explored)


def dijkstra_all(graph: Graph, source: int) -> list[float]:
    """Distancias desde ``source`` a todos los nodos, sin destino (R2-B09)."""
    _check_node(graph, source, "origen")
    dist, _, _ = _dijkstra_heap_core(graph, source, target=None)
    return dist


def travel_time_matrix(graph: Graph, sources: Sequence[int]) -> list[list[float]]:
    """Matriz ``M[i][j]`` = tiempo de ``sources[i]`` a ``sources[j]`` (R2-B10).

    Ejecuta :func:`dijkstra_all` una vez por fila. No asume simetría.
    """
    matrix = []
    for source in sources:
        dist = dijkstra_all(graph, source)
        matrix.append([dist[target] for target in sources])
    return matrix
