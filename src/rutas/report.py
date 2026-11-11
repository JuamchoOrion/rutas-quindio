"""Formato de números y tablas Markdown para el documento técnico.

Spec: specs/protocolo-experimental.md (PE-B09). Funciones puras: no leen ni recalculan
resultados; ``scripts/make_figures.py`` les pasa lo que lee de ``results/``.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

SIGNIFICANT_DIGITS = 3            # Tiempos y memoria (PE-B09).
DECIMAL_MARK = ","
THOUSANDS_SEPARATOR = " "
PLACEHOLDERS = frozenset({"", "—", "no completada"})   # Celdas que no deciden la alineación.
_NUMBER_RE = re.compile(r"^-?\d{1,3}( \d{3})*(,\d+)?\*?$|^-?\d+(,\d+)?\*?$")


def format_fixed(value: float, decimals: int) -> str:
    """``value`` con ``decimals`` decimales, coma decimal y espacio de miles (PE-B09)."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "\0").replace(".", DECIMAL_MARK).replace("\0", THOUSANDS_SEPARATOR)


def format_significant(value: float, digits: int = SIGNIFICANT_DIGITS) -> str:
    """``digits`` cifras significativas, sin notación científica; los valores con más
    cifras enteras que ``digits`` se muestran enteros (``155982.79`` → ``"155 983"``)."""
    if value == 0:
        return "0"
    decimals = _decimals_for(value, digits)
    rounded = round(value, decimals)
    if rounded != 0 and _magnitude(rounded) != _magnitude(value):   # 9,996 → 10,0
        decimals = _decimals_for(rounded, digits)
    return format_fixed(value, decimals)


def _magnitude(value: float) -> int:
    return math.floor(math.log10(abs(value)))


def _decimals_for(value: float, digits: int) -> int:
    return max(0, digits - 1 - _magnitude(value))


def format_ms(value: float) -> str:
    """Tiempo en milisegundos con 3 cifras significativas (PE-B09, PE-C08)."""
    return format_significant(value)


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Tabla Markdown; las columnas numéricas se alinean a la derecha (PE-B09, PE-C09).

    Una columna es numérica si todas sus celdas, sin contar ``PLACEHOLDERS``, son
    números ya formateados (coma decimal, espacio de miles, ``*`` opcional).
    """
    numeric = [_is_numeric_column([row[i] for row in rows]) for i in range(len(headers))]
    separator = ["---:" if is_numeric else "---" for is_numeric in numeric]
    lines = [_markdown_row(headers), _markdown_row(separator)]
    lines += [_markdown_row(row) for row in rows]
    return "\n".join(lines)


def _is_numeric_column(cells: Sequence[str]) -> bool:
    values = [cell for cell in cells if cell not in PLACEHOLDERS]
    return bool(values) and all(_NUMBER_RE.match(cell) for cell in values)


def _markdown_row(cells: Sequence[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def read_csv(path: str | Path) -> list[dict[str, str]]:
    """Filas de un CSV de ``results/`` como diccionarios de texto."""
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_markdown(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\n") + "\n", encoding="utf-8")
