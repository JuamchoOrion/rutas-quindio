# R1 — Modelo de la red vial

## Contexto

Enunciado, sección 5, requerimiento 1. Se descarga la red vial del Quindío con
OSMnx, se le asignan pesos (distancia y tiempo), se extrae la componente
fuertemente conexa (CFC) más grande, se asocian los lugares del catálogo a nodos y
se guarda todo para no volver a descargar.

Módulos: `src/rutas/network_model.py`, `src/rutas/geo.py`, `src/rutas/catalog.py`,
`src/rutas/graph.py`. Script: `scripts/build_network.py`.

## Interfaz

```python
# network_model.py
parse_maxspeed(raw: str | list | None) -> float | None          # km/h
edge_speed_kmh(maxspeed_raw, highway_raw) -> tuple[float, str]   # (velocidad, origen)
travel_time_s(length_m: float, speed_kmh: float) -> float
estimate_memory(n_nodes: int, n_edges: int, ...) -> MemoryEstimate

# geo.py
to_utm(lat: float, lon: float) -> tuple[float, float]            # EPSG:32618
nearest_node(x, y, node_xs, node_ys) -> tuple[int, float]        # (índice, distancia_m)

# catalog.py
load_catalog(path) -> list[Place]
validate_catalog(places) -> list[str]                             # lista de errores

# graph.py
Graph.from_edges(node_ids, edges) -> Graph                        # listas de adyacencia
```

## Comportamiento esperado

### 1. Representación

- **R1-B01.** La estimación de memoria usa el V y E reales de la red descargada.
- **R1-B02.** Matriz de adyacencia: `V² × bytes_por_celda`. Supuesto por defecto:
  una celda guarda el tiempo de viaje como `float64` (8 B). Si se quiere guardar
  también la distancia, son 16 B por celda.
- **R1-B03.** Listas de adyacencia: `V × bytes_por_cabecera + E × bytes_por_entrada`.
  Supuesto por defecto: cabecera = 8 B (referencia a la lista); entrada = vecino
  `int64` (8 B) + tiempo `float64` (8 B) + distancia `float64` (8 B) = 24 B.
- **R1-B04.** Los resultados se reportan en MB (10⁶ bytes) y se indican los supuestos.
  Se reporta también la densidad `E / V²` como argumento de la elección.
- **R1-B05.** Decisión: **listas de adyacencia**. Una red vial es muy dispersa
  (cada intersección tiene pocas vías, E ≈ 2–3 V), así que la matriz desperdicia
  casi todas sus celdas y Dijkstra con cola de prioridad necesita recorrer los
  vecinos de un nodo en O(grado), no en O(V).

### 2. Pesos

- **R1-B06.** Cada arista guarda `length_m` (de OSM) y `travel_time_s`.
- **R1-B07.** `travel_time_s = length_m / (speed_kmh / 3.6)`.
- **R1-B08.** Velocidad del tramo, en este orden de prioridad:
  1. `maxspeed` de OSM si existe y es interpretable (`"50"`, `"50 km/h"`, `"30 mph"`;
     si es una lista se toma la **mínima**, criterio conservador).
  2. Si no, una velocidad por defecto según el tipo de vía (`highway`), tomada de
     la tabla `DEFAULT_SPEED_KMH` (si `highway` es lista, se usa el primer tipo
     reconocido). La tabla se justifica en el documento técnico con la norma de
     velocidades colombiana vigente (citar la fuente exacta).
  3. Si el tipo tampoco se reconoce, `FALLBACK_SPEED_KMH = 30`.
- **R1-B09.** `edge_speed_kmh` devuelve también el **origen** de la velocidad
  (`"maxspeed"`, `"highway_default"`, `"fallback"`) para poder reportar cuántos
  tramos se resolvieron de cada forma.
- **R1-B10.** Velocidades no positivas o absurdas (> 130 km/h) se descartan y se
  pasa a la siguiente regla.

### 3. Componente fuertemente conexa

- **R1-B11.** Se obtiene con `ox.truncate.largest_component(G, strongly=True)`.
- **R1-B12.** El algoritmo interno se investiga **en la versión instalada**
  (`scripts/inspect_scc.py` imprime versión y docstring). Referencia: en
  NetworkX 3.7 `strongly_connected_components` usa una versión iterativa del
  algoritmo de Tarjan con las mejoras de Tarjan y Zwick (2024); en versiones
  anteriores la documentación cita Tarjan (1972) con las modificaciones de
  Nuutila. En ambos casos: tiempo O(V + E), memoria O(V).
- **R1-B13.** Se mide sobre redes de radio 2, 5, 10 y 20 km alrededor de la plaza
  de Bolívar de Armenia y sobre el departamento completo. Solo se mide la llamada
  a `largest_component` (la descarga queda por fuera, PE-B02).
- **R1-B14.** Tabla de salida: `results/r1/scc_tiempos.csv` con columnas
  `red, V, E, V_mas_E, tiempo_ms`.

### 4. Ubicación de los lugares

- **R1-B15.** Coordenadas en UTM zona 18N (EPSG:32618), en metros.
- **R1-B16.** Cada lugar se asocia al nodo de la CFC a menor distancia euclidiana.
- **R1-B17.** Se reportan los lugares con distancia > 500 m en
  `results/r1/lugares_lejanos.csv` y se marca `lejano=True` en la asociación. Se
  mantienen asociados a su nodo más cercano (es el punto donde la vía más próxima
  toca la red) y el documento técnico explica el caso de cada uno (por ejemplo,
  una finca al final de un camino privado que OSM no tiene como vía vehicular).

### 5. Grafo procesado

- **R1-B18.** Se guarda en `data/processed/`:
  - `red_cfc.graphml` (la CFC con `length_m` y `travel_time_s` en cada arista),
  - `lugares_nodos.csv` (`id, nodo_osm, distancia_m, lejano`),
  - `red_resumen.json` (V y E antes/después, fecha de descarga, versión OSMnx).
- **R1-B19.** La fecha de descarga se guarda en ISO 8601.

### Catálogo

- **R1-B20.** El catálogo `data/catalogo.csv` tiene columnas
  `id, nombre, municipio, categoria, lat, lon, duracion_visita_min, fuente_duracion`.
- **R1-B21.** Categorías y mínimos: `cabecera` ≥ 12, `atractivo` ≥ 15,
  `finca_hotel` ≥ 8, `acopio` ≥ 5; total ≥ 40.
- **R1-B22.** Todo `atractivo` tiene `duracion_visita_min > 0` y `fuente_duracion`.
- **R1-B23.** Los `id` son únicos y existe el id `armenia` (punto de partida por
  defecto).
- **R1-B24.** Las coordenadas caen dentro del recuadro del Quindío
  (lat 4.05–4.75, lon −75.95 – −75.35). Es solo un control grueso; cada coordenada
  se verifica a mano en un mapa.

## Complejidad esperada

| Operación | Tiempo | Memoria | Fuente a citar |
|---|---|---|---|
| CFC (Tarjan) | O(V + E) | O(V) | Tarjan (1972), *Depth-first search and linear graph algorithms*; docs NetworkX |
| Nodo más cercano (fuerza bruta) | O(V) por lugar | O(1) extra | — |
| Construir listas de adyacencia | O(V + E) | O(V + E) | Cormen et al., *Introduction to Algorithms*, cap. 20 (4.ª ed.) |

## Casos de prueba

| ID | Entrada | Resultado esperado |
|---|---|---|
| R1-C01 | `parse_maxspeed("50")` | `50.0` |
| R1-C02 | `parse_maxspeed("30 mph")` | `48.28` (±0.01) |
| R1-C03 | `parse_maxspeed(["60", "40"])` | `40.0` (mínimo) |
| R1-C04 | `parse_maxspeed("signals")`, `None`, `"0"` | `None` |
| R1-C05 | `edge_speed_kmh(None, "residential")` | `(DEFAULT_SPEED_KMH["residential"], "highway_default")` |
| R1-C06 | `edge_speed_kmh(None, "tipo_raro")` | `(30.0, "fallback")` |
| R1-C07 | `travel_time_s(1000, 36)` | `100.0` |
| R1-C08 | `estimate_memory(1000, 2500)` | matriz = 8.0 MB; listas = 0.068 MB |
| R1-C09 | `to_utm` de la plaza de Bolívar de Armenia | x ≈ 4.24·10⁵ m (oeste del meridiano central −75°), y ≈ 5.01·10⁵ m (±2 km) |
| R1-C10 | `nearest_node` con 3 nodos y un punto a 3–4–5 m | índice correcto y distancia 5.0 |
| R1-C11 | Catálogo con 39 lugares | `validate_catalog` reporta el faltante |
| R1-C12 | Catálogo con un atractivo sin duración | error que menciona su id |
| R1-C13 | `Graph.from_edges` con aristas paralelas | conserva ambas; `n_edges` las cuenta |

## Fuera de alcance

- La descarga en sí (depende de la red; se ejecuta con `scripts/build_network.py`).
- Tiempos reales de tráfico: el tiempo del modelo es una estimación.
