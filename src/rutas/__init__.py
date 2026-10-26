"""Rutas del Paisaje Cultural Cafetero: algoritmos sobre la red vial del Quindío.

Cada módulo implementa una spec de ``specs/``:

* ``graph``           — listas de adyacencia (R1)
* ``network_model``   — velocidades, tiempos y estimación de memoria (R1)
* ``geo``             — UTM 18N y nodo más cercano (R1, R3)
* ``catalog``         — catálogo de lugares (R1)
* ``shortest_paths``  — Dijkstra lineal y con cola de prioridad (R2)
* ``convex_hull``     — QuickHull (R3)
* ``tsp``             — fuerza bruta, Held-Karp y vecino más cercano (R4)
* ``itinerary``       — itinerario de un día (R4)
* ``benchmark``       — protocolo experimental
"""

__version__ = "0.1.0"
