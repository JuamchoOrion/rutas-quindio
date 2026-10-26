"""Grafo dirigido y ponderado con listas de adyacencia.

Spec: specs/R1-modelo-red.md (R1-B05, R1-C13) y specs/R2-caminos-minimos.md (R2-B01).

Los nodos se identifican internamente con índices consecutivos ``0..V-1`` para que
los algoritmos usen arreglos (``list``) en lugar de diccionarios. El objeto guarda
la traducción entre esos índices y los identificadores originales (ids de OSM).
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass, field

# Una entrada de la lista de adyacencia de u: (vecino v, peso w(u, v)).
Neighbor = tuple[int, float]


@dataclass
class Graph:
    """Grafo dirigido con listas de adyacencia.

    Attributes:
        node_ids: ``node_ids[i]`` es el identificador original del nodo con índice ``i``.
        adjacency: ``adjacency[u]`` es la lista de pares ``(v, peso)`` de las aristas que
            salen de ``u``. Se admiten aristas paralelas (la red de OSM las tiene).
    """

    node_ids: list[Hashable]
    adjacency: list[list[Neighbor]]
    _index_of: dict[Hashable, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if len(self.node_ids) != len(self.adjacency):
            raise ValueError("node_ids y adjacency deben tener la misma longitud")
        self._index_of = {node_id: i for i, node_id in enumerate(self.node_ids)}
        if len(self._index_of) != len(self.node_ids):
            raise ValueError("Hay identificadores de nodo repetidos")

    @classmethod
    def from_edges(
        cls,
        node_ids: Sequence[Hashable],
        edges: Iterable[tuple[Hashable, Hashable, float]],
    ) -> Graph:
        """Construye el grafo a partir de aristas ``(u_id, v_id, peso)``.

        Costo: O(V + E) en tiempo y memoria.

        Raises:
            ValueError: si una arista usa un nodo desconocido o tiene peso negativo,
                infinito o NaN (Dijkstra exige pesos no negativos, R2-B01).
        """
        index_of = {node_id: i for i, node_id in enumerate(node_ids)}
        adjacency: list[list[Neighbor]] = [[] for _ in node_ids]
        for u_id, v_id, weight in edges:
            if u_id not in index_of or v_id not in index_of:
                raise ValueError(f"Arista ({u_id}, {v_id}) con un nodo desconocido")
            if not math.isfinite(weight) or weight < 0:
                raise ValueError(
                    f"Peso inválido {weight} en ({u_id}, {v_id}): debe ser finito y >= 0"
                )
            adjacency[index_of[u_id]].append((index_of[v_id], float(weight)))
        return cls(list(node_ids), adjacency)

    @classmethod
    def from_networkx(cls, nx_graph, weight: str = "travel_time_s") -> Graph:
        """Construye el grafo desde un (Multi)DiGraph de NetworkX/OSMnx.

        Solo se usa NetworkX como contenedor de los datos ya descargados; ningún
        algoritmo de NetworkX interviene en la construcción.
        """
        node_ids = list(nx_graph.nodes)
        edges = ((u, v, data[weight]) for u, v, data in nx_graph.edges(data=True))
        return cls.from_edges(node_ids, edges)

    @property
    def n_nodes(self) -> int:
        return len(self.adjacency)

    @property
    def n_edges(self) -> int:
        return sum(len(neighbors) for neighbors in self.adjacency)

    def index_of(self, node_id: Hashable) -> int:
        """Índice interno del nodo con identificador ``node_id``."""
        return self._index_of[node_id]

    def ids_of(self, indices: Iterable[int]) -> list[Hashable]:
        """Traduce una secuencia de índices (por ejemplo, una ruta) a identificadores."""
        return [self.node_ids[i] for i in indices]

    def edge_weight(self, u: int, v: int) -> float:
        """Menor peso entre las aristas paralelas ``u → v`` (``inf`` si no hay)."""
        return min((w for x, w in self.adjacency[u] if x == v), default=math.inf)
