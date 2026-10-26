"""R1 — Descarga la red vial, asigna pesos, extrae la CFC y asocia los lugares.

Spec: specs/R1-modelo-red.md

Uso (desde la raíz del repositorio, con el entorno activado):

    python scripts/build_network.py              # todo R1
    python scripts/build_network.py --sin-tiempos-scc   # omite la medición por radios

Requiere conexión a internet (OpenStreetMap) y ``pip install -e ".[red,dev]"``.
Si la descarga falla, poner el GraphML del docente en ``data/raw/quindio.graphml``:
el script lo usa en lugar de descargar.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone

import networkx as nx
import numpy as np
import osmnx as ox

from rutas import paths
from rutas.benchmark import machine_info, measure
from rutas.catalog import load_catalog, validate_catalog
from rutas.geo import FAR_THRESHOLD_M, nearest_node, to_utm, to_utm_many
from rutas.network_model import edge_speed_kmh, estimate_memory, travel_time_s

PLACE_QUERY = "Quindío, Colombia"
PLAZA_BOLIVAR_ARMENIA = (4.5339, -75.6811)  # TODO: verificar en el mapa (debe coincidir con el catálogo).
RADII_KM = (2, 5, 10, 20)
RAW_GRAPHML = paths.RAW / "quindio.graphml"


def download_department() -> tuple[nx.MultiDiGraph, str]:
    """Red ``drive`` del departamento y fecha de descarga (ISO 8601, R1-B19).

    ``retain_all=True`` conserva todas las componentes: así el conteo "antes de
    filtrar" es el de la red descargada y no el de la componente débil más grande
    que OSMnx deja por defecto.
    """
    if RAW_GRAPHML.exists():
        print(f"Usando {RAW_GRAPHML} (no se descarga)")
        modified = datetime.fromtimestamp(RAW_GRAPHML.stat().st_mtime, tz=timezone.utc)
        return ox.load_graphml(RAW_GRAPHML), modified.isoformat()
    graph = ox.graph_from_place(PLACE_QUERY, network_type="drive", retain_all=True)
    downloaded_at = datetime.now(timezone.utc).isoformat()
    ox.save_graphml(graph, RAW_GRAPHML)
    return graph, downloaded_at


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


def time_largest_component(graph: nx.MultiDiGraph) -> float:
    """Mediana (ms) de ``largest_component`` sobre ``graph`` (solo la llamada, PE-B02)."""
    return measure(lambda: ox.truncate.largest_component(graph, strongly=True)).median_ms


def scc_timing_table(department: nx.MultiDiGraph) -> list[dict]:
    """R1-B13/B14: tiempo de la CFC para radios crecientes y para el departamento."""
    rows = []
    for radius_km in RADII_KM:
        print(f"  descargando radio {radius_km} km…")
        sub = ox.graph_from_point(
            PLAZA_BOLIVAR_ARMENIA, dist=radius_km * 1000, network_type="drive", retain_all=True
        )
        rows.append(_scc_row(f"Radio de {radius_km} km", sub))
    rows.append(_scc_row("Departamento completo", department))
    return rows


def _scc_row(name: str, graph: nx.MultiDiGraph) -> dict:
    v, e = graph.number_of_nodes(), graph.number_of_edges()
    return {"red": name, "V": v, "E": e, "V_mas_E": v + e, "tiempo_ms": time_largest_component(graph)}


def associate_places(component: nx.MultiDiGraph) -> list[dict]:
    """R1-B15 a R1-B17: nodo de la CFC más cercano a cada lugar, en UTM 18N."""
    places = load_catalog(paths.CATALOG_CSV)
    errors = validate_catalog(places)
    if errors:
        raise SystemExit("Catálogo inválido:\n  - " + "\n  - ".join(errors))

    node_ids = list(component.nodes)
    xs, ys = to_utm_many(
        [component.nodes[n]["y"] for n in node_ids], [component.nodes[n]["x"] for n in node_ids]
    )
    rows = []
    for place in places:
        x, y = to_utm(place.lat, place.lon)
        index, distance = nearest_node(x, y, np.asarray(xs), np.asarray(ys))
        rows.append({
            "id": place.id,
            "nodo_osm": node_ids[index],
            "distancia_m": round(distance, 1),
            "lejano": distance > FAR_THRESHOLD_M,
        })
    return rows


def write_csv(path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        if not rows:
            return
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sin-tiempos-scc", action="store_true", help="omite R1-B13 (radios)")
    args = parser.parse_args()

    for folder in (paths.RAW, paths.PROCESSED, paths.R1):
        folder.mkdir(parents=True, exist_ok=True)
    (paths.R1 / "maquina.json").write_text(json.dumps(machine_info(), indent=2), encoding="utf-8")

    print("1/5 Descargando la red del departamento…")
    department, downloaded_at = download_department()

    print("2/5 Asignando pesos…")
    speed_sources = add_weights(department)
    write_csv(paths.R1 / "velocidades_origen.csv",
              [{"origen": k, "aristas": v} for k, v in speed_sources.items()])

    print("3/5 Componente fuertemente conexa…")
    component = ox.truncate.largest_component(department, strongly=True)
    sizes = [
        {"red": "Red descargada", "nodos": department.number_of_nodes(), "aristas": department.number_of_edges()},
        {"red": "Componente fuertemente conexa", "nodos": component.number_of_nodes(), "aristas": component.number_of_edges()},
    ]
    write_csv(paths.R1 / "red_tamanos.csv", sizes)

    memory = estimate_memory(component.number_of_nodes(), component.number_of_edges())
    (paths.R1 / "memoria.json").write_text(json.dumps(memory.__dict__, indent=2), encoding="utf-8")

    if not args.sin_tiempos_scc:
        print("   midiendo largest_component en redes de tamaño creciente…")
        write_csv(paths.R1 / "scc_tiempos.csv", scc_timing_table(department))

    print("4/5 Asociando lugares del catálogo…")
    associations = associate_places(component)
    write_csv(paths.PLACE_NODES_CSV, associations)
    write_csv(paths.R1 / "lugares_lejanos.csv", [r for r in associations if r["lejano"]])

    print("5/5 Guardando el grafo procesado…")
    ox.save_graphml(component, paths.NETWORK_GRAPHML)
    summary = {
        "fecha_descarga": downloaded_at,
        "consulta": PLACE_QUERY,
        "osmnx": ox.__version__,
        "networkx": nx.__version__,
        "tamanos": sizes,
    }
    paths.NETWORK_SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Listo. Resultados en results/r1/ y data/processed/")


if __name__ == "__main__":
    main()
