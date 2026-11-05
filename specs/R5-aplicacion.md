# R5 — Aplicación demostrativa

## Contexto

Enunciado, sección 5, requerimiento 5. Se evalúa que muestre los resultados, no su
diseño visual. Debe ejecutarse localmente siguiendo el README.

Tecnología: **Streamlit** (interfaz web local con un solo comando) + **Folium**
(mapas Leaflet, con `streamlit-folium`). Archivos:

- `app/app.py`: solo la interfaz (Streamlit). Se ejecuta con
  `streamlit run app/app.py` después de `pip install -e ".[red,app]"`.
- `src/rutas/app_support.py`: la lógica sin Streamlit (rutas sobre el mapa,
  comparación de recorridos, envolvente, búsqueda de resultados), para poder
  probarla con `pytest`.

## Comportamiento esperado

- **R5-B01. Ruta origen-destino.** Dos selectores con los lugares del catálogo; al
  confirmar se ejecuta `dijkstra_heap` **en el momento** entre los nodos de los dos
  lugares (la ruta y su tiempo **no** se leen de la matriz de R2) y se dibuja la ruta
  sobre el mapa con su tiempo de viaje (min) y los nodos explorados.
- **R5-B02. Envolvente.** Capa con el polígono de la envolvente de R3 (puede leerse
  de `results/r3/envolvente_red.json`), transformado de UTM a lat/lon.
- **R5-B03. Itinerario.** Selector del lugar de partida (cualquier lugar del
  catálogo; por defecto Armenia) y selección múltiple de 6 a 8 lugares de la
  categoría `atractivo`, sin incluir el de partida. El botón de calcular está
  desactivado fuera de ese rango y la app dice por qué. Los tiempos entre lugares
  salen de `results/r2/matriz_tiempos.csv` (leída con `load_travel_time_matrix`,
  R2-B15); con ellos se arma la submatriz de la instancia (`instance_matrix`) y
  Held-Karp y el vecino más cercano se ejecutan **en el momento** sobre ella:
  1. *Comparación sobre el conjunto elegido por el usuario (sin quitar nada):*
     `held_karp` y `nearest_neighbor_tour` sobre la misma instancia
     (`instance_matrix`). Para cada uno se muestra el orden, el tiempo de
     desplazamientos, el de visitas y el total con visitas. La diferencia del
     vecino más cercano frente a Held-Karp se da en minutos y en porcentaje, ambas
     **sobre los desplazamientos** (el costo del recorrido), igual que R4-B14:
     `gap% = gap_percent(desplazamiento_vecino, desplazamiento_held_karp)`. Como los
     dos visitan los mismos lugares, la diferencia en minutos de los totales con
     visitas es la misma. Los dos recorridos se
     dibujan en el mapa con colores distintos; cada tramo es la ruta de
     `dijkstra_heap` entre los nodos de los dos lugares.
  2. *Plan de un día:* `plan_day` (R4-B15 a R4-B18) sobre el mismo conjunto. Se
     muestra la tabla con el formato del anexo, los totales, si cabe en 11 h y, si se
     quitaron atractivos, cuáles y con qué ahorro.
- **R5-B04. Resultados.** Pestaña con las tablas (desde los CSV de `results/`) y
  las gráficas (PNG de `results/`) de R1 a R4.
- **R5-B05.** La app carga `data/processed/` y nunca descarga la red.
- **R5-B06. Archivos que faltan.** Si falta un archivo de `results/` (por ejemplo
  `results/r3/envolvente_red.json` antes de ejecutar `scripts/run_r3.py`), la app no
  falla: en su lugar muestra un aviso con el nombre del archivo y el script que lo
  genera. Si falta `data/processed/`, muestra cómo ejecutar R1 y se detiene.
- **R5-B07. Ruta sobre el mapa.** La ruta se dibuja con las coordenadas
  (lat, lon) de sus nodos, en orden; se marcan el origen y el destino. El tiempo se
  muestra en minutos y coincide con la celda de la matriz de R2 (R5-C01).
- **R5-B08. Envolvente.** Se lee `results/r3/envolvente_red.json` con el formato
  que define la spec de R3 (`{"crs": "EPSG:32618", "n_puntos": …, "vertices":
  [[x, y], …]}`, metros enteros, orden de R3-B04). Si `crs` no es `EPSG:32618`, se
  avisa y no se dibuja. Los vértices se convierten a (lat, lon) con `geo.to_latlon` y se dibujan como
  polígono cerrado sobre el mapa del departamento, junto con los lugares del
  catálogo.
- **R5-B09. Resultados.** Por cada requerimiento R1–R4 se muestran todos los
  `*.csv` de `results/rX/` (sin entrar en subcarpetas, como `results/r2/corrida_1/`)
  como tablas y todos los `*.png` como imágenes, en orden alfabético.
- **R5-B10. Carga única.** La red, el catálogo y la matriz se cargan una sola vez por
  sesión (`st.cache_resource`), no en cada interacción.

- **R5-B11. Resultado de la selección actual.** La ruta y el itinerario se guardan
  junto con los datos de entrada que los produjeron; si el usuario cambia la
  selección sin volver a calcular, no se muestra el resultado anterior, sino la
  indicación de pulsar el botón.
- **R5-B12. Pestañas y mapas.** Solo se ejecuta la pestaña abierta
  (`st.tabs(..., on_change="rerun")`), que queda en la URL (`?seccion=`): un mapa
  de Leaflet creado en una pestaña oculta tiene ancho 0 y se muestra como el mundo
  repetido. Los mapas parten centrados en el Quindío, con zoom mínimo 8 y límites en
  la región. Mapa base: gris claro de Esri (sin clave) con capa de nombres;
  OpenStreetMap como alternativa en el control de capas. Los colores de categorías y
  recorridos se validaron para daltonismo y contraste, y el vecino más cercano se
  dibuja punteado (no se distingue solo por color).

## Casos de prueba

Automáticos (`tests/test_r5_app.py`):

| ID | Entrada | Resultado esperado |
|---|---|---|
| R5-C06 | `compare_tours` con la matriz `CE` de R4 y visitas de 10 min por atractivo | desplazamientos: Held-Karp 5 s y vecino 22 s; totales con visitas 1 805 s y 1 822 s; diferencia 17 s y 340 % (sobre los desplazamientos) |
| R5-C07 | `route_latlons` con una ruta de 3 nodos | 3 pares (lat, lon) en el orden de la ruta |
| R5-C08 | `hull_latlons` con un JSON de 4 vértices UTM | 4 pares (lat, lon), cada uno igual a `to_latlon` de su vértice |
| R5-C09 | `hull_latlons` / `result_files` con archivos que no existen | `None` y listas vacías, sin excepción (R5-B06) |
| R5-C10 | `result_files` sobre una carpeta con CSV, PNG y una subcarpeta | solo los archivos de la carpeta, en orden alfabético (R5-B09) |
| R5-C11 | La app completa con `streamlit.testing` (AppTest), abriendo cada pestaña con `?seccion=` | se ejecuta sin excepciones en las cuatro pestañas, calcula una ruta y un itinerario de 7 atractivos; `pytest.skip` si faltan `data/processed/` o `results/` |

Manuales (con captura en el documento técnico):

| ID | Acción | Resultado esperado |
|---|---|---|
| R5-C01 | Armenia → Salento | ruta dibujada; tiempo igual al de `matriz_tiempos.csv` |
| R5-C02 | Activar capa de envolvente | polígono que rodea toda la red |
| R5-C03 | Elegir 5 atractivos | la app pide entre 6 y 8 |
| R5-C04 | Elegir 7 atractivos | dos recorridos, tiempos y diferencia ≥ 0 |
| R5-C05 | Pestaña de resultados | se ven las tablas y gráficas de R1–R4 |
