# R5 — Aplicación demostrativa

## Contexto

Enunciado, sección 5, requerimiento 5. Se evalúa que muestre los resultados, no su
diseño visual. Debe ejecutarse localmente siguiendo el README.

Tecnología propuesta: **Streamlit** (interfaz web local con un solo comando) +
**Folium** (mapas Leaflet). Archivo: `app/app.py`. Estado: **pendiente** (se
implementa después de cerrar R1–R4).

## Comportamiento esperado

- **R5-B01. Ruta origen-destino.** Dos selectores con los lugares del catálogo; al
  confirmar se ejecuta `dijkstra_heap` **en el momento** y se dibuja la ruta sobre
  el mapa con su tiempo de viaje (min) y los nodos explorados.
- **R5-B02. Envolvente.** Capa con el polígono de la envolvente de R3 (puede leerse
  de `results/r3/envolvente_red.json`), transformado de UTM a lat/lon.
- **R5-B03. Itinerario.** Selector del lugar de partida (por defecto Armenia) y
  selección múltiple de 6 a 8 atractivos (la app no deja confirmar fuera de ese
  rango). Se calculan **en el momento** Held-Karp y vecino más cercano; se
  muestran ambos recorridos en el mapa, la tabla del itinerario, el tiempo total
  de cada uno y la diferencia (absoluta y en %).
- **R5-B04. Resultados.** Pestaña con las tablas (desde los CSV de `results/`) y
  las gráficas (PNG de `results/`) de R1 a R4.
- **R5-B05.** La app carga `data/processed/` y nunca descarga la red.

## Casos de prueba (manuales, con captura en el documento técnico)

| ID | Acción | Resultado esperado |
|---|---|---|
| R5-C01 | Armenia → Salento | ruta dibujada; tiempo igual al de `matriz_tiempos.csv` |
| R5-C02 | Activar capa de envolvente | polígono que rodea toda la red |
| R5-C03 | Elegir 5 atractivos | la app pide entre 6 y 8 |
| R5-C04 | Elegir 7 atractivos | dos recorridos, tiempos y diferencia ≥ 0 |
| R5-C05 | Pestaña de resultados | se ven las tablas y gráficas de R1–R4 |
