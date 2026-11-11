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
   `itertools.permutations`. Fuera de `tests/` solo se usan OSMnx/NetworkX para
   preparar la red (R1) y SciPy en `run_r3.py` para la comparación que pide R3.
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
python scripts/measure_scc.py   # R1: repetir solo la medición de la CFC (R1-B26)
python scripts/run_r2.py        # R2; luego run_r3.py y run_r4.py
python scripts/make_figures.py  # gráficas (results/rX/) y tablas (results/tablas/)
streamlit run app/app.py        # R5 (pip install -e ".[red,app]")
```

## Pendiente (en orden)

Hecho: catálogo verificado (40 lugares), R1–R4 ejecutados con sus tablas y
gráficas en `results/`, aplicación R5.

1. Documento técnico con la estructura de la sección 7 del enunciado: arquitectura
   (`docs/arquitectura.md`), por requerimiento problema, complejidad con fuente y
   recurrencia, correctitud, tablas y gráficas de `results/tablas/` y discusión;
   conclusiones; anexo de IA. Repartir las secciones entre Juan y Laura.
2. Discusiones que el documento debe incluir: los 7 lugares a más de 500 m
   (R1-B17), el radio de 20 km con más nodos que el departamento, el cociente de
   Dijkstra no constante (185–439) frente a lo esperado en R2, y las dos máquinas
   (R1/R2 en Ryzen 7 7445HS, R3/R4 en Apple M2).
3. Registrar cada sesión con IA en `docs/anexo-ia.md`.
4. Preparar la sustentación: cada integrante debe poder explicar cualquier parte.
