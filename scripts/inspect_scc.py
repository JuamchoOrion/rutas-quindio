"""R1-B12 — Muestra qué algoritmo de CFC usa la versión instalada de OSMnx/NetworkX.

Uso: python scripts/inspect_scc.py
Copiar la salida (versiones y notas del docstring) al documento técnico.
"""

import inspect

import networkx as nx
import osmnx as ox


def main() -> None:
    print(f"OSMnx {ox.__version__} | NetworkX {nx.__version__}\n")
    print("=== osmnx.truncate.largest_component (código fuente) ===")
    print(inspect.getsource(ox.truncate.largest_component))
    doc = inspect.getdoc(nx.strongly_connected_components) or ""
    print("=== networkx.strongly_connected_components: Notas y referencias ===")
    print(doc[doc.find("Notes"):] if "Notes" in doc else doc)


if __name__ == "__main__":
    main()
