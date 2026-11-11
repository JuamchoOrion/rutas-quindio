"""Gráficas y tablas del documento técnico, generadas solo desde ``results/`` (PE-B08).

Spec: specs/protocolo-experimental.md (PE-B08 a PE-B10), specs/R1-modelo-red.md (R1-B25),
specs/R2-caminos-minimos.md (R2-B14), specs/R3-envolvente-convexa.md y
specs/R4-ruta-optima.md (sección Experimentos).

Uso (desde la raíz del repositorio, después de ``build_network.py`` y los ``run_rX.py``):

    python scripts/make_figures.py

No recalcula ningún algoritmo: lee los CSV y JSON de ``results/`` (y, para los lugares
lejanos de R1 y el itinerario de R4, solo los nombres de ``data/catalogo.csv``). Si falta
el archivo de un requerimiento, avisa y sigue con los demás.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")                    # Sin ventanas (PE-B10).
import matplotlib.pyplot as plt          # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter  # noqa: E402

from rutas import paths                  # noqa: E402
from rutas.benchmark import LONG_RUN_S   # noqa: E402
from rutas.catalog import load_catalog   # noqa: E402
from rutas.report import (               # noqa: E402
    format_fixed,
    format_ms,
    format_significant,
    markdown_table,
    read_csv,
    read_json,
    write_markdown,
)

TABLES_DIR = paths.RESULTS / "tablas"

# Estilo de las gráficas (PE-B10).
FIGURE_SIZE_IN = (7.0, 4.5)
FIGURE_DPI = 200
LINE_WIDTH_PT = 1.5                      # ≈ 2 px en pantalla.
MARKER_SIZE_PT = 6
SERIES_STYLES = (                        # Orden fijo de la paleta validada.
    ("Fuerza bruta", "#2a78d6", "o"),
    ("Held-Karp", "#eb6834", "s"),
)
GRID_COLOR = "#d9d9d6"
TEXT_COLOR = "#52514e"
LABEL_OFFSET_PT = (6, 0)
X_MARGIN_RIGHT = 0.9                     # Espacio para la etiqueta del último punto.

LONG_RUN_MS = LONG_RUN_S * 1000          # Más largo → una sola ejecución (PE-B03).
WORKDAY_H = 11
MINUTES_PER_HOUR = 60.0

R3_SET_LABELS = {"red_vial": "Nodos de la red"}
SQUARE_PREFIX = "cuadrado_"
NOT_COMPLETED = "no completada"
NO_VISIT = "—"
PERCENT = 100
US_PER_MS = 1000
SPEED_ORIGIN_LABELS = {
    "maxspeed": "maxspeed de OSM",
    "highway_default": "Por defecto según el tipo de vía",
    "fallback": "Velocidad de respaldo",
}
DIJKSTRA_VERSIONS = (("cola_prioridad", "Cola de prioridad"), ("lineal", "Lineal"))


@dataclass(frozen=True)
class ExactPlot:
    """Lo que se dibujó en ``exactas_tiempo_vs_k.png`` (para las pruebas, PE-C10)."""

    png: Path
    series_k: dict[str, list[int]]
    legend_labels: list[str]


def shown_path(path: Path) -> Path:
    return path.relative_to(paths.ROOT) if path.is_relative_to(paths.ROOT) else path


def source_line(path: Path) -> str:
    return f"Fuente: `{shown_path(path)}`."


def missing(path: Path) -> bool:
    if path.is_file():
        return False
    print(f"   aviso: falta {path}; se omite")
    return True


def integer(value: str) -> str:
    """Cantidad entera con espacio de miles (PE-B09)."""
    return format_fixed(int(value), 0)


# --------------------------------------------------------------------------- #
# R1: tablas del modelo de la red (la spec de R1 no pide gráfica)
# --------------------------------------------------------------------------- #
def size_table(csv_path: Path) -> str:
    body = [[row["red"], integer(row["nodos"]), integer(row["aristas"])]
            for row in read_csv(csv_path)]
    return "\n\n".join(["### Tamaño de la red antes y después de la componente",
                        markdown_table(["Red", "Nodos", "Aristas"], body),
                        source_line(csv_path)])


def memory_table(csv_path: Path) -> str:
    rows = read_csv(csv_path)
    headers = ["Red", "V", "E", "Densidad E/V²", "Matriz (MB)", "Listas (MB)"]
    body = [[row["red"], integer(row["V"]), integer(row["E"]),
             format_significant(float(row["densidad"])),
             format_significant(float(row["matriz_mb"])),
             format_significant(float(row["listas_mb"]))] for row in rows]
    assumptions = sorted({row["supuestos"] for row in rows})
    return "\n\n".join(["### Memoria: matriz de adyacencia frente a listas de adyacencia",
                        markdown_table(headers, body),
                        f"Supuestos: {'; '.join(assumptions)}. MB = 10⁶ bytes. "
                        + source_line(csv_path)])


def speed_table(csv_path: Path) -> str:
    rows = read_csv(csv_path)
    total = sum(int(row["aristas"]) for row in rows)
    body = [[SPEED_ORIGIN_LABELS.get(row["origen"], row["origen"]), integer(row["aristas"]),
             format_fixed(PERCENT * int(row["aristas"]) / total, 1)] for row in rows]
    return "\n\n".join(["### Origen de la velocidad de cada tramo (R1-B08, R1-B09)",
                        markdown_table(["Origen", "Aristas", "Porcentaje (%)"], body),
                        source_line(csv_path)])


def scc_table(csv_path: Path) -> str:
    headers = ["Red", "V", "E", "V+E", "Tiempo (ms)", "Tiempo por elemento (µs)"]
    body = [[row["red"], integer(row["V"]), integer(row["E"]), integer(row["V_mas_E"]),
             format_ms(float(row["tiempo_ms"])),
             format_significant(US_PER_MS * float(row["tiempo_ms"]) / int(row["V_mas_E"]))]
            for row in read_csv(csv_path)]
    return "\n\n".join(["### Tiempo de obtener la componente fuertemente conexa",
                        markdown_table(headers, body),
                        "Tiempo por elemento = tiempo / (V + E). " + source_line(csv_path)])


def far_places_table(csv_path: Path, catalog_csv: Path) -> str:
    """Lugares a más de 500 m de su nodo (R1-B17), con el nombre del catálogo."""
    rows = read_csv(csv_path)
    title = "### Lugares a más de 500 m de la red (R1-B17)"
    if not rows:
        return "\n\n".join([title, "Lugares a más de 500 m: ninguno. " + source_line(csv_path)])
    names = {place.id: place.name for place in load_catalog(catalog_csv)}
    body = [[names.get(row["id"], row["id"]), row["id"], row["nodo_osm"],
             format_fixed(float(row["distancia_m"]), 0)] for row in rows]
    return "\n\n".join([title,
                        markdown_table(["Lugar", "Id", "Nodo OSM", "Distancia (m)"], body),
                        source_line(csv_path)])


def figuras_r1(
    r1_dir: Path = paths.R1, tables_dir: Path = TABLES_DIR, catalog_csv: Path = paths.CATALOG_CSV
) -> None:
    """Tablas de R1 en ``results/tablas/r1.md`` (PE-B09, PE-C12)."""
    builders = (("red_tamanos.csv", size_table), ("memoria.csv", memory_table),
                ("velocidades_origen.csv", speed_table), ("scc_tiempos.csv", scc_table))
    sections = ["## Requerimiento 1: modelo de la red vial"]
    sections += [build(r1_dir / name) for name, build in builders
                 if not missing(r1_dir / name)]
    far_csv = r1_dir / "lugares_lejanos.csv"
    if not missing(far_csv):
        sections.append(far_places_table(far_csv, catalog_csv))
    write_markdown(tables_dir / "r1.md", "\n\n".join(sections))
    print(f"   {tables_dir.name}/r1.md")


# --------------------------------------------------------------------------- #
# R2: gráfica de Dijkstra y tablas
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ScatterPlot:
    """Lo que se dibujó en ``dijkstra_tiempo_vs_nodos.png`` (para las pruebas, PE-C11)."""

    png: Path
    series_points: dict[str, int]


def plot_dijkstra(rows: Sequence[dict[str, str]], png: Path) -> ScatterPlot:
    """Dispersión de tiempo frente a nodos explorados, ejes logarítmicos (PE-B10)."""
    fig, ax = plt.subplots(figsize=FIGURE_SIZE_IN)
    fig.patch.set_facecolor("white")
    counts: dict[str, int] = {}
    for (version, label), (_, color, marker) in zip(DIJKSTRA_VERSIONS, SERIES_STYLES):
        points = [row for row in rows if row["version"] == version]
        ax.plot([int(row["nodos_explorados"]) for row in points],
                [float(row["tiempo_ms"]) for row in points], linestyle="none",
                color=color, marker=marker, markersize=MARKER_SIZE_PT, label=label)
        counts[label] = len(points)
    ax.set_xscale("log")                 # Antes de los formatos: set_*scale los reinicia.
    ax.set_yscale("log")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_locator(LogLocator(base=10))
        axis.set_major_formatter(FuncFormatter(log_tick_label))
        axis.set_minor_formatter(NullFormatter())
    ax.grid(axis="y", which="major", color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_xlabel("Nodos explorados (escala logarítmica)")
    ax.set_ylabel("Tiempo (ms, escala logarítmica)")
    ax.set_title("Dijkstra: tiempo según nodos explorados")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(png, dpi=FIGURE_DPI, facecolor="white")
    plt.close(fig)
    return ScatterPlot(png, counts)


def measurements_table(rows: Sequence[dict[str, str]], csv_path: Path) -> str:
    headers = ["Origen", "Destino", "Versión", "Tiempo de viaje (s)", "Nodos explorados",
               "Tiempo (ms)", "Tipo de par"]
    body = [[row["origen"], row["destino"], row["version"],
             format_fixed(float(row["tiempo_viaje_s"]), 1), integer(row["nodos_explorados"]),
             format_ms(float(row["tiempo_ms"])), row["tipo_par"]] for row in rows]
    return "\n\n".join(["### Mediciones de Dijkstra", markdown_table(headers, body),
                        "Mediana de 5 ejecuciones. " + source_line(csv_path)])


def ratio_pairs_table(csv_path: Path) -> str:
    headers = ["Origen", "Destino", "Nodos explorados lineal", "Nodos explorados cola",
               "Tiempo lineal (ms)", "Tiempo cola (ms)", "Cociente"]
    body = [[row["origen"], row["destino"], integer(row["explorados_lineal"]),
             integer(row["explorados_cola"]), format_ms(float(row["tiempo_lineal_ms"])),
             format_ms(float(row["tiempo_cola_ms"])), format_fixed(float(row["cociente"]), 1)]
            for row in read_csv(csv_path)]
    return "\n\n".join(["### Cociente lineal / cola de prioridad por par",
                        markdown_table(headers, body), source_line(csv_path)])


def ratio_summary_table(csv_path: Path) -> str:
    row = read_csv(csv_path)[0]
    body = [[format_fixed(float(row[col]), 1) for col in ("mediana", "minimo", "maximo")]]
    return "\n\n".join([f"### Cociente entre versiones (en los {row['pares']} pares medidos "
                        "con ambas)", markdown_table(["Mediana", "Mínimo", "Máximo"], body),
                        source_line(csv_path)])


def matrix_summary(json_path: Path) -> str:
    summary = read_json(json_path)
    diff = summary["max_diferencia_s"]
    same_node = ", ".join(" y ".join(f"`{p}`" for p in group)
                          for group in summary["lugares_mismo_nodo"]) or "ninguno"
    lines = [
        f"- Lugares: {summary['n']} (matriz {summary['n']} × {summary['n']}).",
        f"- Tiempo de cálculo: {format_ms(summary['tiempo_ms'])} ms.",
        f"- Pares asimétricos: {summary['pares_asimetricos']} de {summary['pares_totales']}.",
        f"- Mayor diferencia entre ida y regreso: {format_fixed(diff['valor'], 1)} s "
        f"(`{diff['lugar_a']}` y `{diff['lugar_b']}`).",
        f"- Lugares en el mismo nodo: {same_node}.",
    ]
    return "\n\n".join(["### Matriz de tiempos", "\n".join(lines), source_line(json_path)])


def figuras_r2(r2_dir: Path = paths.R2, tables_dir: Path = TABLES_DIR) -> ScatterPlot | None:
    """Gráfica y tablas de R2 (R2-B14, PE-B09, PE-B10); devuelve lo dibujado (PE-C11)."""
    csv_path = r2_dir / "dijkstra_mediciones.csv"
    if missing(csv_path):
        return None
    rows = read_csv(csv_path)
    plot = plot_dijkstra(rows, r2_dir / "dijkstra_tiempo_vs_nodos.png")
    print(f"   {r2_dir.name}/{plot.png.name}")

    sections = ["## Requerimiento 2: caminos mínimos", measurements_table(rows, csv_path)]
    for name, build in (("dijkstra_cociente.csv", ratio_pairs_table),
                        ("dijkstra_cociente_resumen.csv", ratio_summary_table),
                        ("matriz_resumen.json", matrix_summary)):
        if not missing(r2_dir / name):
            sections.append(build(r2_dir / name))
    write_markdown(tables_dir / "r2.md", "\n\n".join(sections))
    print(f"   {tables_dir.name}/r2.md")
    return plot


# --------------------------------------------------------------------------- #
# R3: tabla de la envolvente (la spec de R3 no pide gráfica)
# --------------------------------------------------------------------------- #
def r3_set_label(name: str) -> str:
    """``red_vial`` → "Nodos de la red"; ``cuadrado_N`` → "Cuadrado, N puntos" (PE-B09)."""
    if name.startswith(SQUARE_PREFIX):
        return f"Cuadrado, {format_fixed(int(name[len(SQUARE_PREFIX):]), 0)} puntos"
    return R3_SET_LABELS.get(name, name)


def figuras_r3(r3_dir: Path = paths.R3, tables_dir: Path = TABLES_DIR) -> None:
    csv_path = r3_dir / "envolvente_tiempos.csv"
    if missing(csv_path):
        return
    headers = ["Conjunto de puntos", "n", "Vértices de la envolvente", "Tiempo propio (ms)",
               "Tiempo SciPy (ms)", "Cociente"]
    rows = [
        [r3_set_label(row["conjunto"]), format_fixed(int(row["n"]), 0), row["vertices"],
         format_ms(float(row["tiempo_propio_ms"])), format_ms(float(row["tiempo_scipy_ms"])),
         format_fixed(float(row["cociente"]), 1)]
        for row in read_csv(csv_path)
    ]
    text = "\n\n".join([
        "## Requerimiento 3: envolvente convexa",
        markdown_table(headers, rows),
        "Cociente = tiempo propio / tiempo SciPy (mediana de 5 ejecuciones). "
        + source_line(csv_path),
    ])
    write_markdown(tables_dir / "r3.md", text)
    print(f"   {tables_dir.name}/r3.md")


# --------------------------------------------------------------------------- #
# R4: gráfica de las exactas y tablas
# --------------------------------------------------------------------------- #
def is_true(value: str) -> bool:
    return value.strip().lower() == "true"


def exact_series(rows: Sequence[dict[str, str]]) -> list[tuple[str, list[int], list[float],
                                                                list[int]]]:
    """Por método: nombre, ``k`` completados, sus tiempos y ``k`` no completados."""
    columns = (("tiempo_fuerza_bruta_ms", "completado_fb"),
               ("tiempo_held_karp_ms", "completado_hk"))
    series = []
    for (name, _, _), (time_col, done_col) in zip(SERIES_STYLES, columns):
        done = [row for row in rows if is_true(row[done_col])]
        not_done = [int(row["k"]) for row in rows if not is_true(row[done_col])]
        series.append((name, [int(r["k"]) for r in done], [float(r[time_col]) for r in done],
                       not_done))
    return series


def log_tick_label(value: float, _position: int) -> str:
    return format_significant(value, 1)


def style_axes(ax, ks: Sequence[int]) -> None:
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_major_formatter(FuncFormatter(log_tick_label))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(list(ks))
    ax.set_xlim(min(ks) - 0.4, max(ks) + X_MARGIN_RIGHT)
    ax.grid(axis="y", which="major", color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_xlabel("k (lugares a visitar)")
    ax.set_ylabel("Tiempo (ms, escala logarítmica)")
    ax.set_title("Métodos exactos del ATSP: tiempo según k")


def plot_exact_times(rows: Sequence[dict[str, str]], png: Path) -> ExactPlot:
    """``exactas_tiempo_vs_k.png`` (spec R4, PE-B10); los ``k`` no completados no se
    dibujan y se indican en la leyenda."""
    fig, ax = plt.subplots(figsize=FIGURE_SIZE_IN)
    fig.patch.set_facecolor("white")
    series_k: dict[str, list[int]] = {}
    labels: list[str] = []
    for (name, ks, times, not_done), (_, color, marker) in zip(exact_series(rows),
                                                                SERIES_STYLES):
        label = name if not not_done else \
            f"{name} ({NOT_COMPLETED}: k = {', '.join(map(str, not_done))})"
        ax.plot(ks, times, color=color, marker=marker, linewidth=LINE_WIDTH_PT,
                markersize=MARKER_SIZE_PT, label=label)
        if ks:
            ax.annotate(f"{format_ms(times[-1])} ms", (ks[-1], times[-1]),
                        xytext=LABEL_OFFSET_PT, textcoords="offset points",
                        va="center", color=TEXT_COLOR, fontsize=8)
        series_k[name] = ks
        labels.append(label)
    style_axes(ax, [int(row["k"]) for row in rows])
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(png, dpi=FIGURE_DPI, facecolor="white")
    plt.close(fig)
    return ExactPlot(png, series_k, labels)


def exact_time_cell(completed: str, value: str) -> str:
    if not is_true(completed):
        return NOT_COMPLETED
    milliseconds = float(value)
    return format_ms(milliseconds) + ("*" if milliseconds > LONG_RUN_MS else "")


def largest_k(rows: Sequence[dict[str, str]], done_col: str) -> str:
    ks = [int(row["k"]) for row in rows if is_true(row[done_col])]
    return f"k = {max(ks)}" if ks else "ninguno"


def exact_table(rows: Sequence[dict[str, str]], csv_path: Path) -> str:
    headers = ["k", "Tiempo fuerza bruta (ms)", "Tiempo Held-Karp (ms)",
               "Memoria tabla Held-Karp (MB)"]
    body = [
        [row["k"], exact_time_cell(row["completado_fb"], row["tiempo_fuerza_bruta_ms"]),
         exact_time_cell(row["completado_hk"], row["tiempo_held_karp_ms"]),
         format_significant(float(row["memoria_tabla_hk_mb"]))]
        for row in rows
    ]
    notes = [f"Mayor k resuelto: fuerza bruta {largest_k(rows, 'completado_fb')}; "
             f"Held-Karp {largest_k(rows, 'completado_hk')}."]
    if any("*" in cell for line in body for cell in line):
        notes.insert(0, f"\\* Una sola ejecución: la primera pasó de {LONG_RUN_S:g} s (PE-B03). "
                        "Los demás tiempos son la mediana de 5 ejecuciones.")
    return "\n\n".join(["### Soluciones exactas", markdown_table(headers, body),
                        " ".join(notes) + " " + source_line(csv_path)])


def heuristic_table(csv_path: Path) -> str:
    headers = ["k", "Instancias", "Brecha promedio (%)", "Brecha máxima (%)"]
    body = [
        [row["k"], row["instancias"], format_fixed(float(row["brecha_promedio_pct"]), 1),
         format_fixed(float(row["brecha_maxima_pct"]), 1)]
        for row in read_csv(csv_path)
    ]
    return "\n\n".join(["### Calidad de la heurística (vecino más cercano)",
                        markdown_table(headers, body), source_line(csv_path)])


def minutes_and_hours(minutes: float) -> str:
    return f"{format_fixed(minutes, 1)} min ({format_fixed(minutes / MINUTES_PER_HOUR, 2)} h)"


def itinerary_table(csv_path: Path, summary_path: Path, catalog_csv: Path) -> str:
    rows = read_csv(csv_path)
    summary = read_json(summary_path)
    headers = ["Orden", "Lugar", "Desplazamiento desde el anterior (min)", "Visita (min)",
               "Tiempo acumulado (h)"]
    body = [
        [row["orden"], row["lugar"], format_fixed(float(row["desplazamiento_min"]), 1),
         format_fixed(float(row["visita_min"]), 0) if row["visita_min"] else NO_VISIT,
         format_fixed(float(row["acumulado_h"]), 2)]
        for row in rows
    ]
    day_min = summary["jornada_total_h"] * MINUTES_PER_HOUR
    totals = [
        f"- Tiempo total de visitas: {minutes_and_hours(summary['visitas_total_min'])}.",
        "- Tiempo total de desplazamientos: "
        f"{minutes_and_hours(summary['desplazamientos_total_min'])}.",
        f"- Duración total de la jornada: {minutes_and_hours(day_min)}; "
        f"{'cabe' if summary['cabe'] else 'no cabe'} en {WORKDAY_H} h.",
        removed_lines(summary["quitados"], catalog_csv),
    ]
    start = rows[-1]["lugar"] if rows else summary["partida"]
    return "\n\n".join([f"### Itinerario de un día (lugar de partida: {start})",
                        markdown_table(headers, body), "\n".join(totals),
                        f"Fuentes: `{shown_path(csv_path)}` y `{shown_path(summary_path)}`."])


def removed_lines(removed: Sequence[dict], catalog_csv: Path) -> str:
    """Atractivos quitados (R4-B17), con el nombre leído del catálogo (PE-B09)."""
    if not removed:
        return "- Atractivos quitados: ninguno."
    names = {place.id: place.name for place in load_catalog(catalog_csv)}
    lines = ["- Atractivos quitados (R4-B17), en el orden en que se quitaron:"]
    for item in removed:
        lines.append(
            f"  - {names.get(item['lugar'], item['lugar'])} (`{item['lugar']}`): ahorro "
            f"{format_fixed(item['ahorro_min'], 1)} min; jornada antes de quitarlo "
            f"{format_fixed(item['jornada_antes_h'], 2)} h."
        )
    return "\n".join(lines)


def figuras_r4(
    r4_dir: Path = paths.R4, tables_dir: Path = TABLES_DIR, catalog_csv: Path = paths.CATALOG_CSV
) -> ExactPlot | None:
    """Gráfica de las exactas y tablas de R4; devuelve lo dibujado (PE-C10)."""
    exact_csv = r4_dir / "exactas_tiempos.csv"
    if missing(exact_csv):
        return None
    rows = read_csv(exact_csv)
    plot = plot_exact_times(rows, r4_dir / "exactas_tiempo_vs_k.png")
    print(f"   {r4_dir.name}/{plot.png.name}")

    sections = ["## Requerimiento 4: ruta óptima", exact_table(rows, exact_csv)]
    heuristic_csv = r4_dir / "heuristica_resumen.csv"
    if not missing(heuristic_csv):
        sections.append(heuristic_table(heuristic_csv))
    itinerary_csv, summary_json = r4_dir / "itinerario.csv", r4_dir / "itinerario_resumen.json"
    if not missing(itinerary_csv) and not missing(summary_json):
        sections.append(itinerary_table(itinerary_csv, summary_json, catalog_csv))
    write_markdown(tables_dir / "r4.md", "\n\n".join(sections))
    print(f"   {tables_dir.name}/r4.md")
    return plot


def main() -> None:
    print("Generando gráficas y tablas desde results/…")
    figuras_r1()
    figuras_r2()
    figuras_r3()
    figuras_r4()
    print("   listo")


if __name__ == "__main__":
    main()
