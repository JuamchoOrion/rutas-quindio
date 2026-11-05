"""R5 — Aplicación demostrativa: rutas, envolvente, itinerario y resultados de R1–R4.

Spec: specs/R5-aplicacion.md

Uso (desde la raíz del repositorio):

    pip install -e ".[red,app]"
    streamlit run app/app.py

Solo lee archivos (data/processed/ y results/); nunca descarga la red (R5-B05).
La lógica sin interfaz está en ``rutas.app_support``; el tema visual, en
``.streamlit/config.toml``.
"""

from __future__ import annotations

import json
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
from rutas.itinerary import MAX_ATTRACTIONS, MIN_ATTRACTIONS, DayPlan, plan_day
from rutas.shortest_paths import dijkstra_heap
from rutas.tsp import instance_matrix

MATRIX_CSV = paths.R2 / "matriz_tiempos.csv"
HULL_JSON = paths.R3 / "envolvente_red.json"
DEFAULT_DESTINATION_ID = "salento"
SECONDS_PER_MINUTE = 60.0
MINUTES_PER_HOUR = 60

# Mapa: centrado en el Quindío y sin poder alejarse hasta ver el mundo repetido.
QUINDIO_CENTER = (4.45, -75.68)
DEPARTMENT_ZOOM = 10
MIN_ZOOM = 8
MAP_BOUNDS = {"min_lat": 3.6, "max_lat": 5.3, "min_lon": -76.6, "max_lon": -74.8}
# Mapa base gris claro de Esri (no pide clave; CARTO muestra "API KEY REQUIRED") con una
# capa de nombres encima, y OpenStreetMap como alternativa en el control de capas.
ESRI_CANVAS = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/{}/MapServer/tile/"
LIGHT_TILES_URL = ESRI_CANVAS.format("World_Light_Gray_Base") + "{z}/{y}/{x}"
LABELS_TILES_URL = ESRI_CANVAS.format("World_Light_Gray_Reference") + "{z}/{y}/{x}"
ESRI_ATTR = "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ"
MAP_HEIGHT_PX = 560

# Paleta validada con el validador de daltonismo y contraste (skill dataviz):
# categorías y recorridos pasan las seis comprobaciones sobre el fondo claro del mapa.
INK = "#2b2420"
OPTIMAL_COLOR = "#008b7d"        # Held-Karp y ruta origen-destino (verde cafetal)
HEURISTIC_COLOR = "#c75a2a"      # Vecino más cercano (terracota), además punteado
HULL_COLOR = "#3560b0"
CATEGORY_COLORS = {
    "cabecera": "#3560b0",
    "atractivo": "#c75a2a",
    "finca_hotel": "#008b7d",
    "acopio": "#b8880c",
}
CATEGORY_LABELS = {
    "cabecera": "Cabecera municipal",
    "atractivo": "Atractivo turístico",
    "finca_hotel": "Finca u hotel rural",
    "acopio": "Centro de acopio",
}

SECTIONS = ["Ruta", "Envolvente", "Itinerario", "Resultados"]
# Requerimiento → (carpeta, título, script que la genera; aviso de R5-B06).
RESULT_SOURCES = {
    "R1": (paths.R1, "Modelo de la red", "scripts/build_network.py"),
    "R2": (paths.R2, "Caminos mínimos", "scripts/run_r2.py"),
    "R3": (paths.R3, "Envolvente convexa", "scripts/run_r3.py"),
    "R4": (paths.R4, "Ruta óptima", "scripts/run_r4.py"),
}
# Nombre legible de los archivos conocidos; los demás se muestran con su nombre.
RESULT_TITLES = {
    "red_tamanos.csv": "Tamaño de la red antes y después de la CFC",
    "memoria.csv": "Memoria: matriz frente a listas de adyacencia",
    "velocidades_origen.csv": "Origen de la velocidad de cada tramo",
    "scc_tiempos.csv": "Tiempo de la componente fuertemente conexa (ms)",
    "lugares_lejanos.csv": "Lugares a más de 500 m de la red",
    "dijkstra_mediciones.csv": "Mediciones de Dijkstra (ms)",
    "dijkstra_cociente.csv": "Cociente lineal / cola de prioridad por par",
    "dijkstra_cociente_resumen.csv": "Cociente lineal / cola de prioridad: resumen",
    "matriz_tiempos.csv": "Matriz de tiempos entre lugares (s)",
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


@st.cache_data
def load_summary() -> dict:
    path = paths.NETWORK_SUMMARY_JSON
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


# --------------------------------------------------------------------------- #
# Formato
# --------------------------------------------------------------------------- #
def number(value: float, decimals: int = 0) -> str:
    """Número con formato en español: 1.234,5."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "\0").replace(".", ",").replace("\0", ".")


def duration(seconds: float) -> str:
    """Duración legible: «34 min» o «1 h 05 min»."""
    total_min = round(seconds / SECONDS_PER_MINUTE)
    hours, mins = divmod(total_min, MINUTES_PER_HOUR)
    return f"{hours} h {mins:02d} min" if hours else f"{mins} min"


def missing(file_name: str, script: str) -> None:
    """Aviso de archivo faltante con el script que lo genera (R5-B06)."""
    st.info(f"Todavía no existe `{file_name}`. Se genera con `python {script}`.")


DOT, LINE, DASHED = "punto", "línea", "punteada"   # Símbolos de la leyenda.


def legend(items: Sequence[tuple[str, str, str]]) -> None:
    """Leyenda con los mismos colores y trazos del mapa (punto, línea o punteada)."""
    parts = []
    for label, color, symbol in items:
        style = {
            DOT: f"background:{color};width:12px;height:12px;border-radius:50%",
            LINE: f"border-top:3px solid {color};width:22px",
            DASHED: f"border-top:3px dashed {color};width:22px",
        }[symbol]
        parts.append(f'<span style="display:inline-flex;align-items:center;gap:6px;'
                     f'margin-right:18px"><span style="display:inline-block;{style}"></span>'
                     f"{label}</span>")
    st.markdown(f'<div style="font-size:0.9rem">{"".join(parts)}</div>',
                unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Mapas
# --------------------------------------------------------------------------- #
def base_map() -> folium.Map:
    fmap = folium.Map(location=QUINDIO_CENTER, zoom_start=DEPARTMENT_ZOOM, tiles=None,
                      min_zoom=MIN_ZOOM, max_bounds=True, control_scale=True, **MAP_BOUNDS)
    folium.TileLayer(LIGHT_TILES_URL, attr=ESRI_ATTR, name="Mapa claro",
                     max_zoom=16).add_to(fmap)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", show=False).add_to(fmap)
    folium.TileLayer(LABELS_TILES_URL, attr=ESRI_ATTR, name="Nombres", overlay=True,
                     control=False, max_zoom=16).add_to(fmap)
    return fmap


def place_dot(fmap, place: Place, color: str, tooltip: str, radius: int = 7) -> None:
    folium.CircleMarker(
        location=(place.lat, place.lon), radius=radius, color="#ffffff", weight=2,
        fill=True, fill_color=color, fill_opacity=1.0, tooltip=tooltip,
    ).add_to(fmap)


def numbered_marker(fmap, place: Place, label: str, tooltip: str) -> None:
    html = (f'<div style="background:{INK};color:#fff;border:2px solid #fff;'
            f"border-radius:50%;width:24px;height:24px;line-height:20px;text-align:center;"
            f'font:600 12px sans-serif;box-shadow:0 1px 3px rgba(0,0,0,.35)">{label}</div>')
    folium.Marker((place.lat, place.lon), tooltip=tooltip,
                  icon=folium.DivIcon(html=html, icon_size=(24, 24),
                                      icon_anchor=(12, 12))).add_to(fmap)


def show_map(fmap, key: str, points: Sequence[tuple[float, float]] = ()) -> None:
    if points:
        lats, lons = [lat for lat, _ in points], [lon for _, lon in points]
        fmap.fit_bounds([(min(lats), min(lons)), (max(lats), max(lons))], padding=(30, 30))
    folium.LayerControl(collapsed=True).add_to(fmap)
    st_folium(fmap, key=key, height=MAP_HEIGHT_PX, use_container_width=True,
              returned_objects=[])


# --------------------------------------------------------------------------- #
# Pestaña Ruta (R5-B01, R5-B07)
# --------------------------------------------------------------------------- #
def route_section(network: ProcessedNetwork, places: dict[str, Place]) -> None:
    ids = list(places)
    controls, view = st.columns([1, 2.4], gap="large")
    with controls:
        st.markdown("#### Ruta más rápida")
        st.caption("Dijkstra con cola de prioridad, calculado en el momento.")
        origin = st.selectbox("Origen", ids, index=ids.index(DEFAULT_START_ID),
                              format_func=lambda i: places[i].name, key="route_origin")
        destination = st.selectbox("Destino", ids, index=ids.index(DEFAULT_DESTINATION_ID),
                                   format_func=lambda i: places[i].name, key="route_dest")
        same = origin == destination
        if st.button("Calcular ruta", type="primary", disabled=same, width="stretch"):
            result = dijkstra_heap(network.graph, network.place_node[origin],
                                   network.place_node[destination])
            st.session_state["route"] = ((origin, destination), result)
        if same:
            st.warning("Elija un destino distinto del origen.")

        # Solo se muestra el resultado de la selección actual, no el de una anterior.
        stored = st.session_state.get("route")
        result = stored[1] if stored and stored[0] == (origin, destination) else None
        if result is not None:
            st.metric("Tiempo de viaje", duration(result.cost), border=True)
            st.metric("Nodos explorados", number(result.explored), border=True)
            matrix = load_matrix()
            if matrix is not None:
                matrix_ids, values = matrix
                cell = values[matrix_ids.index(origin)][matrix_ids.index(destination)]
                st.caption(f"Matriz de R2: {number(cell / SECONDS_PER_MINUTE, 1)} min · "
                           f"ruta de {number(len(result.path))} nodos.")
        elif not same:
            st.caption("Pulse «Calcular ruta» para ver el recorrido.")

    with view:
        fmap = base_map()
        points: list[tuple[float, float]] = []
        if result is not None:
            points = route_latlons(network.nx_graph, network.graph, result.path)
            folium.PolyLine(points, color=OPTIMAL_COLOR, weight=6, opacity=0.9).add_to(fmap)
        numbered_marker(fmap, places[origin], "A", f"Origen: {places[origin].name}")
        numbered_marker(fmap, places[destination], "B", f"Destino: {places[destination].name}")
        ends = [(places[i].lat, places[i].lon) for i in (origin, destination)]
        show_map(fmap, "route_map", points or ends)


# --------------------------------------------------------------------------- #
# Pestaña Envolvente (R5-B02, R5-B08)
# --------------------------------------------------------------------------- #
def hull_section(places: dict[str, Place]) -> None:
    st.markdown("#### Envolvente convexa de la red vial")
    try:
        vertices = hull_latlons(HULL_JSON)
    except ValueError as error:
        st.warning(str(error))
        vertices = None
    if vertices is None and not HULL_JSON.exists():
        missing("results/r3/envolvente_red.json", "scripts/run_r3.py")
    elif vertices is not None:
        st.caption(f"Polígono de {len(vertices)} vértices calculado con QuickHull (R3) sobre "
                   "los nodos de la componente fuertemente conexa.")

    fmap = base_map()
    if vertices is not None:
        folium.Polygon(vertices, color=HULL_COLOR, weight=3, fill=True, fill_color=HULL_COLOR,
                       fill_opacity=0.06, tooltip="Envolvente convexa").add_to(fmap)
    for place in places.values():
        place_dot(fmap, place, CATEGORY_COLORS[place.category],
                  f"{place.name} · {CATEGORY_LABELS[place.category]}")
    legend([(CATEGORY_LABELS[c], color, DOT) for c, color in CATEGORY_COLORS.items()]
           + ([("Envolvente", HULL_COLOR, LINE)] if vertices is not None else []))
    show_map(fmap, "hull_map", vertices or [(p.lat, p.lon) for p in places.values()])


# --------------------------------------------------------------------------- #
# Pestaña Itinerario (R5-B03)
# --------------------------------------------------------------------------- #
def itinerary_section(network: ProcessedNetwork, places: dict[str, Place]) -> None:
    st.markdown("#### Itinerario de un día")
    matrix = load_matrix()
    if matrix is None:
        missing("results/r2/matriz_tiempos.csv", "scripts/run_r2.py")
        return
    matrix_ids, values = matrix
    ids = list(places)

    start_col, places_col, button_col = st.columns([1.2, 3, 0.9], vertical_alignment="bottom")
    start = start_col.selectbox("Lugar de partida", ids, index=ids.index(DEFAULT_START_ID),
                                format_func=lambda i: places[i].name, key="itinerary_start")
    options = [i for i in ids if places[i].category == "atractivo" and i != start]
    if "itinerary_places" in st.session_state:  # Si cambia la partida, quitarla de la selección.
        st.session_state["itinerary_places"] = [
            i for i in st.session_state["itinerary_places"] if i in options
        ]
    chosen = places_col.multiselect(
        f"Atractivos (entre {MIN_ATTRACTIONS} y {MAX_ATTRACTIONS})", options,
        format_func=lambda i: f"{places[i].name} · {places[i].visit_min:.0f} min",
        max_selections=MAX_ATTRACTIONS, key="itinerary_places",
        placeholder="Elija los atractivos del día",
    )
    valid = MIN_ATTRACTIONS <= len(chosen) <= MAX_ATTRACTIONS
    if button_col.button("Calcular", type="primary", disabled=not valid, width="stretch"):
        selection = [start, *chosen]
        costs = instance_matrix(values, matrix_ids.index(start),
                                [matrix_ids.index(i) for i in chosen])
        visit = [0.0] + [places[i].visit_min for i in chosen]
        labels = [places[i].name for i in selection]
        st.session_state["itinerary"] = (
            tuple(selection), compare_tours(costs, visit), plan_day(costs, labels, visit)
        )
    if not valid:
        st.caption(f"Elija entre {MIN_ATTRACTIONS} y {MAX_ATTRACTIONS} atractivos para "
                   f"calcular (lleva {len(chosen)}).")

    # Solo se muestra el resultado de la selección actual, no el de una anterior.
    stored = st.session_state.get("itinerary")
    if not stored or stored[0] != (start, *chosen):
        if valid:
            st.caption("Pulse «Calcular» para comparar los recorridos.")
        return
    selection, comparison, plan = stored
    show_comparison(comparison, selection, places)
    show_tours_map(network, comparison, selection, places)
    show_day_plan(plan)


def stat_grid(items: Sequence[tuple[str, str]]) -> None:
    """Cifras en una cuadrícula compacta (st.metric corta los valores en tarjetas angostas)."""
    cells = "".join(
        f'<div><div style="font-size:0.8rem;opacity:0.75">{label}</div>'
        f'<div style="font-size:1.35rem;font-weight:600;white-space:nowrap">{value}</div></div>'
        for label, value in items
    )
    st.markdown(f'<div style="display:grid;grid-template-columns:repeat({len(items)},1fr);'
                f'gap:12px;margin:4px 0 10px">{cells}</div>', unsafe_allow_html=True)


def tour_card(column, tour, selection: Sequence[str], places: dict[str, Place],
              color: str, dashed: bool) -> None:
    with column.container(border=True):
        line = "dashed" if dashed else "solid"
        st.markdown(f'<div style="display:flex;align-items:center;gap:10px;font-weight:600">'
                    f'<span style="border-top:4px {line} {color};width:32px"></span>'
                    f"{tour.method}</div>", unsafe_allow_html=True)
        stat_grid([("Desplazamientos", duration(tour.travel_s)),
                   ("Visitas", duration(tour.visit_s)),
                   ("Total del día", duration(tour.total_s))])
        st.caption(" → ".join(places[selection[i]].name for i in tour.order))


def show_comparison(comparison: TourComparison, selection: Sequence[str],
                    places: dict[str, Place]) -> None:
    st.markdown("##### Held-Karp frente al vecino más cercano")
    st.caption("Los dos visitan los mismos atractivos elegidos, sin quitar ninguno.")
    left, right, delta = st.columns([2, 2, 1])
    tour_card(left, comparison.optimal, selection, places, OPTIMAL_COLOR, False)
    tour_card(right, comparison.heuristic, selection, places, HEURISTIC_COLOR, True)
    with delta.container(border=True):
        st.markdown('<div style="font-weight:600">Vecino − Held-Karp</div>',
                    unsafe_allow_html=True)
        stat_grid([("Diferencia", duration(comparison.difference_s))])
        stat_grid([("En %", f"{number(comparison.gap_pct, 1)} %")])
        st.caption("Sobre los desplazamientos, como R4-B14.")


def show_tours_map(network: ProcessedNetwork, comparison: TourComparison,
                   selection: Sequence[str], places: dict[str, Place]) -> None:
    fmap = base_map()
    all_points: list[tuple[float, float]] = []
    styles = ((comparison.optimal, OPTIMAL_COLOR, 7, None),
              (comparison.heuristic, HEURISTIC_COLOR, 4, "10 8"))
    for tour, color, weight, dash in styles:
        nodes = [network.place_node[selection[i]] for i in tour.order]
        layer = folium.FeatureGroup(name=tour.method)
        for leg in tour_legs(network.graph, nodes):
            points = route_latlons(network.nx_graph, network.graph, leg)
            all_points += points
            folium.PolyLine(points, color=color, weight=weight, opacity=0.9,
                            dash_array=dash, tooltip=tour.method).add_to(layer)
        layer.add_to(fmap)
    visit_number = {place: n for n, place in enumerate(comparison.optimal.order[1:-1], 1)}
    for index, place_id in enumerate(selection):
        place = places[place_id]
        label = "P" if index == 0 else str(visit_number[index])
        role = "Partida" if index == 0 else f"Parada {label} con Held-Karp"
        numbered_marker(fmap, place, label, f"{role}: {place.name}")
    legend([("Held-Karp (óptimo)", OPTIMAL_COLOR, LINE),
            ("Vecino más cercano", HEURISTIC_COLOR, DASHED)])
    show_map(fmap, "tours_map", all_points)


def show_day_plan(plan: DayPlan) -> None:
    st.markdown("##### Plan del día con Held-Karp")
    if plan.removed:
        removed = ", ".join(removal.place for removal in plan.removed)
        st.warning(f"La jornada no cabía en 11 h. Se quitaron, en este orden: {removed}.")
    else:
        st.success("La jornada cabe en 11 h sin quitar atractivos.")
    a, b, c = st.columns(3)
    a.metric("Total de visitas", duration(plan.visit_total_s), border=True)
    b.metric("Total de desplazamientos", duration(plan.travel_total_s), border=True)
    c.metric("Duración de la jornada", duration(plan.total_s), border=True)

    # Formato del anexo; "Orden" y "Visita" son texto porque usan "Regreso" y "—".
    rows = [{
        "Orden": str(row.position),
        "Lugar": row.place,
        "Desplazamiento desde el anterior (min)": round(row.travel_min, 1),
        "Visita (min)": "—" if row.visit_min is None else f"{row.visit_min:.0f}",
        "Tiempo acumulado (h)": round(row.cumulative_h, 2),
    } for row in plan.rows]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    if plan.removed:
        st.caption("Atractivos quitados y su justificación (R4-B17):")
        st.dataframe(pd.DataFrame([{
            "Atractivo quitado": removal.place,
            "Ahorro (min)": round(removal.saving_s / SECONDS_PER_MINUTE, 1),
            "Jornada antes de quitarlo": duration(removal.day_before_s),
        } for removal in plan.removed]), hide_index=True, width="stretch")


# --------------------------------------------------------------------------- #
# Pestaña Resultados (R5-B04, R5-B09)
# --------------------------------------------------------------------------- #
def results_section() -> None:
    st.markdown("#### Resultados de R1 a R4")
    st.caption("Tablas y gráficas leídas de `results/`, tal como las generó cada script.")
    for tab, (folder, title, script) in zip(st.tabs(list(RESULT_SOURCES)),
                                            RESULT_SOURCES.values()):
        with tab:
            st.markdown(f"**{title}**")
            tables, images = result_files(folder, ".csv"), result_files(folder, ".png")
            if not tables and not images:
                missing(f"{folder.relative_to(paths.ROOT)}/*.csv", script)
            for image in images:
                st.image(str(image), caption=image.name)
            for table in tables:
                st.markdown(f"{RESULT_TITLES.get(table.name, table.stem)} · `{table.name}`")
                st.dataframe(pd.read_csv(table), hide_index=True, width="stretch")


TOP_PADDING_CSS = ('<style>[data-testid="stMainBlockContainer"]'
                   "{padding-top:2.5rem}</style>")


def header() -> None:
    st.markdown(TOP_PADDING_CSS, unsafe_allow_html=True)
    st.title("Rutas del Paisaje Cultural Cafetero")
    summary = load_summary()
    sizes = {row["red"]: row for row in summary.get("tamanos", [])}
    component = sizes.get("Componente fuertemente conexa")
    if component:
        downloaded = summary.get("fecha_descarga", "")[:10]
        st.caption(f"Red vial del Quindío (OpenStreetMap, descargada el {downloaded}): "
                   f"{number(component['nodos'])} nodos y {number(component['aristas'])} "
                   "tramos en la componente fuertemente conexa.")


def main() -> None:
    st.set_page_config(page_title="Rutas del Paisaje Cultural Cafetero", layout="wide")
    if not paths.NETWORK_GRAPHML.exists():
        st.error("Falta la red procesada de R1 (`data/processed/`). Ejecute primero:")
        st.code("python scripts/build_network.py")
        st.stop()
    header()
    network = load_network()
    places = {place.id: place for place in network.places}

    # Solo se ejecuta la pestaña abierta: un mapa en una pestaña oculta se crea con
    # ancho 0 y Leaflet lo muestra como el mundo repetido. La pestaña queda en la URL.
    route, hull, itinerary, results = st.tabs(SECTIONS, key="seccion",
                                              on_change="rerun", bind="query-params")
    if route.open:
        with route:
            route_section(network, places)
    if hull.open:
        with hull:
            hull_section(places)
    if itinerary.open:
        with itinerary:
            itinerary_section(network, places)
    if results.open:
        with results:
            results_section()


main()
