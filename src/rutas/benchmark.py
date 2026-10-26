"""Protocolo experimental: repeticiones, mediana, límite de tiempo y datos de la máquina.

Spec: specs/protocolo-experimental.md (PE-B01 a PE-B08).
"""

from __future__ import annotations

import multiprocessing as mp
import os
import platform
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

SEED = 20262                   # Semilla única de todos los experimentos (PE-B05).
REPETITIONS = 5                # PE-B03
LONG_RUN_S = 60.0              # Ejecuciones más largas se miden una sola vez (PE-B03).
TIMEOUT_S = 300.0              # Límite de 5 minutos (PE-B07).

_NS_PER_MS = 1_000_000


@dataclass
class Measurement:
    """Resultado de medir una función. Tiempos en milisegundos (PE-B04)."""

    samples_ms: list[float] = field(default_factory=list)
    completed: bool = True
    result: Any = None

    @property
    def median_ms(self) -> float | None:
        return median(self.samples_ms) if self.samples_ms else None


def median(values: Sequence[float]) -> float:
    """Mediana (promedio de los dos centrales si la cantidad es par)."""
    if not values:
        raise ValueError("La mediana de una lista vacía no está definida")
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def _timed_call(fn: Callable[[], Any]) -> tuple[float, Any]:
    """Cronometra solo la llamada (PE-B02). Devuelve (ms, valor de retorno)."""
    start = time.perf_counter_ns()
    result = fn()
    elapsed_ms = (time.perf_counter_ns() - start) / _NS_PER_MS
    return elapsed_ms, result


def measure(
    fn: Callable[[], Any],
    repetitions: int = REPETITIONS,
    long_run_s: float = LONG_RUN_S,
) -> Measurement:
    """Ejecuta ``fn`` ``repetitions`` veces; si la primera dura más de ``long_run_s``, solo una.

    ``fn`` no recibe argumentos: los datos se preparan antes y se capturan en un
    ``lambda`` para que su preparación no se mida.
    """
    measurement = Measurement()
    for run in range(repetitions):
        elapsed_ms, result = _timed_call(fn)
        measurement.samples_ms.append(elapsed_ms)
        measurement.result = result
        if run == 0 and elapsed_ms > long_run_s * 1000:
            break
    return measurement


def _child(fn, repetitions, long_run_s, connection) -> None:
    """Proceso hijo: envía cada muestra apenas termina para que el padre vigile el límite."""
    for run in range(repetitions):
        elapsed_ms, result = _timed_call(fn)
        is_last = run == repetitions - 1 or (run == 0 and elapsed_ms > long_run_s * 1000)
        connection.send((elapsed_ms, result if is_last else None, is_last))
        if is_last:
            break
    connection.close()


def measure_with_timeout(
    fn: Callable[[], Any],
    repetitions: int = REPETITIONS,
    timeout_s: float = TIMEOUT_S,
    long_run_s: float = LONG_RUN_S,
) -> Measurement:
    """Como :func:`measure`, pero ninguna ejecución puede durar más de ``timeout_s``.

    Las ejecuciones corren en un proceso hijo. Si una pasa el límite, el hijo se
    termina y se devuelve ``completed=False`` (PE-B07). En Linux se usa ``fork``,
    así que ``fn`` puede ser un ``lambda``; en Windows/macOS (``spawn``) debe poder
    serializarse con ``pickle`` (por ejemplo ``functools.partial`` de una función
    de módulo).
    """
    method = "fork" if "fork" in mp.get_all_start_methods() else "spawn"
    context = mp.get_context(method)
    parent_conn, child_conn = context.Pipe(duplex=False)
    process = context.Process(
        target=_child, args=(fn, repetitions, long_run_s, child_conn), daemon=True
    )
    process.start()
    child_conn.close()

    measurement = Measurement()
    try:
        while True:
            if not parent_conn.poll(timeout_s):
                measurement.completed = False
                break
            elapsed_ms, result, is_last = parent_conn.recv()
            measurement.samples_ms.append(elapsed_ms)
            if is_last:
                measurement.result = result
                break
    except EOFError:  # El hijo terminó con un error.
        measurement.completed = False
    finally:
        if process.is_alive():
            process.terminate()
        process.join()
        parent_conn.close()
    return measurement


def machine_info() -> dict[str, Any]:
    """Procesador, RAM, sistema operativo y versión de Python (PE-B01)."""
    info: dict[str, Any] = {
        "procesador": _cpu_model(),
        "nucleos_logicos": os.cpu_count(),
        "ram_gb": _ram_gb(),
        "sistema_operativo": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "implementacion": platform.python_implementation(),
        "semilla": SEED,
    }
    return info


def _cpu_model() -> str:
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as file:
            for line in file:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def _ram_gb() -> float | None:
    try:
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9, 1)
    except (ValueError, OSError, AttributeError):
        return None  # Windows: completar a mano en maquina.json.
