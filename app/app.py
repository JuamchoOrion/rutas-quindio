"""R5 — Aplicación demostrativa: rutas, envolvente, itinerario y resultados de R1–R4.

Spec: specs/R5-aplicacion.md

Uso (desde la raíz del repositorio):

    pip install -e ".[red,app]"
    streamlit run app/app.py

Solo lee archivos (data/processed/ y results/); nunca descarga la red (R5-B05).
La lógica sin interfaz está en ``rutas.app_support``.
"""

from __future__ import annotations

from collections.abc import Sequence

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from rutas import paths
from rutas.app_support import (
    TourComparison,
    compare_tours,
    hull_latlons,
    result_files,
    route_latlons,
    tour_legs,
)
from rutas.catalog import DEFAULT_START_ID, Place
from rutas.data_io import ProcessedNetwork, load_processed_network, load_travel_time_matrix
from rutas.itinerary import MAX_ATTRACTIONS, MIN_ATTRACTIONS, WORKDAY_S, DayPlan, plan_day
from rutas.shortest_paths import dijkstra_heap
from rutas.tsp import instance_matrix

MATRIX_CSV = paths.R2 / "matriz_tiempos.csv"
HULL_JSON = paths.R3 / "envolvente_red.json"
QUINDIO_CENTER = (4.45, -75.68)
DEPARTMENT_ZOOM = 10
MAP_HEIGHT_PX = 520
SECONDS_PER_MINUTE = 60.0
SECONDS_PER_HOUR = 3600.0
ROUTE_COLOR = "#1f6feb"
OPTIMAL_COLOR = "#1f6feb"
HEURISTIC_COLOR = "#e8590c"
HULL_COLOR = "#2f9e44"
# Categoría → (color del marcador, nombre del color en la leyenda de Streamlit).
CATEGORY_COLORS = {
    "cabecera": ("#495057", "gray"),
    "atractivo": ("#c92a2a", "red"),
    "finca_hotel": ("#2f9e44", "green"),
    "acopio": ("#7950f2", "violet"),
}
# Script que genera cada carpeta de resultados (aviso de R5-B06).
RESULT_SOURCES = {
    "R1 · Modelo de la red": (paths.R1, "scripts/build_network.py"),
    "R2 · Caminos mínimos": (paths.R2, "scripts/run_r2.py"),
    "R3 · Envolvente convexa": (paths.R3, "scripts/run_r3.py"),
    "R4 · Ruta óptima": (paths.R4, "scripts/run_r4.py"),
}


# --------------------------------------------------------------------------- #
# Carga (una vez por sesión, R5-B10)
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner="Cargando la red procesada de R1…")
def load_network() -> ProcessedNetwork:
    return load_processed_network()


@st.cache_resource
def load_matrix() -> tuple[list[str], list[list[float]]] | None:
    return load_travel_time_matrix(MATRIX_CSV) if MATRIX_CSV.exists() else None


def missing(file_name: str, script: str) -> None:
    """Aviso de archivo faltante con el script que lo genera (R5-B06)."""
    st.info(f"Pendiente: falta `{file_name}`. Se genera con `python {script}`.")


def minutes(seconds: float) -> str:
    return f"{seconds / SECONDS_PER_MINUTE:,.1f} min"


def hours(seconds: float) -> str:
    return f"{seconds / SECONDS_PER_HOUR:,.2f} h"


# --------------------------------------------------------------------------- #
# Mapas
# --------------------------------------------------------------------------- #
def base_map(center: tuple[float, float] = QUINDIO_CENTER, zoom: int = DEPARTMENT_ZOOM):
    return folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")


def add_place_marker(fmap, place: Place, color: str, label: str | None = None) -> None:
    folium.CircleMarker(
        location=(place.lat, place.lon), radius=6, color=color, fill=True,
        fill_opacity=0.9, tooltip=label or place.name,
    ).add_to(fmap)


def show_map(fmap, key: str, points: Sequence[tuple[float, float]] = ()) -> None:
    if points:
        lats, lons = [lat for lat, _ in points], [lon for _, lon in points]
        fmap.fit_bounds([(min(lats), min(lons)), (max(lats), max(lons))])
    st_folium(fmap, key=key, height=MAP_HEIGHT_PX, use_container_width=True,
              returned_objects=[])


# --------------------------------------------------------------------------- #
# Pestaña 1: ruta origen-destino (R5-B01, R5-B07)
# --------------------------------------------------------------------------- #
def route_tab(network: ProcessedNetwork, places: dict[str, Place]) -> None:
    st.subheader("Ruta más rápida entre dos lugares")
    st.caption("Dijkstra con cola de prioridad, calculado en el momento (R5-B01).")
    ids = list(places)
    left, right = st.columns(2)
    origin = left.selectbox("Origen", ids, index=ids.index(DEFAULT_START_ID),
                            format_func=lambda i: places[i].name, key="route_origin")
    destination = right.selectbox("Destino", ids, index=ids.index("salento"),
                                  format_func=lambda i: places[i].name, key="route_dest")
    if st.button("Calcular ruta", type="primary", disabled=origin == destination):
        source, target = network.place_node[origin], network.place_node[destination]
        st.session_state["route"] = (origin, destination,
                                     dijkstra_heap(network.graph, source, target))
    if origin == destination:
        st.warning("El origen y el destino deben ser distintos.")

    if "route" not in st.session_state:
        return
    origin, destination, result = st.session_state["route"]
    a, b, c = st.columns(3)
    a.metric("Tiempo de viaje", minutes(result.cost))
    b.metric("Nodos explorados", f"{result.explored:,}")
    c.metric("Nodos en la ruta", f"{len(result.path):,}")
    matrix = load_matrix()
    if matrix is not None:
        matrix_ids, values = matrix
        cell = values[matrix_ids.index(origin)][matrix_ids.index(destination)]
        st.caption(f"En `matriz_tiempos.csv` (R2): {minutes(cell)} (R5-C01).")

    points = route_latlons(network.nx_graph, network.graph, result.path)
    fmap = base_map()
    folium.PolyLine(points, color=ROUTE_COLOR, weight=5, opacity=0.85).add_to(fmap)
    add_place_marker(fmap, places[origin], "#2f9e44", f"Origen: {places[origin].name}")
    add_place_marker(fmap, places[destination], "#c92a2a",
                     f"Destino: {places[destination].name}")
    show_map(fmap, "route_map", points)


# --------------------------------------------------------------------------- #
# Pestaña 2: envolvente convexa (R5-B02, R5-B08)
# --------------------------------------------------------------------------- #
def hull_tab(places: dict[str, Place]) -> None:
    st.subheader("Envolvente convexa de la red vial")
    try:
        vertices = hull_latlons(HULL_JSON)
    except ValueError as error:
        st.warning(str(error))
        return
    if vertices is None:
        missing("results/r3/envolvente_red.json", "scripts/run_r3.py")
    fmap = base_map()
    if vertices is not None:
        st.caption(f"{len(vertices)} vértices (QuickHull, R3), convertidos de UTM 18N.")
        folium.Polygon(vertices, color=HULL_COLOR, weight=3, fill=True,
                       fill_opacity=0.08, tooltip="Envolvente convexa").add_to(fmap)
    for place in places.values():
        add_place_marker(fmap, place, CATEGORY_COLORS[place.category][0],
                         f"{place.name} ({place.category})")
    st.caption("Lugares: " + " · ".join(f":{name}[●] {category}"
                                        for category, (_, name) in CATEGORY_COLORS.items()))
    show_map(fmap, "hull_map", vertices or [(p.lat, p.lon) for p in places.values()])


# --------------------------------------------------------------------------- #
# Pestaña 3: itinerario (R5-B03)
# --------------------------------------------------------------------------- #
def itinerary_tab(network: ProcessedNetwork, places: dict[str, Place]) -> None:
    st.subheader("Itinerario de un día")
    matrix = load_matrix()
    if matrix is None:
        missing("results/r2/matriz_tiempos.csv", "scripts/run_r2.py")
        return
    matrix_ids, values = matrix
    ids = list(places)
    start = st.selectbox("Lugar de partida", ids, index=ids.index(DEFAULT_START_ID),
                         format_func=lambda i: places[i].name, key="itinerary_start")
    options = [i for i in ids if places[i].category == "atractivo" and i != start]
    if "itinerary_places" in st.session_state:  # Si cambia la partida, quitarla de la selección.
        st.session_state["itinerary_places"] = [
            i for i in st.session_state["itinerary_places"] if i in options
        ]
    chosen = st.multiselect(
        f"Atractivos (entre {MIN_ATTRACTIONS} y {MAX_ATTRACTIONS})", options,
        format_func=lambda i: f"{places[i].name} ({places[i].visit_min:.0f} min)",
        max_selections=MAX_ATTRACTIONS, key="itinerary_places",
    )
    valid = MIN_ATTRACTIONS <= len(chosen) <= MAX_ATTRACTIONS
    if not valid:
        st.warning(f"Elija entre {MIN_ATTRACTIONS} y {MAX_ATTRACTIONS} atractivos "
                   f"(lleva {len(chosen)}).")
    if st.button("Calcular itinerario", type="primary", disabled=not valid):
        selection = [start, *chosen]
        costs = instance_matrix(values, matrix_ids.index(start),
                                [matrix_ids.index(i) for i in chosen])
        visit = [0.0] + [places[i].visit_min for i in chosen]
        labels = [places[i].name for i in selection]
        st.session_state["itinerary"] = (
            selection, compare_tours(costs, visit), plan_day(costs, labels, visit)
        )

    if "itinerary" not in st.session_state:
        return
    selection, comparison, plan = st.session_state["itinerary"]
    show_comparison(comparison, selection, places)
    show_tours_map(network, comparison, selection, places)
    show_day_plan(plan)


def show_comparison(
    comparison: TourComparison, selection: Sequence[str], places: dict[str, Place]
) -> None:
    st.markdown("**Held-Karp frente al vecino más cercano** (mismos atractivos, sin quitar "
                "ninguno)")
    rows = []
    for tour in (comparison.optimal, comparison.heuristic):
        order = " → ".join(places[selection[i]].name for i in tour.order)
        rows.append({"Método": tour.method, "Desplazamientos": minutes(tour.travel_s),
                     "Visitas": minutes(tour.visit_s), "Total con visitas": hours(tour.total_s),
                     "Orden": order})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    a, b = st.columns(2)
    a.metric("Diferencia (vecino − Held-Karp)", minutes(comparison.difference_s))
    b.metric("Diferencia en %", f"{comparison.gap_pct:.1f} %",
             help="Sobre los desplazamientos, como R4-B14")


def show_tours_map(
    network: ProcessedNetwork, comparison: TourComparison,
    selection: Sequence[str], places: dict[str, Place],
) -> None:
    fmap = base_map()
    all_points: list[tuple[float, float]] = []
    for tour, color in ((comparison.heuristic, HEURISTIC_COLOR),
                        (comparison.optimal, OPTIMAL_COLOR)):
        nodes = [network.place_node[selection[i]] for i in tour.order]
        layer = folium.FeatureGroup(name=tour.method)
        for leg in tour_legs(network.graph, nodes):
            points = route_latlons(network.nx_graph, network.graph, leg)
            all_points += points
            folium.PolyLine(points, color=color, weight=5, opacity=0.75,
                            tooltip=tour.method).add_to(layer)
        layer.add_to(fmap)
    for position, place_id in enumerate(selection):
        label = "Partida" if position == 0 else "Atractivo"
        add_place_marker(fmap, places[place_id], "#212529",
                         f"{label}: {places[place_id].name}")
    folium.LayerControl(collapsed=False).add_to(fmap)
    st.caption(":blue[●] Held-Karp · :orange[●] vecino más cercano")
    show_map(fmap, "tours_map", all_points)


def show_day_plan(plan: DayPlan) -> None:
    st.markdown("**Plan del día con Held-Karp** (formato del anexo)")
    # Columnas de texto: "Orden" mezcla números con "Regreso" y "Visita" usa "—" (anexo).
    rows = [{
        "Orden": str(row.position),
        "Lugar": row.place,
        "Desplazamiento desde el anterior (min)": round(row.travel_min, 1),
        "Visita (min)": "—" if row.visit_min is None else f"{row.visit_min:.0f}",
        "Tiempo acumulado (h)": round(row.cumulative_h, 2),
    } for row in plan.rows]
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    a, b, c = st.columns(3)
    a.metric("Total de visitas", hours(plan.visit_total_s))
    b.metric("Total de desplazamientos", hours(plan.travel_total_s))
    c.metric("Jornada", hours(plan.total_s))
    if plan.removed:
        st.warning("No cabía en 11 h; se quitaron, en este orden:")
        st.dataframe(pd.DataFrame([{
            "Atractivo quitado": removal.place,
            "Ahorro (min)": round(removal.saving_s / SECONDS_PER_MINUTE, 1),
            "Jornada antes de quitarlo (h)": round(removal.day_before_s / SECONDS_PER_HOUR, 2),
        } for removal in plan.removed]), hide_index=True)
    elif plan.fits(WORKDAY_S):
        st.success("La jornada cabe en 11 h sin quitar atractivos.")


# --------------------------------------------------------------------------- #
# Pestaña 4: resultados (R5-B04, R5-B09)
# --------------------------------------------------------------------------- #
def results_tab() -> None:
    st.subheader("Resultados de R1 a R4")
    st.caption("Tablas y gráficas leídas de `results/` (las genera cada script).")
    for title, (folder, script) in RESULT_SOURCES.items():
        with st.expander(title, expanded=False):
            tables, images = result_files(folder, ".csv"), result_files(folder, ".png")
            if not tables and not images:
                missing(f"{folder.relative_to(paths.ROOT)}/*.csv", script)
            for table in tables:
                st.markdown(f"`{table.name}`")
                st.dataframe(pd.read_csv(table), hide_index=True)
            for image in images:
                st.image(str(image), caption=image.name)


def main() -> None:
    st.set_page_config(page_title="Rutas del Paisaje Cultural Cafetero", layout="wide")
    st.title("Rutas del Paisaje Cultural Cafetero")
    if not paths.NETWORK_GRAPHML.exists():
        st.error("Falta la red procesada de R1 (`data/processed/`). Ejecute primero:")
        st.code("python scripts/build_network.py")
        st.stop()
    network = load_network()
    places = {place.id: place for place in network.places}
    route, hull, itinerary, results = st.tabs(
        ["Ruta origen-destino", "Envolvente convexa", "Itinerario", "Resultados"]
    )
    with route:
        route_tab(network, places)
    with hull:
        hull_tab(places)
    with itinerary:
        itinerary_tab(network, places)
    with results:
        results_tab()


main()
