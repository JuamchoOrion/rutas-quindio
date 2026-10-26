# R2 — Caminos mínimos (Dijkstra)

## Contexto

Enunciado, sección 5, requerimiento 2. Se trabaja sobre la CFC de R1 con peso
`travel_time_s`. Dos implementaciones propias de Dijkstra: búsqueda lineal del
mínimo y cola de prioridad. Con la segunda se calcula la matriz de tiempos entre
todos los lugares del catálogo, que usa R4.

Módulo: `src/rutas/shortest_paths.py`. Script: `scripts/run_r2.py`.

## Interfaz

```python
@dataclass(frozen=True)
class PathResult:
    cost: float            # tiempo total en segundos (math.inf si no hay camino)
    path: list[int]        # índices de nodos desde el origen hasta el destino ([] si no hay camino)
    explored: int          # nodos extraídos (marcados como definitivos)

dijkstra_linear(graph: Graph, source: int, target: int) -> PathResult   # O(V²)
dijkstra_heap(graph: Graph, source: int, target: int) -> PathResult     # O((V+E) log V)
dijkstra_all(graph: Graph, source: int) -> list[float]                  # sin destino
travel_time_matrix(graph: Graph, sources: list[int]) -> list[list[float]]
```

Los nodos se manejan por **índice** `0..V-1` (el `Graph` traduce desde y hacia los
identificadores OSM). Así las tablas `dist`, `pred` y `visited` son arreglos y no
diccionarios.

## Comportamiento esperado

- **R2-B01.** Pesos: deben ser **no negativos**. Si el grafo tiene una arista con
  peso negativo, ambas funciones lanzan `ValueError` (se valida al construir el
  `Graph`).
- **R2-B02.** Un nodo cuenta como explorado **una sola vez**, la primera vez que se
  extrae (en la versión con cola, las entradas obsoletas del heap se descartan
  sin contarlas).
- **R2-B03.** Ambas versiones se **detienen al extraer el destino**.
- **R2-B04.** La ruta se reconstruye desde el arreglo de predecesores, empieza en
  `source` y termina en `target`.
- **R2-B05.** `source == target` → `cost = 0`, `path = [source]`, `explored = 1`.
- **R2-B06.** Sin camino → `cost = inf`, `path = []` y `explored` = nodos alcanzables.
- **R2-B07.** Versión lineal: en cada iteración recorre los V nodos para encontrar
  el no visitado de menor distancia finita; si no hay, termina.
- **R2-B08.** Versión con cola: `heapq` con **eliminación perezosa** (lazy deletion):
  al mejorar una distancia se inserta una nueva entrada en lugar de disminuir la
  clave. Costo de `heapq`: `heappush` y `heappop` son O(log n) sobre un heap de
  tamaño n ≤ E + 1 (documentación de Python, módulo `heapq`); como E ≤ V²,
  log E ≤ 2 log V y se conserva O((V + E) log V).
- **R2-B09.** `dijkstra_all` no se detiene y devuelve la distancia a todos los nodos.
- **R2-B10.** `travel_time_matrix[i][j]` = tiempo de `sources[i]` a `sources[j]`;
  la diagonal es 0; no se asume simetría. Se ejecuta `dijkstra_all` una vez por
  fila (|catálogo| ejecuciones).
- **R2-B11.** Verificación: en todo par medido con ambas versiones los costos
  coinciden (tolerancia relativa 1e-9). Las **rutas** pueden diferir si hay
  empates; eso no es un error.

## Argumento de correctitud (para el documento técnico)

**Invariante.** Al inicio de cada iteración, para todo nodo `u` ya extraído,
`dist[u] = δ(s, u)` (la distancia mínima real); y para todo nodo no extraído,
`dist[v]` es la longitud del camino más corto de `s` a `v` cuyos nodos
intermedios están todos extraídos.

**Por qué se puede parar en el destino.** Cuando `t` se extrae, el invariante
garantiza `dist[t] = δ(s, t)`; las iteraciones siguientes solo extraen nodos con
distancia ≥ `dist[t]` y, como los pesos son no negativos, ningún camino que pase
por ellos puede mejorar `dist[t]`.

**Condición sobre los pesos.** `w(u, v) ≥ 0`. Con un peso negativo, un nodo
extraído podría mejorarse después (el argumento de "todo desvío cuesta ≥ 0" se
rompe) y el invariante deja de valer.

Fuente: Cormen, Leiserson, Rivest y Stein, *Introduction to Algorithms*, 4.ª ed.,
sección 22.3 (Teorema 22.6, correctitud de Dijkstra).

## Complejidad esperada

| Versión | Tiempo | Memoria |
|---|---|---|
| Lineal | O(V² + E) = O(V²) | O(V) |
| Cola de prioridad (heap binario, lazy) | O((V + E) log V) | O(V + E) (el heap puede tener hasta E entradas) |
| Matriz n × n de lugares | n · O((V + E) log V) | O(n² + V + E) |

## Experimento

- Cola de prioridad: ≥ 20 pares origen-destino del catálogo.
- Lineal: 10 de esos pares, entre lugares del mismo municipio o de municipios vecinos.
- Archivo `results/r2/dijkstra_mediciones.csv`:
  `origen, destino, version, tiempo_viaje_s, nodos_explorados, tiempo_ms`
  con `version ∈ {lineal, cola_prioridad}`.
- Gráfica: nodos explorados (x) vs tiempo ms (y), un color por versión.
- Cociente `tiempo_lineal / tiempo_cola` en los 10 pares: mediana, mínimo, máximo.
- Matriz: `results/r2/matriz_tiempos.csv`; primera fila y primera columna son ids.

## Casos de prueba

Grafo pequeño de referencia `G_ref` (resuelto a mano):

```
0 →1 (4)   0 →2 (1)   2 →1 (2)   1 →3 (1)   2 →3 (5)   3 →4 (3)
```
Distancias desde 0: `[0, 3, 1, 4, 7]`; ruta 0→4: `[0, 2, 1, 3, 4]`.

| ID | Entrada | Resultado esperado |
|---|---|---|
| R2-C01 | `G_ref`, 0 → 4, ambas versiones | `cost = 7`, `path = [0, 2, 1, 3, 4]` |
| R2-C02 | `G_ref`, 0 → 0 | `cost = 0`, `path = [0]`, `explored = 1` |
| R2-C03 | `G_ref`, 4 → 0 (no hay camino) | `cost = inf`, `path = []` |
| R2-C04 | `G_ref`, 0 → 2 | parada temprana: `explored = 2` (se extraen 0 y 2) |
| R2-C05 | `dijkstra_all(G_ref, 0)` | `[0, 3, 1, 4, 7]` |
| R2-C06 | Grafo con aristas paralelas `0→1 (5)` y `0→1 (2)` | `cost = 2` |
| R2-C07 | 30 grafos aleatorios (semilla fija), todos los pares | lineal = cola = `networkx.dijkstra_path_length` |
| R2-C08 | Rutas devueltas en R2-C07 | la suma de pesos de la ruta es igual a `cost` y cada paso es una arista existente |
| R2-C09 | `travel_time_matrix` sobre un grafo asimétrico | diagonal 0 y `M[i][j] ≠ M[j][i]` donde corresponde |
| R2-C10 | Grafo con peso negativo | `ValueError` al construir |

## Fuera de alcance

- A* u otras variantes.
- Heaps con `decrease-key` (Fibonacci): se mencionan solo en la discusión.
