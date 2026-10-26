"""Rutas de archivos del proyecto (un solo lugar para no repetir cadenas)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATA = ROOT / "data"
CATALOG_CSV = DATA / "catalogo.csv"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
NETWORK_GRAPHML = PROCESSED / "red_cfc.graphml"
PLACE_NODES_CSV = PROCESSED / "lugares_nodos.csv"
NETWORK_SUMMARY_JSON = PROCESSED / "red_resumen.json"

RESULTS = ROOT / "results"
R1 = RESULTS / "r1"
R2 = RESULTS / "r2"
R3 = RESULTS / "r3"
R4 = RESULTS / "r4"
