# Anexo — Uso de inteligencia artificial

Exigido por la sección 3 del enunciado. Se actualiza en cada sesión de trabajo con IA.

| Fecha | Herramienta | Para qué se usó | Archivos afectados | Cómo se verificó |
|---|---|---|---|---|
| 2026-10-26 | Claude (claude.ai) | Estructura del repositorio, specs iniciales de R1–R5 y del protocolo, implementación de los algoritmos de R2–R4 y utilidades de R1 | `specs/`, `src/rutas/`, `tests/`, `scripts/build_network.py` | 180 pruebas con pytest: casos resueltos a mano (spec), comparación con NetworkX (Dijkstra, 30 grafos aleatorios), SciPy (envolvente, 50 nubes + peor caso) y fuerza bruta vs. Held-Karp (40 matrices). Revisión manual de cada spec por el grupo. |
| 2026-11-05 | Claude Code (Opus 5.5) | Fase 0 (Juan): instalación del entorno, ejecución de pytest y revisión del código frente a las specs R1–R5 y el protocolo; lista de inconsistencias para discutir | `docs/anexo-ia.md` | `pytest`: 180 pruebas en verde (Python 3.14.7, OSMnx 2.1.1, NetworkX 3.7). Trazabilidad `Rx-Cyy` → prueba revisada con `grep`. Nota de R1-B12 contrastada con el docstring de la versión instalada. Inconsistencias revisadas por Juan. |
| 2026-11-05 | Claude Code (Opus 5.5) | Cambio de spec R1-B01 aprobado por Juan (memoria de la red descargada y de la CFC), nueva regla R1-B25 (archivos de `results/r1/`) y R1-B19 ampliada; correcciones de `build_network.py` (catálogo validado al inicio, centro de radios desde el catálogo, CSV con encabezado, fuente de la red), líneas ≤ 100 y citas de reglas en R1 y R2 | `specs/R1-modelo-red.md`, `scripts/build_network.py`, `src/rutas/catalog.py`, `data_io.py`, `network_model.py`, `shortest_paths.py`, `tests/test_r1_network_model.py` | `pytest`: 180 en verde; prueba manual sin red de `memory_rows`, `write_csv` vacío y validación del catálogo. Revisión del diff por Juan antes del commit. |
| 2026-11-05 | Claude Code (Opus 5.5) | Fase 2 (Juan, R1): ejecución de `inspect_scc.py` y `build_network.py` con el catálogo de la rama de Laura; búsqueda de la norma de velocidades (Ley 2251 de 2022, art. 12 y 13) y tabla `LEGAL_MAX_KMH` con el caso R1-C14; reorden del script (radios al final), metadatos de descarga y opción `--overpass-url` | `specs/R1-modelo-red.md`, `scripts/build_network.py`, `src/rutas/network_model.py`, `tests/test_r1_network_model.py`, `.gitignore`, `results/r1/`, `data/processed/` | `pytest`: 181 en verde. Texto de la ley leído en la página oficial del Senado. Tiempos de la CFC ajustados a una recta (R² = 0,994). Lugares lejanos revisados uno por uno contra `catalogo_verificacion.csv`. |

## Criterios del grupo

- Toda sugerencia de la IA pasa primero por una spec en `specs/`; si la IA propone
  algo que contradice la spec, se discute y se corrige la spec antes del código.
- Ningún resultado se acepta sin pruebas en verde.
- Cada integrante revisa y puede explicar los módulos generados con ayuda de IA
  antes de la sustentación.
