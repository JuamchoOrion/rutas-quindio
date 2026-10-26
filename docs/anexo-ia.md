# Anexo — Uso de inteligencia artificial

Exigido por la sección 3 del enunciado. Se actualiza en cada sesión de trabajo con IA.

| Fecha | Herramienta | Para qué se usó | Archivos afectados | Cómo se verificó |
|---|---|---|---|---|
| 2026-10-26 | Claude (claude.ai) | Estructura del repositorio, specs iniciales de R1–R5 y del protocolo, implementación de los algoritmos de R2–R4 y utilidades de R1 | `specs/`, `src/rutas/`, `tests/`, `scripts/build_network.py` | 180 pruebas con pytest: casos resueltos a mano (spec), comparación con NetworkX (Dijkstra, 30 grafos aleatorios), SciPy (envolvente, 50 nubes + peor caso) y fuerza bruta vs. Held-Karp (40 matrices). Revisión manual de cada spec por el grupo. |

## Criterios del grupo

- Toda sugerencia de la IA pasa primero por una spec en `specs/`; si la IA propone
  algo que contradice la spec, se discute y se corrige la spec antes del código.
- Ningún resultado se acepta sin pruebas en verde.
- Cada integrante revisa y puede explicar los módulos generados con ayuda de IA
  antes de la sustentación.
