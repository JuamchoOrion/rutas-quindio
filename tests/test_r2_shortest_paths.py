"""Pruebas de specs/R2-caminos-minimos.md. Cada prueba cita el ID del caso."""

import math
import random

import networkx as nx
import pytest

from rutas.graph import Graph
from rutas.shortest_paths import (
    dijkstra_all,
    dijkstra_heap,
    dijkstra_linear,
    travel_time_matrix,
)

BOTH_VERSIONS = pytest.mark.parametrize("dijkstra", [dijkstra_linear, dijkstra_heap])


@pytest.fixture
def reference_graph() -> Graph:
    """G_ref de la spec, resuelto a mano: distancias desde 0 = [0, 3, 1, 4, 7]."""
    edges = [(0, 1, 4), (0, 2, 1), (2, 1, 2), (1, 3, 1), (2, 3, 5), (3, 4, 3)]
    return Graph.from_edges(range(5), edges)


def random_graph(seed: int, n_nodes: int, n_edges: int) -> tuple[Graph, nx.DiGraph]:
    """Grafo aleatorio propio y su equivalente en NetworkX (solo para verificar)."""
    rng = random.Random(seed)
    edges = []
    for _ in range(n_edges):
        u, v = rng.randrange(n_nodes), rng.randrange(n_nodes)
        if u != v:
            edges.append((u, v, round(rng.uniform(1, 100), 3)))
    reference = nx.DiGraph()
    reference.add_nodes_from(range(n_nodes))
    for u, v, w in edges:  # Con aristas paralelas, NetworkX DiGraph conserva la menor.
        if not reference.has_edge(u, v) or reference[u][v]["weight"] > w:
            reference.add_edge(u, v, weight=w)
    return Graph.from_edges(range(n_nodes), edges), reference


@BOTH_VERSIONS
def test_R2_C01_hand_solved_route(dijkstra, reference_graph):
    result = dijkstra(reference_graph, 0, 4)
    assert result.cost == 7
    assert result.path == [0, 2, 1, 3, 4]


@BOTH_VERSIONS
def test_R2_C02_source_equals_target(dijkstra, reference_graph):
    result = dijkstra(reference_graph, 0, 0)
    assert (result.cost, result.path, result.explored) == (0, [0], 1)


@BOTH_VERSIONS
def test_R2_C03_unreachable_target(dijkstra, reference_graph):
    result = dijkstra(reference_graph, 4, 0)
    assert math.isinf(result.cost)
    assert result.path == []
    assert result.explored == 1  # Solo el nodo 4 es alcanzable desde 4 (R2-B06).


@BOTH_VERSIONS
def test_R2_C04_early_stop_counts_each_node_once(dijkstra, reference_graph):
    assert dijkstra(reference_graph, 0, 2).explored == 2


def test_R2_C05_all_distances(reference_graph):
    assert dijkstra_all(reference_graph, 0) == [0, 3, 1, 4, 7]


@BOTH_VERSIONS
def test_R2_C06_parallel_edges_use_cheapest(dijkstra):
    graph = Graph.from_edges([0, 1], [(0, 1, 5), (0, 1, 2)])
    assert dijkstra(graph, 0, 1).cost == 2


@pytest.mark.parametrize("seed", range(30))
def test_R2_C07_C08_random_graphs_match_networkx(seed):
    graph, reference = random_graph(seed, n_nodes=25, n_edges=70)
    for source in range(graph.n_nodes):
        expected = nx.single_source_dijkstra_path_length(reference, source)
        for target in range(graph.n_nodes):
            linear = dijkstra_linear(graph, source, target)
            heap = dijkstra_heap(graph, source, target)
            if target not in expected:
                assert math.isinf(linear.cost) and math.isinf(heap.cost)
                continue
            assert linear.cost == pytest.approx(expected[target], rel=1e-9)
            assert heap.cost == pytest.approx(linear.cost, rel=1e-9)  # R2-B11
            for result in (linear, heap):  # R2-C08: la ruta es real y cuesta lo reportado.
                assert result.path[0] == source and result.path[-1] == target
                steps = list(zip(result.path, result.path[1:]))
                assert sum(graph.edge_weight(u, v) for u, v in steps) == pytest.approx(result.cost)


def test_R2_C09_matrix_is_asymmetric_with_zero_diagonal():
    graph = Graph.from_edges(
        "abc", [("a", "b", 1), ("b", "a", 9), ("b", "c", 1), ("c", "a", 1)]
    )
    sources = [graph.index_of(x) for x in "abc"]
    matrix = travel_time_matrix(graph, sources)
    assert [matrix[i][i] for i in range(3)] == [0, 0, 0]
    assert matrix[0][1] == 1 and matrix[1][0] == 2  # b → c → a es más rápido que b → a.
    assert matrix[0][1] != matrix[1][0]


def test_R2_C10_negative_weight_is_rejected():
    with pytest.raises(ValueError):
        Graph.from_edges([0, 1], [(0, 1, -1)])
