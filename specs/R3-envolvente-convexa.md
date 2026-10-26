# R3 — Envolvente convexa de la red vial

## Contexto

Enunciado, sección 5, requerimiento 3. La envolvente convexa de los nodos de la
CFC aproxima la extensión de la red. Implementación propia por **divide y
vencerás**, verificada contra `scipy.spatial.ConvexHull`.

Módulo: `src/rutas/convex_hull.py`. Script: `scripts/run_r3.py`.

## Elección del algoritmo: QuickHull

Se elige **QuickHull** (Eddy 1977; Barber, Dobkin y Huhdanpaa 1996). Es divide y
vencerás: la recta entre los puntos extremos divide el conjunto en dos; en cada
mitad, el punto más lejano a la recta forma un triángulo cuyo interior se
descarta, y se resuelven recursivamente los dos lados exteriores.

Justificación según la distribución de los puntos de la red:

1. Los nodos de una red vial se concentran en cascos urbanos y a lo largo de las
   vías, y casi todos quedan **lejos del borde**: el número de vértices `h` de la
   envolvente es muy pequeño frente a `n`. QuickHull descarta en la primera
   partición todos los puntos dentro del cuadrilátero formado por los extremos, y
   su costo efectivo depende de `h` (caso típico O(n log h)).
2. El peor caso O(n²) exige muchos puntos sobre el borde (por ejemplo, sobre una
   circunferencia), lo que no ocurre en una red vial ni en puntos uniformes en un
   cuadrado (para ellos el número esperado de vértices es O(log n), Rényi y
   Sulanke 1963).
3. SciPy usa Qhull, que también es QuickHull. Comparar el mismo algoritmo aísla el
   efecto de la implementación (C compilado frente a Python interpretado).

Alternativa considerada: *merge hull* de Preparata y Hong (O(n log n) garantizado
en el peor caso). Se descarta porque en estos datos su paso de mezcla no
aprovecha que casi todos los puntos son interiores.

## Interfaz

```python
Point = tuple[int, int]

prepare_points(xs_m: Iterable[float], ys_m: Iterable[float]) -> list[Point]
quickhull(points: Sequence[Point]) -> list[Point]   # vértices en sentido antihorario
```

## Comportamiento esperado

- **R3-B01.** `prepare_points` redondea cada coordenada UTM (metros) al entero más
  cercano con `floor(v + 0.5)` (regla explícita; se evita `round()` de Python,
  que redondea los empates al par) y elimina duplicados conservando el orden de
  aparición.
- **R3-B02.** Toda la geometría usa enteros: el giro se decide con el producto
  cruz `cross(a, b, p) = (bx − ax)(py − ay) − (by − ay)(px − ax)`, sin
  divisiones ni flotantes. (En Python los `int` son de precisión arbitraria; en un
  lenguaje con enteros fijos se usaría `int64`: con coordenadas UTM < 10⁷ m, el
  producto es < 4·10¹⁴, lejos del límite 9.2·10¹⁸.)
- **R3-B03.** Los puntos **colineales** sobre un lado no son vértices: un punto solo
  se considera exterior a un segmento si `cross < 0` estrictamente (lado derecho
  del segmento dirigido, recorriendo en sentido antihorario).
- **R3-B04.** Salida en sentido **antihorario**, empezando por el punto con menor
  `x` (y menor `y` en caso de empate), sin repetir el primero al final.
- **R3-B05.** Casos degenerados: 0 puntos → `[]`; 1 punto → `[p]`; todos
  colineales → los 2 extremos.
- **R3-B06.** La recursión se implementa con una **pila explícita** para no
  depender del límite de recursión de Python en entradas con muchos vértices.
- **R3-B07.** Verificación: el conjunto de vértices es igual al de
  `scipy.spatial.ConvexHull(points).vertices` en todas las pruebas no degeneradas.

## Recurrencia y complejidad

Sea `n` el número de puntos de un subproblema. Encontrar el punto más lejano y
repartir los puntos cuesta Θ(n):

```
T(n) = T(n₁) + T(n₂) + Θ(n),   con n₁ + n₂ ≤ n − 1
```

- Partición balanceada (n₁ ≈ n₂ ≈ n/2): T(n) = Θ(n log n) (teorema maestro, caso 2).
- Peor caso (n₁ = n − 1, n₂ = 0 en cada paso): T(n) = Θ(n²).
- Sensible a la salida: como cada nivel de recursión produce un vértice, la
  profundidad es ≤ h y cada nivel cuesta O(n): O(n·h) en el peor caso.
- Memoria: O(n) (los subconjuntos de un nivel son disjuntos).

Fuentes: Preparata y Shamos, *Computational Geometry: An Introduction* (1985),
sección 3.3.4; Barber, Dobkin y Huhdanpaa, "The Quickhull algorithm for convex
hulls", *ACM Trans. Math. Software* 22(4), 1996.

## Experimento

| Conjunto | Generación |
|---|---|
| Nodos de la red | CFC de R1, en UTM, redondeados y sin duplicados |
| Cuadrado 1 000 / 10 000 / 50 000 | enteros uniformes en `[0, 100 000)²`, semilla `SEED` |

Archivo `results/r3/envolvente_tiempos.csv`:
`conjunto, n, vertices, tiempo_propio_ms, tiempo_scipy_ms, cociente`.
El tiempo de SciPy mide solo `ConvexHull(arr)` con `arr` ya construido.

## Casos de prueba

| ID | Entrada | Resultado esperado |
|---|---|---|
| R3-C01 | Cuadrado `(0,0),(4,0),(4,4),(0,4)` + interior `(2,2)` | 4 vértices, antihorario desde `(0,0)` |
| R3-C02 | Cuadrado con puntos medios de los lados `(2,0),(4,2),…` | 4 vértices (colineales excluidos) |
| R3-C03 | `[]`, `[(1,1)]` | `[]`, `[(1,1)]` |
| R3-C04 | `(0,0),(1,1),(2,2),(3,3)` | `[(0,0),(3,3)]` |
| R3-C05 | Triángulo | 3 vértices |
| R3-C06 | `prepare_points([1.4, 1.6, 1.4], [2.4, 0.2, 2.3])` | `[(1, 2), (2, 0)]` (redondeo + sin duplicados, conserva el orden de aparición) |
| R3-C10 | `prepare_points([0.5, -0.5], [2.5, -2.5])` | `[(1, 3), (0, -2)]` (empates hacia +∞: `floor(v + 0.5)`) |
| R3-C07 | 50 nubes aleatorias (semilla fija), n entre 10 y 2 000 | mismo conjunto de vértices que SciPy |
| R3-C08 | 360 puntos sobre una circunferencia (peor caso) | todos son vértices; sin `RecursionError` |
| R3-C09 | Salida de R3-C07 | todos los giros consecutivos son estrictamente a la izquierda (`cross > 0`) |

## Fuera de alcance

- Envolventes en 3D.
- Dibujo del polígono (lo hace la aplicación de R5).
