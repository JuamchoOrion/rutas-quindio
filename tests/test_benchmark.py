"""Pruebas de specs/protocolo-experimental.md."""

import time

from rutas.benchmark import measure, measure_with_timeout, median


def test_PE_C01_five_samples_and_median():
    measurement = measure(lambda: time.sleep(0.001))
    assert len(measurement.samples_ms) == 5
    assert min(measurement.samples_ms) <= measurement.median_ms <= max(measurement.samples_ms)


def test_PE_C01_long_run_is_measured_once():
    measurement = measure(lambda: time.sleep(0.02), long_run_s=0.01)
    assert len(measurement.samples_ms) == 1


def test_PE_C02_timeout_marks_not_completed():
    start = time.perf_counter()
    measurement = measure_with_timeout(lambda: time.sleep(3), timeout_s=1)
    assert measurement.completed is False
    assert time.perf_counter() - start < 2.5


def test_PE_C03_fast_function_completes_with_result():
    measurement = measure_with_timeout(lambda: sum(range(1000)), timeout_s=10)
    assert measurement.completed is True
    assert measurement.result == 499_500
    assert len(measurement.samples_ms) == 5


def test_PE_C04_median():
    assert median([5, 1, 3]) == 3
    assert median([4, 1, 3, 2]) == 2.5
