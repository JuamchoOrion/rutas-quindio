"""R1 — Descarga la red vial, asigna pesos, extrae la CFC y asocia los lugares.

Spec: specs/R1-modelo-red.md

Uso (desde la raíz del repositorio, con el entorno activado):

    python scripts/build_network.py              # todo R1
    python scripts/build_network.py --sin-tiempos-scc   # omite la medición por radios
    python scripts/build_network.py --overpass-url https://maps.mail.ru/osm/tools/overpass/api
                                                 # espejo si overpass-api.de rechaza la conexión

Requiere conexión a internet (OpenStreetMap) y ``pip install -e ".[red,dev]"``.
Si la descarga falla, poner el GraphML del docente en ``data/raw/quindio.graphml``:
el script lo usa en lugar de descargar (R1-B19).
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox

from rutas import paths
from rutas.benchmark import machine_info, measure
from rutas.catalog import DEFAULT_START_ID, Place, load_catalog, validate_catalog
from rutas.geo import FAR_THRESHOLD_M, nearest_node, to_utm, to_utm_many
from rutas.network_model import edge_speed_kmh, estimate_memory, travel_time_s

PLACE_QUERY = "Quindío, Colombia"
# Centro de las redes por radio (R1-B13). CAT-C05 comprueba que coincide con el lugar
# `armenia` del catálogo; start_point() lo vuelve a comprobar al ejecutar.
PLAZA_BOLIVAR_ARMENIA = (4.5339, -75.6811)
RADII_KM = (2, 5, 10, 20)
METERS_PER_KM = 1000
RAW_GRAPHML = paths.RAW / "quindio.graphml"
# Fecha y fuente de la descarga, para no perderlas al reusar RAW_GRAPHML (R1-B19).
RAW_METADATA_JSON = paths.RAW / "quindio_descarga.json"
DOWNLOADED_NAME = "Red descargada"
COMPONENT_NAME = "Componente fuertemente conexa"
PLACE_NODE_COLUMNS = ["id", "nodo_osm", "distancia_m", "lejano"]


def load_valid_catalog() -> list[Place]:
    """Carga el catálogo y aborta si no cumple R1-B20 a R1-B24 (antes de descargar, R1-B25)."""
    places = load_catalog(paths.CATALOG_CSV)
    errors = validate_catalog(places)
    if errors:
        raise SystemExit("Catálogo inválido:\n  - " + "\n  - ".join(errors))
    return places


def start_point(places: Sequence[Place]) -> tuple[float, float]:
    """Centro de las redes por radio (R1-B13); aborta si no coincide con el catálogo (R1-B23)."""
    start = next(place for place in places if place.id == DEFAULT_START_ID)
    if (start.lat, start.lon) != PLAZA_BOLIVAR_ARMENIA:
        raise SystemExit(
            f"PLAZA_BOLIVAR_ARMENIA {PLAZA_BOLIVAR_ARMENIA} no coincide con '{DEFAULT_START_ID}' "
            f"del catálogo ({start.lat}, {start.lon}); ver specs/catalogo.md (CAT-B05)"
        )
    return PLAZA_BOLIVAR_ARMENIA


def download_department() -> tuple[nx.MultiDiGraph, str, str]:
    """Red ``drive`` del departamento, fecha ISO 8601 y fuente de la red (R1-B19).

    ``retain_all=True`` conserva todas las componentes: así el conteo "antes de
    filtrar" es el de la red descargada y no el de la componente débil más grande
    que OSMnx deja por defecto.
    """
    if RAW_GRAPHML.exists():
        print(f"Usando {RAW_GRAPHML} (no se descarga)")
        return ox.load_graphml(RAW_GRAPHML), *_raw_metadata()
    graph = ox.graph_from_place(PLACE_QUERY, network_type="drive", retain_all=True)
    downloaded_at = datetime.now(timezone.utc).isoformat()
    ox.save_graphml(graph, RAW_GRAPHML)
    source = "descarga con OSMnx"
    write_json(RAW_METADATA_JSON, {"fecha_descarga": downloaded_at, "fuente_red": source})
    return graph, downloaded_at, source


def _raw_metadata() -> tuple[str, str]:
    """Fecha y fuente de RAW_GRAPHML: las de su descarga o, si es el GraphML del docente,
    la fecha de modificación del archivo (R1-B19)."""
    if RAW_METADATA_JSON.exists():
        metadata = json.loads(RAW_METADATA_JSON.read_text(encoding="utf-8"))
        return metadata["fecha_descarga"], metadata["fuente_red"]
    modified = datetime.fromtimestamp(RAW_GRAPHML.stat().st_mtime, tz=timezone.utc)
    source = f"GraphML local {RAW_GRAPHML.name} (fecha = modificación del archivo)"
    return modified.isoformat(), source


def add_weights(graph: nx.MultiDiGraph) -> Counter:
    """Agrega ``length_m``, ``speed_kmh``, ``speed_source`` y ``travel_time_s`` (R1-B06 a B09)."""
    sources: Counter = Counter()
    for _, _, data in graph.edges(data=True):
        speed, source = edge_speed_kmh(data.get("maxspeed"), data.get("highway"))
        data["length_m"] = float(data["length"])
        data["speed_kmh"] = speed
        data["speed_source"] = source
        data["travel_time_s"] = travel_time_s(data["length_m"], speed)
        sources[source] += 1
    return sources


def largest_scc(graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """CFC más grande con OSMnx (R1-B11); el algoritmo interno se documenta con inspect_scc.py."""
    return ox.truncate.largest_component(graph, strongly=True)


def time_largest_component(graph: nx.MultiDiGraph) -> float:
    """Mediana (ms) de ``largest_component`` sobre ``graph`` (solo la llamada, PE-B02)."""
    return measure(lambda: largest_scc(graph)).median_ms


def scc_timing_table(department: nx.MultiDiGraph, center: tuple[float, float]) -> list[dict]:
    """R1-B13/B14: tiempo de la CFC para radios crecientes y para el departamento."""
    rows = []
    for radius_km in RADII_KM:
        print(f"  descargando radio {radius_km} km…")
        sub = ox.graph_from_point(
            center, dist=radius_km * METERS_PER_KM, network_type="drive", retain_all=True
        )
        rows.append(_scc_row(f"Radio de {radius_km} km", sub))
    rows.append(_scc_row("Departamento completo", department))
    return rows


def _scc_row(name: str, graph: nx.MultiDiGraph) -> dict:
    v, e = graph.number_of_nodes(), graph.number_of_edges()
    return {"red": name, "V": v, "E": e, "V_mas_E": v + e,
            "tiempo_ms": time_largest_component(graph)}


def memory_rows(networks: dict[str, nx.MultiDiGraph]) -> list[dict]:
    """R1-B01 a B04: estimación de memoria con el V y E reales de cada red."""
    rows = []
    for name, graph in networks.items():
        memory = estimate_memory(graph.number_of_nodes(), graph.number_of_edges())
        rows.append({
            "red": name,
            "V": memory.n_nodes,
            "E": memory.n_edges,
            "densidad": memory.density,
            "matriz_mb": memory.matrix_mb,
            "listas_mb": memory.lists_mb,
            "supuestos": memory.assumptions,
        })
    return rows


def associate_places(component: nx.MultiDiGraph, places: Sequence[Place]) -> list[dict]:
    """R1-B15 a R1-B17: nodo de la CFC más cercano (euclidiano, UTM 18N) a cada lugar."""
    node_ids = list(component.nodes)
    xs, ys = to_utm_many(
        [component.nodes[n]["y"] for n in node_ids], [component.nodes[n]["x"] for n in node_ids]
    )
    rows = []
    for place in places:
        x, y = to_utm(place.lat, place.lon)
        index, distance = nearest_node(x, y, np.asarray(xs), np.asarray(ys))  # R1-B16
        rows.append({
            "id": place.id,
            "nodo_osm": node_ids[index],
            "distancia_m": round(distance, 1),
            "lejano": distance > FAR_THRESHOLD_M,
        })
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: Sequence[str] | None = None) -> None:
    """Escribe ``rows`` con encabezado, aunque no haya filas si se da ``fieldnames`` (R1-B25)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(fieldnames) if fieldnames is not None else list(rows[0]) if rows else []
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sin-tiempos-scc", action="store_true", help="omite R1-B13 (radios)")
    parser.add_argument("--overpass-url", help="servidor Overpass alterno (por defecto el de OSMnx)")
    args = parser.parse_args()
    if args.overpass_url:
        ox.settings.overpass_url = args.overpass_url

    for folder in (paths.RAW, paths.PROCESSED, paths.R1):
        folder.mkdir(parents=True, exist_ok=True)

    print("0/6 Validando el catálogo…")
    places = load_valid_catalog()
    center = start_point(places)
    write_json(paths.R1 / "maquina.json", machine_info())

    print("1/6 Descargando la red del departamento…")
    department, downloaded_at, network_source = download_department()

    print("2/6 Asignando pesos…")
    speed_sources = add_weights(department)
    write_csv(paths.R1 / "velocidades_origen.csv",
              [{"origen": k, "aristas": v} for k, v in speed_sources.items()])

    print("3/6 Componente fuertemente conexa…")
    component = largest_scc(department)
    networks = {DOWNLOADED_NAME: department, COMPONENT_NAME: component}
    sizes = [{"red": name, "nodos": g.number_of_nodes(), "aristas": g.number_of_edges()}
             for name, g in networks.items()]
    write_csv(paths.R1 / "red_tamanos.csv", sizes)
    write_csv(paths.R1 / "memoria.csv", memory_rows(networks))

    print("4/6 Asociando lugares del catálogo…")
    associations = associate_places(component, places)
    write_csv(paths.PLACE_NODES_CSV, associations, PLACE_NODE_COLUMNS)
    write_csv(paths.R1 / "lugares_lejanos.csv",
              [r for r in associations if r["lejano"]], PLACE_NODE_COLUMNS)

    print("5/6 Guardando el grafo procesado…")
    ox.save_graphml(component, paths.NETWORK_GRAPHML)
    write_json(paths.NETWORK_SUMMARY_JSON, {
        "fecha_descarga": downloaded_at,
        "fuente_red": network_source,
        "consulta": PLACE_QUERY,
        "osmnx": ox.__version__,
        "overpass_radios_scc": ox.settings.overpass_url,  # servidor de las redes por radio
        "networkx": nx.__version__,
        "tamanos": sizes,
    })
    if not args.sin_tiempos_scc:
        # Al final: depende de Overpass y, si falla, lo anterior ya quedó guardado.
        print("6/6 Midiendo largest_component en redes de tamaño creciente…")
        write_csv(paths.R1 / "scc_tiempos.csv", scc_timing_table(department, center))
    print("Listo. Resultados en results/r1/ y data/processed/")


if __name__ == "__main__":
    main()
