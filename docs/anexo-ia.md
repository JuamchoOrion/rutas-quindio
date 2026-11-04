# Anexo — Uso de inteligencia artificial

Exigido por la sección 3 del enunciado. Se actualiza en cada sesión de trabajo con IA.

| Fecha | Herramienta | Para qué se usó | Archivos afectados | Cómo se verificó |
|---|---|---|---|---|
| 2026-10-26 | Claude (claude.ai) | Estructura del repositorio, specs iniciales de R1–R5 y del protocolo, implementación de los algoritmos de R2–R4 y utilidades de R1 | `specs/`, `src/rutas/`, `tests/`, `scripts/build_network.py` | 180 pruebas con pytest: casos resueltos a mano (spec), comparación con NetworkX (Dijkstra, 30 grafos aleatorios), SciPy (envolvente, 50 nubes + peor caso) y fuerza bruta vs. Held-Karp (40 matrices). Revisión manual de cada spec por el grupo. |
| 2026-11-03 | Claude Code (Opus 5.5) | Fase 0: revisión del cumplimiento de las specs R3 y R4 y del estado del catálogo, sin cambios de código | Ninguno (solo este anexo) | `pytest`: 180 pruebas en verde. Hallazgos reproducidos: empate de distancia en QuickHull comparado con SciPy (ejemplo de 5 puntos) y conteo de iteraciones de la fuerza bruta para k = 5..10. |
| 2026-11-03 | Claude Code (Opus 5.5) | Fase 1: cambios de spec aprobados por el grupo (R3-B08, R4-B01, R4-B05, R4-C11, formatos de salida de R3/R4) y su implementación: desempate en QuickHull, fuerza bruta por intercambios, validación de la diagonal, citas de reglas | `specs/R3-envolvente-convexa.md`, `specs/R4-ruta-optima.md`, `src/rutas/convex_hull.py`, `src/rutas/tsp.py`, `src/rutas/itinerary.py`, `tests/test_r3_convex_hull.py`, `tests/test_r4_tsp.py` | Pruebas nuevas (R3-C11, R4-C10 en los tres métodos) escritas antes del código y vistas fallar; luego `pytest` con 193 pruebas en verde. R3-C11 comparado también con SciPy. Conteo de iteraciones de la nueva fuerza bruta: ≈ 2.718·k! para k = 5..10 (antes ≈ 1.718·k·k!). |

## Criterios del grupo

- Toda sugerencia de la IA pasa primero por una spec en `specs/`; si la IA propone
  algo que contradice la spec, se discute y se corrige la spec antes del código.
- Ningún resultado se acepta sin pruebas en verde.
- Cada integrante revisa y puede explicar los módulos generados con ayuda de IA
  antes de la sustentación.
