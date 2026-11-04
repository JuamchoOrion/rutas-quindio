"""Pruebas de specs/catalogo.md sobre los archivos reales de data/. Cada prueba cita su ID."""

import ast
import csv
import datetime
import re
from pathlib import Path

import pytest

from rutas import paths
from rutas.catalog import DEFAULT_START_ID, load_catalog, validate_catalog

VERIFICATION_CSV = paths.CATALOG_CSV.parent / "catalogo_verificacion.csv"
BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_network.py"
VERIFICATION_COLUMNS = ["id", "coordenada_verificada", "nota"]
ALLOWED_VALUES = {"si", "no"}
ARMENIA_NOTE = "copiada de PLAZA_BOLIVAR_ARMENIA (también sin verificar)"
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
PENDING_PREFIX = "PENDIENTE"
PENDING_PLACE_NOTE = "PENDIENTE: buscar lugar real"


def read_verification() -> tuple[list[str], list[dict[str, str]]]:
    with open(VERIFICATION_CSV, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def plaza_bolivar_constant() -> tuple[float, float]:
    """Lee PLAZA_BOLIVAR_ARMENIA con ``ast`` para no importar el script ni OSMnx."""
    tree = ast.parse(BUILD_SCRIPT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "PLAZA_BOLIVAR_ARMENIA" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("PLAZA_BOLIVAR_ARMENIA no está en scripts/build_network.py")


def test_CAT_C01_ids_match_one_to_one():
    catalog_ids = [place.id for place in load_catalog(paths.CATALOG_CSV)]
    _, rows = read_verification()
    verification_ids = [row["id"] for row in rows]
    assert len(verification_ids) == len(set(verification_ids)), "ids repetidos"
    assert set(verification_ids) == set(catalog_ids)


def test_CAT_C02_columns_values_and_notes():
    columns, rows = read_verification()
    assert columns == VERIFICATION_COLUMNS
    assert {row["coordenada_verificada"] for row in rows} <= ALLOWED_VALUES
    for row in rows:
        if row["coordenada_verificada"] == "no":
            assert row["nota"].strip(), f"'{row['id']}' está en 'no' sin nota"
        if row["nota"].startswith(PENDING_PREFIX):
            assert row["coordenada_verificada"] == "no", (
                f"'{row['id']}' es PENDIENTE y está en 'si'"
            )


def test_CAT_C03_verified_rows_have_iso_date():
    _, rows = read_verification()
    for row in rows:
        if row["coordenada_verificada"] == "si":
            match = ISO_DATE.search(row["nota"])
            assert match, f"'{row['id']}' está verificada pero su nota no tiene fecha"
            datetime.date.fromisoformat(match.group())  # Lanza si la fecha no es válida.


def test_CAT_C04_real_catalog_is_valid():
    assert validate_catalog(load_catalog(paths.CATALOG_CSV)) == []


def test_CAT_C05_armenia_matches_build_network_constant():
    armenia = next(p for p in load_catalog(paths.CATALOG_CSV) if p.id == DEFAULT_START_ID)
    assert (armenia.lat, armenia.lon) == plaza_bolivar_constant()
    _, rows = read_verification()
    row = next(r for r in rows if r["id"] == DEFAULT_START_ID)
    if row["coordenada_verificada"] == "no":
        assert row["nota"] == ARMENIA_NOTE


def test_CAT_C06_pending_places_are_reported_without_failing():
    """CAT-B04: avisa (skip) qué lugares faltan por buscar; nunca falla."""
    _, rows = read_verification()
    pending = [row["id"] for row in rows if row["nota"].startswith(PENDING_PLACE_NOTE)]
    if pending:
        pytest.skip(f"Lugares PENDIENTE antes de ejecutar R1: {pending}")
