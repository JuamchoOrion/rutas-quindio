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

Script: `scripts/run_r2.py`. Usa la red procesada de R1 (`data/processed/`) y no
descarga nada.

- **R2-B12. Elección de los pares.** Solo se usan pares ordenados `(origen, destino)`
  cuyos lugares están en **nodos distintos** de la red (por ejemplo, se excluye
  Cocora → Acaime, que comparten nodo).
  - *Cercanos (10):* lugares del **mismo municipio**. Se barajan todos los pares
    candidatos con `random.Random(SEED)` y se toman en ese orden, saltando los de un
    municipio que ya tenga **3** pares, hasta completar 10. Así quedan en al menos
    4 municipios distintos. Se miden con las **dos** versiones.
  - *Lejanos (10):* lugares de municipios distintos, barajados con
    `random.Random(SEED + 1)`; se toman los 10 primeros. Solo se miden con la cola de
    prioridad y sirven para cubrir en la gráfica desde pocos hasta casi todos los
    nodos explorados.
  - La cola de prioridad se mide en los 20 pares (≥ 20 que pide el enunciado).
- **R2-B13. Verificación antes de medir (PE-B06).** Sin NetworkX (regla de
  implementación propia: las librerías solo se usan en `tests/`), contra la otra
  implementación propia. El script aborta si falla algo:
  1. en los 20 pares, `dijkstra_heap(o, d).cost` = `dijkstra_all(o)[d]`
     (tolerancia relativa 1e-9);
  2. en los 10 pares cercanos, `dijkstra_linear` y `dijkstra_heap` dan el mismo costo
     (R2-B11);
  3. toda ruta devuelta empieza en `o`, termina en `d`, cada paso es una arista
     existente y la suma de sus pesos (el menor entre aristas paralelas) es el costo;
  4. la matriz tiene diagonal 0, todas sus celdas son finitas (la red es la CFC) y
     coincide con los costos de los 20 pares.
- **R2-B14. Archivos en `results/r2/`.** Tiempos en ms (PE-B04), mediana de 5
  repeticiones con `rutas.benchmark.measure` (PE-B02, PE-B03).

  | Archivo | Columnas / contenido |
  |---|---|
  | `dijkstra_mediciones.csv` | `origen, destino, version, tiempo_viaje_s, nodos_explorados, tiempo_ms, tipo_par, semilla`; `version ∈ {lineal, cola_prioridad}`, `tipo_par ∈ {cercano, lejano}` |
  | `dijkstra_cociente.csv` | `origen, destino, explorados_lineal, explorados_cola, tiempo_lineal_ms, tiempo_cola_ms, cociente` (10 filas; `cociente = tiempo_lineal_ms / tiempo_cola_ms`) |
  | `dijkstra_cociente_resumen.csv` | `pares, mediana, minimo, maximo` |
  | `matriz_tiempos.csv` | celda superior izquierda `id`; primera fila y primera columna con los ids en el orden del catálogo; celdas en segundos |
  | `matriz_resumen.json` | `n`, `tiempo_ms` (mediana de `travel_time_matrix`), `pares_asimetricos` (pares `i < j` con `M[i][j] ≠ M[j][i]`, tolerancia relativa 1e-9), `max_diferencia_s` (mayor `|M[i][j] − M[j][i]|` y su par), `lugares_mismo_nodo` |
  | `maquina.json` | `benchmark.machine_info()` (PE-B01) |

  La gráfica (nodos explorados en x, tiempo en ms en y, un color por versión) la
  genera `scripts/make_figures.py` desde `dijkstra_mediciones.csv` (PE-B08) en
  `results/r2/dijkstra_tiempo_vs_nodos.png` (estilo en PE-B10); las tablas, en
  `results/tablas/r2.md` (PE-B09).
- **R2-B15. Lectura y escritura de la matriz.** `rutas.data_io` ofrece
  `write_travel_time_matrix(path, ids, matrix)` y
  `load_travel_time_matrix(path) -> tuple[list[str], list[list[float]]]`, con el
  formato de R2-B14. R4 y R5 leen la matriz con esta función.

## Discusión esperada (para el documento técnico)

- Con parada temprana, las dos versiones extraen los nodos en el mismo orden (de
  menor a mayor distancia), así que exploran los **mismos nodos**; solo pueden
  diferir cuando hay empates de distancia, en cuál de los empatados se extrae antes
  del destino. Por eso `explorados_lineal ≈ explorados_cola` en cada par.
- Si se exploran `x` nodos, la lineal hace `x` barridos de los `V` nodos, Θ(x·V),
  y la cola hace Θ((x + aristas relajadas) · log V). Como las aristas relajadas son
  ≈ grado medio · x, el cociente es ≈ `V / log V` por una constante que no depende
  del par: se espera **aproximadamente constante**, del orden de `V / log V`
  (con V = 8 791, `V / log₂ V` ≈ 670), y la constante la fijan los costos reales
  de cada operación en Python.

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
| R2-C11 | `write_travel_time_matrix` y luego `load_travel_time_matrix` con ids y una matriz asimétrica con decimales | mismos ids, mismo orden y mismos valores (exactos) |

## Fuera de alcance

- A* u otras variantes.
- Heaps con `decrease-key` (Fibonacci): se mencionan solo en la discusión.
