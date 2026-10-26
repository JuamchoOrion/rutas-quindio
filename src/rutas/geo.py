"""Proyección a UTM 18N y búsqueda del nodo más cercano (R1, punto 4; R3).

Spec: specs/R1-modelo-red.md (R1-B15 a R1-B17).
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

import numpy as np
from pyproj import Transformer

WGS84 = "EPSG:4326"
UTM_18N = "EPSG:32618"
FAR_THRESHOLD_M = 500.0


@lru_cache(maxsize=2)
def _transformer(inverse: bool) -> Transformer:
    source, target = (UTM_18N, WGS84) if inverse else (WGS84, UTM_18N)
    # always_xy=True: el orden es (lon, lat) / (x, y) sin importar la convención del EPSG.
    return Transformer.from_crs(source, target, always_xy=True)


def to_utm(lat: float, lon: float) -> tuple[float, float]:
    """(lat, lon) en grados → (x, y) en metros, UTM zona 18N."""
    x, y = _transformer(False).transform(lon, lat)
    return float(x), float(y)


def to_utm_many(lats: Sequence[float], lons: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    """Versión vectorizada de :func:`to_utm`."""
    xs, ys = _transformer(False).transform(np.asarray(lons), np.asarray(lats))
    return np.asarray(xs), np.asarray(ys)


def to_latlon(x: float, y: float) -> tuple[float, float]:
    """(x, y) UTM 18N → (lat, lon). Lo usa la aplicación para dibujar la envolvente."""
    lon, lat = _transformer(True).transform(x, y)
    return float(lat), float(lon)


def nearest_node(x: float, y: float, node_xs: np.ndarray, node_ys: np.ndarray) -> tuple[int, float]:
    """Índice del nodo a menor distancia euclidiana de (x, y) y esa distancia en metros.

    Búsqueda lineal O(V) por consulta (con ~40 lugares no hace falta un árbol k-d).
    """
    squared = (node_xs - x) ** 2 + (node_ys - y) ** 2
    index = int(np.argmin(squared))
    return index, float(np.sqrt(squared[index]))
