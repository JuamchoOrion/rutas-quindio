"""Pruebas de specs/protocolo-experimental.md."""

import io
import subprocess
import time

import pytest

from rutas import benchmark
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


def _no_proc_cpuinfo(*args, **kwargs):
    raise OSError("sin /proc/cpuinfo")


def _fake_sysctl(stdout: str):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=stdout, stderr="")
    return run


def _failing_sysctl(error: Exception):
    def run(*args, **kwargs):
        raise error
    return run


def test_PE_C05_macos_uses_sysctl(monkeypatch):
    monkeypatch.setattr(benchmark.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(benchmark.subprocess, "run", _fake_sysctl("Apple M2\n"))
    assert benchmark._cpu_model() == "Apple M2"


@pytest.mark.parametrize("sysctl", [
    _failing_sysctl(FileNotFoundError("sysctl")),
    _failing_sysctl(subprocess.CalledProcessError(1, "sysctl")),
    _failing_sysctl(subprocess.TimeoutExpired("sysctl", 2)),
    _fake_sysctl("  \n"),
])
def test_PE_C06_macos_sysctl_failure_falls_back(monkeypatch, sysctl):
    monkeypatch.setattr(benchmark.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(benchmark.subprocess, "run", sysctl)
    monkeypatch.setattr(benchmark, "open", _no_proc_cpuinfo, raising=False)
    monkeypatch.setattr(benchmark.platform, "processor", lambda: "")
    monkeypatch.setattr(benchmark.platform, "machine", lambda: "arm64")
    assert benchmark._cpu_model() == "arm64"


def test_PE_C07_linux_reads_proc_cpuinfo_without_sysctl(monkeypatch):
    cpuinfo = "processor\t: 0\nmodel name\t: Intel(R) Core(TM) i5\n"
    monkeypatch.setattr(benchmark.platform, "system", lambda: "Linux")
    monkeypatch.setattr(benchmark.subprocess, "run", _failing_sysctl(AssertionError("sysctl")))
    monkeypatch.setattr(benchmark, "open", lambda *a, **k: io.StringIO(cpuinfo), raising=False)
    assert benchmark._cpu_model() == "Intel(R) Core(TM) i5"
