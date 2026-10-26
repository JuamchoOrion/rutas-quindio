# Guía para Claude Code

Proyecto final de Análisis de Algoritmos (UniQuindío). Enunciado y anexo en
`docs/enunciado/`. Lee `specs/README.md` antes de cualquier cambio.

## Reglas del proyecto

1. **Spec primero.** No implementes nada sin spec en `specs/`. Si el código
   necesita un comportamiento que la spec no describe, propón el cambio a la spec,
   espera aprobación y luego programa.
2. **Trazabilidad.** Cada caso `Rx-Cyy` de una spec tiene una prueba con ese ID en
   su nombre (`test_R2_C03_...`). Cada regla `Rx-Byy` se cita en el docstring o
   comentario del código que la cumple.
3. **Implementación propia.** Dijkstra, QuickHull, fuerza bruta, Held-Karp y el
   vecino más cercano NO pueden usar NetworkX, SciPy, Shapely ni
   `itertools.permutations`. Esas librerías solo se usan en `tests/` para verificar.
   Permitido como apoyo: `heapq`, `list`, `dict`, `sorted` (documentar su costo).
4. **Protocolo de medición** (`specs/protocolo-experimental.md`): usar
   `rutas.benchmark.measure` / `measure_with_timeout`; solo se cronometra el
   algoritmo; 5 repeticiones y mediana; límite de 5 min; tiempos en ms; semilla
   `SEED`. Los experimentos escriben CSV en `results/rX/` y las gráficas se
   generan desde esos CSV.
5. **Verificar antes de medir.** Un script de experimento verifica primero (contra
   otra implementación o librería) y aborta si falla.
6. **Idioma.** Código (identificadores) en inglés; docstrings, comentarios, specs,
   CSV y documentación en español.
7. **Estilo.** Type hints, funciones cortas, dataclasses para resultados, sin
   números mágicos (constantes con nombre), PEP 8, líneas ≤ 100.

## Comandos

```bash
pip install -e ".[red,dev]"     # dependencias
pytest                          # siempre antes de commitear
python scripts/build_network.py # R1 (requiere internet y catálogo válido)
```

## Pendiente (en orden)

1. Llenar `data/catalogo.csv` (≥ 40 lugares, coordenadas verificadas en mapa).
2. Ejecutar R1 y completar la tabla de velocidades por defecto con su fuente.
3. `scripts/run_r2.py`, `run_r3.py`, `run_r4.py`, `make_figures.py` según las specs.
4. Aplicación (spec R5) en `app/app.py`.
5. Registrar cada sesión con IA en `docs/anexo-ia.md`.
