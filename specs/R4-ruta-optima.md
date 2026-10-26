# R4 — Ruta óptima de recorrido (ATSP)

## Contexto

Enunciado, sección 5, requerimiento 4. Se sale de un lugar, se visitan `k` lugares
y se regresa, minimizando el tiempo total según la matriz de R2. Es el problema
del viajante **asimétrico** (ATSP): `d(i, j)` puede ser distinto de `d(j, i)`.

Módulos: `src/rutas/tsp.py`, `src/rutas/itinerary.py`. Script: `scripts/run_r4.py`.

## Modelo de una instancia

Una instancia es una submatriz cuadrada `costs` de tamaño `n = k + 1`, extraída
de la matriz de R2, donde el **índice 0 es el lugar de partida** y los índices
`1..k` son los lugares a visitar. `instance_matrix(full, ids, start, places)`
construye esa submatriz y conserva la traducción de índices a ids.

Un **recorrido** (`Tour`) se representa como la lista de índices
`[0, v₁, …, v_k, 0]` y su costo es `Σ costs[tᵢ][tᵢ₊₁]`.

## Interfaz

```python
@dataclass(frozen=True)
class Tour:
    order: list[int]   # empieza y termina en 0
    cost: float        # segundos

tour_cost(costs, order) -> float
brute_force_tsp(costs) -> Tour
held_karp(costs) -> Tour
nearest_neighbor_tour(costs) -> Tour
held_karp_table_bytes(k, value_bytes=8, parent_bytes=4) -> int

# itinerary.py
plan_day(costs, labels, visit_min, budget_s=11*3600) -> DayPlan
```

## Comportamiento esperado

### Comunes
- **R4-B01.** `costs` es cuadrada, de tamaño ≥ 1, con diagonal 0 y valores ≥ 0.
- **R4-B02.** `k = 0` → `Tour([0, 0], 0)`; `k = 1` → `Tour([0, 1, 0], d(0,1) + d(1,0))`.
- **R4-B03.** Todo `Tour` devuelto empieza y termina en 0, visita cada índice
  `1..k` exactamente una vez y su `cost` es igual a `tour_cost(costs, order)`.
- **R4-B04.** Si hay empates en el óptimo, cualquier recorrido óptimo es válido; la
  verificación compara **costos**, no órdenes.

### Fuerza bruta
- **R4-B05.** Enumera las `k!` permutaciones de `1..k` (el inicio está fijo) con
  un generador propio por *backtracking*, **sin poda**: todas las permutaciones se
  evalúan completas. El costo parcial se acumula al bajar en el árbol para no
  recalcular prefijos (sigue siendo búsqueda exhaustiva).
- **R4-B06.** No usa `itertools.permutations` (implementación propia).

### Held-Karp
- **R4-B07.** Subestructura óptima: si `0 → … → j` es la mejor forma de salir de 0,
  visitar exactamente el conjunto `S` y terminar en `j ∈ S`, entonces su prefijo
  `0 → … → i` es la mejor forma de visitar `S \ {j}` terminando en `i` (si no lo
  fuera, cambiarlo por uno mejor mejoraría el total: cortar y pegar).
- **R4-B08.** Recurrencia (con `S ⊆ {1..k}`, `j ∈ S`):

  ```
  C({j}, j) = d(0, j)
  C(S, j)   = min_{i ∈ S \ {j}}  C(S \ {j}, i) + d(i, j)        si |S| ≥ 2
  óptimo    = min_{j ∈ {1..k}}   C({1..k}, j) + d(j, 0)
  ```
- **R4-B09.** Los conjuntos se representan como máscaras de bits de `k` bits; se
  recorren en orden numérico creciente, lo que garantiza que `S \ {j}` (menor que
  `S`) ya está calculado.
- **R4-B10.** Se guarda el predecesor `P(S, j) = argmin` para **reconstruir el
  recorrido**, no solo su costo.
- **R4-B11.** Memoria de la tabla: `2^k · k` celdas de costo y otras tantas de
  predecesor. `held_karp_table_bytes(k)` = `2^k · k · (8 + 4)` bytes con los
  supuestos `float64` y `int32`.

### Heurística voraz: vecino más cercano
- **R4-B12.** Desde el lugar actual (empezando en 0) se va al lugar **no visitado**
  con menor `d(actual, j)`; empate → menor índice. Al visitar todos, se regresa a 0.
- **R4-B13.** Justificación de la elección: es la heurística voraz más directa
  (misma elección local que hace Dijkstra: "lo más cercano primero"), funciona
  igual en el caso asimétrico porque solo mira la fila del lugar actual, y cuesta
  O(k²), despreciable frente a Held-Karp.
- **R4-B14.** Brecha: `gap% = 100 · (costo_heurística − costo_óptimo) / costo_óptimo`.

### Itinerario de un día
- **R4-B15.** Entrada: lugar de partida (por defecto `armenia`) y entre 6 y 8
  atractivos; se ordenan con Held-Karp.
- **R4-B16.** Duración de la jornada = Σ desplazamientos + Σ visitas. Cabe si es
  ≤ 11 h (39 600 s).
- **R4-B17.** Si no cabe, se quita **un** atractivo por vez: el que más reduce la
  jornada al quitarlo del recorrido actual, es decir, el de mayor ahorro
  `d(prev, j) + visita(j) + d(j, next) − d(prev, next)`. Empate → el de mayor
  visita. Luego se recalcula Held-Karp y se repite hasta que quepa. Cada atractivo
  quitado se registra con su ahorro como justificación.
- **R4-B18.** Salida (`DayPlan`): filas con `orden, lugar, desplazamiento_min,
  visita_min, acumulado_h`, la fila de regreso, totales de visitas, de
  desplazamientos y de la jornada, y la lista de atractivos quitados.

## Complejidad esperada

| Algoritmo | Tiempo | Memoria | Fuente |
|---|---|---|---|
| Fuerza bruta (textbook, costo de cada permutación desde cero) | Θ(k · k!) | O(k) | — |
| Fuerza bruta implementada (costo incremental) | Θ(k!) (el árbol tiene ≈ e · k! nodos) | O(k) | — |
| Held-Karp | Θ(2^k · k²) | Θ(2^k · k) | Held y Karp, "A dynamic programming approach to sequencing problems", *J. SIAM* 10(1), 1962; Bellman, *J. ACM* 9(1), 1962 |
| Vecino más cercano | Θ(k²) | O(k) | Rosenkrantz, Stearns y Lewis, *SIAM J. Comput.* 6(3), 1977 |

Recurrencia de tiempo de Held-Karp: hay `2^k · k` estados `(S, j)` y cada uno
toma el mínimo sobre ≤ `k` predecesores → `Σ_{s=1..k} C(k, s) · s · (s − 1) = Θ(2^k k²)`.

## Experimentos

- Inicio Armenia; `k` lugares al azar del catálogo, sin Armenia, de todas las
  categorías, con `random.Random(SEED + k)` (y `SEED + 100·k + i` para la
  instancia `i` de calidad).
- Exactas: `k = 5..12`; se detiene cada método cuando una ejecución pasa de 5 min
  (PE-B07). `results/r4/exactas_tiempos.csv`:
  `k, tiempo_fuerza_bruta_ms, tiempo_held_karp_ms, completado_fb, completado_hk, costo_fb_s, costo_hk_s`.
- Calidad: `k ∈ {5, 8, 10, 12}`, ≥ 5 instancias cada uno.
  `results/r4/heuristica_calidad.csv`: `k, instancia, costo_optimo_s, costo_heuristica_s, brecha_pct`
  y un resumen con promedio y máximo por `k`.
- Itinerario: `results/r4/itinerario.csv` con el formato del anexo.

## Voraz frente a óptimo (para el documento técnico)

Contraejemplo `CE` (k = 3, matriz asimétrica en segundos):

```
        0    1    2    3
0  [    0,   1,  10,  10 ]
1  [   10,   0,   2,   1 ]
2  [   10,  10,   0,   1 ]
3  [    1,  10,  10,   0 ]
```

- Vecino más cercano: 0 → 1 (1) → 3 (1, más barato que ir a 2) → 2 (10) → 0 (10) = **22**.
- Óptimo: 0 → 1 → 2 → 3 → 0 = 1 + 2 + 1 + 1 = **5**.

Por qué Dijkstra sí acierta: su elección voraz (extraer el nodo con menor
distancia tentativa) cumple la **propiedad de elección voraz** gracias al
invariante de R2 y a los pesos no negativos: ningún camino que pase por nodos aún
no extraídos puede volver más barato al nodo extraído, así que la decisión nunca
se revisa. En el ATSP la decisión "ir al más cercano" compromete los arcos
futuros: el recorrido debe cerrar un ciclo que pase por todos, y un paso barato
puede dejar como únicas opciones arcos caros (como 3 → 2 → 0 en `CE`). El
problema tiene subestructura óptima (por eso funciona Held-Karp) pero no
elección voraz.

## Casos de prueba

| ID | Entrada | Resultado esperado |
|---|---|---|
| R4-C01 | Matriz 1 × 1 (`k = 0`) | `Tour([0, 0], 0)` en los tres métodos |
| R4-C02 | `k = 1`, `d(0,1)=3`, `d(1,0)=5` | costo 8 en los tres métodos |
| R4-C03 | `CE` | fuerza bruta = Held-Karp = 5, orden `[0,1,2,3,0]`; vecino más cercano = 22, orden `[0,1,3,2,0]` |
| R4-C04 | 40 matrices asimétricas aleatorias, `k = 2..8` (semilla fija) | costo fuerza bruta = costo Held-Karp |
| R4-C05 | Recorridos de R4-C04 | cumplen R4-B03 (permutación válida y costo consistente) |
| R4-C06 | Mismas matrices | costo heurística ≥ costo óptimo |
| R4-C07 | `held_karp_table_bytes(12)` | `4096 · 12 · 12 = 589 824` |
| R4-C08 | Plan de día que cabe | no se quita nada; totales = suma de las filas |
| R4-C09 | Plan de día que no cabe | se quitan atractivos por mayor ahorro hasta que la jornada ≤ 11 h |
| R4-C10 | Matriz no cuadrada o con valor negativo | `ValueError` |

## Fuera de alcance

- Mejoras locales (2-opt, Or-opt): se pueden mencionar como trabajo futuro.
