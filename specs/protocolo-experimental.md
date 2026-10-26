# Protocolo experimental

Fuente: sección 6 del enunciado. Aplica a **todas** las mediciones de R1–R4.
Implementación: `src/rutas/benchmark.py`.

## Reglas

| ID | Regla | Cómo se cumple en el código |
|---|---|---|
| PE-B01 | Las mediciones de un requerimiento se hacen en la misma máquina; se reportan CPU, RAM, SO y versión del lenguaje. | `benchmark.machine_info()` genera un diccionario que cada script guarda en `results/<rX>/maquina.json`. |
| PE-B02 | Solo se mide el algoritmo (no lectura de archivos, generación de datos ni impresión). | `measure()` recibe una función ya preparada sin argumentos (`lambda`) y cronometra solo su llamada con `time.perf_counter_ns`. |
| PE-B03 | Cada medición se repite 5 veces y se reporta la mediana; si una ejecución dura más de 1 minuto, se mide una sola vez. | `measure(fn, repetitions=5)`: si la primera corrida pasa de 60 s, devuelve esa única medición. |
| PE-B04 | Todos los tiempos en una misma unidad. | Se usa **milisegundos** (`float`) en todos los CSV; la columna se llama `tiempo_ms`. |
| PE-B05 | Datos aleatorios con semilla fija documentada. | Constante `SEED = 20262` en `benchmark.py`; cada script la registra en su CSV de salida. |
| PE-B06 | Cada algoritmo se verifica antes de medirse. | Los scripts de experimento llaman a la verificación correspondiente y abortan si falla. |
| PE-B07 | Si una ejecución pasa de 5 minutos, se detiene y se reporta como **no completada**. | `measure_with_timeout(fn, timeout_s=300)` ejecuta en un proceso hijo y lo termina al vencer el plazo; devuelve `completed=False`. |
| PE-B08 | Resultados en CSV/JSON; tablas y gráficas se generan **desde esos archivos**. | Los scripts `scripts/run_rX.py` escriben CSV en `results/rX/`; `scripts/make_figures.py` lee esos CSV. |

## Casos de prueba

| ID | Entrada | Resultado esperado |
|---|---|---|
| PE-C01 | `measure` de una función que tarda ~1 ms, 5 repeticiones | Devuelve 5 muestras y la mediana entre la mínima y la máxima. |
| PE-C02 | `measure_with_timeout` de una función que duerme 3 s con límite de 1 s | `completed=False`, sin excepción, en poco más de 1 s. |
| PE-C03 | `measure_with_timeout` de una función rápida | `completed=True` y el valor de retorno disponible. |
| PE-C04 | `median` de `[5, 1, 3]` y de `[4, 1, 3, 2]` | `3` y `2.5`. |
