# Especificaciones (Spec-Driven Development)

Este directorio es la **fuente de verdad** del proyecto. Ningún módulo se programa
sin que exista antes su especificación, y ninguna especificación se da por
cumplida hasta que todos sus casos de prueba pasan.

## Flujo de trabajo

```
1. Especificar  →  2. Escribir pruebas  →  3. Implementar  →  4. Verificar  →  5. Medir
   specs/Rx.md      tests/test_*.py         src/rutas/*.py     pytest            scripts/
```

1. **Especificar.** Se escribe (o actualiza) la spec del requerimiento: entradas,
   salidas, comportamiento esperado, complejidad esperada y casos de prueba con ID.
2. **Pruebas.** Cada caso de la spec se traduce en una prueba cuyo nombre o
   docstring contiene el ID del caso (por ejemplo `R2-C03`). Así se puede rastrear
   `spec → prueba → código` con `grep -r "R2-C03"`.
3. **Implementar.** Se implementa lo mínimo para que las pruebas pasen, respetando
   las restricciones de "implementación propia" del enunciado.
4. **Verificar.** `pytest` en verde. Un algoritmo rápido pero incorrecto no cuenta
   como implementado (sección 6.6 del enunciado).
5. **Medir.** Solo después de verificar se ejecutan los experimentos (protocolo en
   [`protocolo-experimental.md`](protocolo-experimental.md)).

Si durante la implementación se descubre que la spec estaba mal o incompleta, **se
corrige primero la spec** (en un commit propio) y después el código.

## Índice

| Spec | Requerimiento | Peso |
|---|---|---|
| [R1-modelo-red.md](R1-modelo-red.md) | Modelo de la red vial | 15 % |
| [R2-caminos-minimos.md](R2-caminos-minimos.md) | Dijkstra lineal y con cola de prioridad, matriz de tiempos | 20 % |
| [R3-envolvente-convexa.md](R3-envolvente-convexa.md) | Envolvente convexa por divide y vencerás (QuickHull) | 20 % |
| [R4-ruta-optima.md](R4-ruta-optima.md) | ATSP: fuerza bruta, Held-Karp, heurística voraz, itinerario | 25 % |
| [R5-aplicacion.md](R5-aplicacion.md) | Aplicación demostrativa | 5 % |
| [protocolo-experimental.md](protocolo-experimental.md) | Reglas comunes de medición | — |

## Plantilla de una spec

```markdown
# Rx — Nombre

## Contexto
Qué problema resuelve y de qué requerimiento del enunciado viene.

## Interfaz
Firma de las funciones públicas, tipos de entrada y salida.

## Comportamiento esperado
Reglas numeradas (Rx-B01, Rx-B02, …) que el código debe cumplir.

## Complejidad esperada
Tiempo y memoria, con la fuente que se citará en el documento técnico.

## Casos de prueba
| ID | Entrada | Resultado esperado |

## Fuera de alcance
Lo que esta spec no cubre.
```

## Uso con asistentes de IA

Cuando se le pida a una IA (Claude Code u otra) implementar o modificar algo, se le
indica la spec correspondiente: *"implementa R4-B05 según specs/R4-ruta-optima.md
y agrega la prueba R4-C09"*. Toda respuesta de la IA se verifica con las pruebas y
se registra en el anexo de uso de IA del documento técnico.
