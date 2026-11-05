# Rutas del Paisaje Cultural Cafetero

Proyecto final de **Análisis de Algoritmos** — Universidad del Quindío, 2026-2.

Sistema de planificación de rutas sobre la red vial real del Quindío: caminos
mínimos (Dijkstra), envolvente convexa (QuickHull), problema del viajante asimétrico
(fuerza bruta, Held-Karp y vecino más cercano) y una aplicación demostrativa.

El proyecto sigue **Spec-Driven Development**: cada requerimiento tiene una
especificación en [`specs/`](specs/README.md) con su comportamiento esperado y sus
casos de prueba, y cada caso tiene una prueba en `tests/` con el mismo ID.

## Estado

| Requerimiento | Spec | Algoritmos y pruebas | Experimentos | Documento |
|---|---|---|---|---|
| R1 Modelo de la red | ✅ | ✅ pesos, memoria, UTM, catálogo | ✅ `results/r1/` (catálogo provisional) | ⏳ |
| R2 Caminos mínimos | ✅ | ✅ Dijkstra lineal y con cola | ✅ `results/r2/` | ⏳ |
| R3 Envolvente convexa | ✅ | ✅ QuickHull entero | ⏳ `run_r3.py` | ⏳ |
| R4 Ruta óptima | ✅ | ✅ fuerza bruta, Held-Karp, voraz, itinerario | ⏳ `run_r4.py` | ⏳ |
| R5 Aplicación | ✅ | ✅ `app/app.py` | — | ⏳ |
| Catálogo (≥ 40 lugares) | ✅ | validador ✅ | ✅ 40 lugares; coordenadas por verificar | ⏳ |

## Estructura

```
specs/                 Especificaciones (fuente de verdad, SDD)
src/rutas/             Paquete con los algoritmos (implementación propia)
  graph.py             Listas de adyacencia                         R1
  network_model.py     Velocidades, tiempos, estimación de memoria  R1
  geo.py               UTM 18N y nodo más cercano                   R1, R3
  catalog.py           Carga y validación del catálogo              R1
  shortest_paths.py    Dijkstra O(V²) y O((V+E) log V)              R2
  convex_hull.py       QuickHull con aritmética entera              R3
  tsp.py               Fuerza bruta, Held-Karp, vecino más cercano  R4
  itinerary.py         Itinerario de un día (11 h)                  R4
  benchmark.py         Protocolo experimental (mediana, límite 5 min)
  app_support.py       Lógica de la aplicación (sin Streamlit)      R5
  data_io.py, paths.py Carga del grafo procesado, matriz y rutas de archivos
app/app.py             Aplicación demostrativa (Streamlit + Folium) R5
tests/                 Pruebas (pytest); los nombres llevan el ID del caso de la spec
scripts/               Descarga de la red y experimentos
data/                  catalogo.csv, raw/ (no versionado), processed/
results/r1..r4/        CSV/JSON de mediciones, tablas y gráficas
docs/                  Enunciado, arquitectura y anexo de IA
```

## Instalación

Requiere Python ≥ 3.11.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[red,dev]"          # algoritmos, scripts y pruebas
pip install -e ".[red,app]"          # aplicación (R5)
```

## Uso

```bash
# 1. Verificar los algoritmos (siempre antes de medir)
pytest

# 2. R1: investigar el algoritmo de CFC de la versión instalada
python scripts/inspect_scc.py

# 3. R1: descargar la red, pesos, CFC, asociar lugares y guardar (requiere internet
#    y un catálogo válido en data/catalogo.csv). Si overpass-api.de rechaza la
#    conexión, agregar --overpass-url https://maps.mail.ru/osm/tools/overpass/api
python scripts/build_network.py

# 4. R2: verificar y medir Dijkstra; matriz de tiempos (results/r2/)
python scripts/run_r2.py
```

## Aplicación (R5)

La red procesada (`data/processed/`) y los resultados (`results/`) ya están en el
repositorio, así que la aplicación funciona sin internet y sin ejecutar nada antes:

```bash
pip install -e ".[red,app]"
streamlit run app/app.py
```

Se abre en el navegador (por defecto en <http://localhost:8501>) con cuatro pestañas:

| Pestaña | Qué hace |
|---|---|
| Ruta origen-destino | Elige dos lugares, ejecuta Dijkstra con cola de prioridad en el momento y dibuja la ruta con su tiempo y los nodos explorados |
| Envolvente convexa | Dibuja la envolvente de R3 (`results/r3/envolvente_red.json`) y los lugares del catálogo |
| Itinerario | Elige la partida (Armenia por defecto) y de 6 a 8 atractivos; compara Held-Karp con el vecino más cercano y arma el plan de 11 h |
| Resultados | Muestra las tablas (CSV) y gráficas (PNG) de `results/r1` a `results/r4` |

Si falta algún archivo de `results/` (por ejemplo, antes de ejecutar `run_r3.py`), la
pestaña correspondiente muestra qué script lo genera.

## Convenciones

- **Unidades**: tiempos de viaje en segundos, tiempos de ejecución en **milisegundos**,
  distancias en metros, coordenadas planas en UTM zona 18N (EPSG:32618).
- **Semilla**: `SEED = 20262` (`src/rutas/benchmark.py`).
- **Nodos**: los algoritmos trabajan con índices `0..V-1`; `Graph` traduce desde y
  hacia los ids de OSM.
- **Implementación propia**: Dijkstra, QuickHull, fuerza bruta, Held-Karp y el
  vecino más cercano no usan funciones de librería que los resuelvan. NetworkX y
  SciPy solo aparecen en `tests/` para verificar resultados. De apoyo se usa
  `heapq` (cola de prioridad; su costo se analiza en la spec de R2).
- **Commits**: un commit por spec o por caso implementado, con el ID en el mensaje
  (`feat(R2): Dijkstra con cola de prioridad [R2-B08, R2-C01..C08]`).

## Documentación

- [Especificaciones](specs/README.md)
- [Arquitectura](docs/arquitectura.md)
- [Anexo de uso de IA](docs/anexo-ia.md)
- Enunciado: [`docs/enunciado/`](docs/enunciado/)
