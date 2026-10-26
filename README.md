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
| R1 Modelo de la red | ✅ | ✅ pesos, memoria, UTM, catálogo | ⏳ ejecutar `build_network.py` | ⏳ |
| R2 Caminos mínimos | ✅ | ✅ Dijkstra lineal y con cola | ⏳ `run_r2.py` | ⏳ |
| R3 Envolvente convexa | ✅ | ✅ QuickHull entero | ⏳ `run_r3.py` | ⏳ |
| R4 Ruta óptima | ✅ | ✅ fuerza bruta, Held-Karp, voraz, itinerario | ⏳ `run_r4.py` | ⏳ |
| R5 Aplicación | ✅ | ⏳ | — | ⏳ |
| Catálogo (≥ 40 lugares) | ✅ | validador ✅ | ⏳ llenar `data/catalogo.csv` | ⏳ |

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
  data_io.py, paths.py Carga del grafo procesado y rutas de archivos
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
pip install -e ".[red,dev]"          # agregar ",app" para la aplicación
```

## Uso

```bash
# 1. Verificar los algoritmos (siempre antes de medir)
pytest

# 2. R1: investigar el algoritmo de CFC de la versión instalada
python scripts/inspect_scc.py

# 3. R1: descargar la red, pesos, CFC, asociar lugares y guardar (requiere internet
#    y un catálogo válido en data/catalogo.csv)
python scripts/build_network.py
```

Los scripts de R2–R4 y la aplicación se agregan en las siguientes iteraciones.

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
