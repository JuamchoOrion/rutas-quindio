# CAT — Verificación del catálogo de lugares

## Contexto

Enunciado, sección 4: "Las coordenadas se verifican en un mapa". Las reglas del
catálogo (columnas, categorías y mínimos, duraciones, ids, recuadro) están en
**R1-B20 a R1-B24** de [`R1-modelo-red.md`](R1-modelo-red.md) y no se repiten aquí.
Esta spec agrega un registro aparte de qué coordenadas ya revisó el grupo y de
dónde salen los lugares, **sin cambiar las columnas de `data/catalogo.csv`**
(R1-B20).

Archivos: `data/catalogo.csv`, `data/catalogo_verificacion.csv`.
Prueba: `tests/test_catalogo.py`. No hay código nuevo en `src/`: la prueba usa
`load_catalog` y `validate_catalog` de R1 y lee el archivo de verificación con `csv`.

## Comportamiento esperado

- **CAT-B01.** `data/catalogo_verificacion.csv` (UTF-8, separado por comas) tiene
  exactamente las columnas `id, coordenada_verificada, nota`.
- **CAT-B02.** Tiene una fila por cada `id` de `data/catalogo.csv`: ni ids que
  falten, ni ids extra, ni repetidos.
- **CAT-B03.** `coordenada_verificada ∈ {si, no}`. Solo un integrante del grupo la
  cambia a `si`, después de comprobar la coordenada en un mapa; en ese caso la nota
  incluye la fecha de la verificación en ISO 8601 (`AAAA-MM-DD`). Hasta entonces
  queda en `no`. La IA nunca cambia una fila a `si`.
- **CAT-B04.** En una fila con `no`, la nota dice qué es dudoso o qué falta revisar.
  Si la existencia o el nombre del lugar se confirmó en una fuente web, la nota
  incluye su enlace. Si no se encontró una fuente confiable que confirme que el
  lugar existe, la nota **empieza** por `PENDIENTE: buscar lugar real`. Esas filas se
  mantienen en el catálogo para cumplir los mínimos de R1-B21, pero no son
  definitivas: antes de ejecutar R1 (`scripts/build_network.py`) no debe quedar
  ninguna (CAT-C06 las lista sin hacer fallar `pytest`).
- **CAT-B05.** La coordenada de `armenia` es igual a la constante
  `PLAZA_BOLIVAR_ARMENIA` de `scripts/build_network.py` (R1-B23 la fija como punto
  de partida). Su nota es `copiada de PLAZA_BOLIVAR_ARMENIA (también sin verificar)`
  mientras no se verifique.
- **CAT-B06.** La categoría `finca_hotel` solo incluye fincas cafeteras u hoteles
  rurales reales del Quindío (enunciado, sección 4); no se incluyen hoteles de
  cadena. La categoría `acopio` solo incluye puntos de compra de café o trilladoras
  reales. Esta regla se revisa a mano (no tiene prueba automática).

## Casos de prueba

| ID | Entrada | Resultado esperado |
|---|---|---|
| CAT-C01 | `data/catalogo.csv` y `data/catalogo_verificacion.csv` | el conjunto de ids es el mismo y ninguno se repite en la verificación (CAT-B02) |
| CAT-C02 | `data/catalogo_verificacion.csv` | columnas exactas (CAT-B01); todo valor de `coordenada_verificada` es `si` o `no` (CAT-B03); toda fila con `no` tiene la nota no vacía y toda fila cuya nota empieza por `PENDIENTE` está en `no` (CAT-B04) |
| CAT-C03 | Filas con `coordenada_verificada = si` | la nota contiene una fecha `AAAA-MM-DD` válida (CAT-B03) |
| CAT-C04 | `validate_catalog(load_catalog("data/catalogo.csv"))` | `[]` (R1-B21 a R1-B24) |
| CAT-C05 | Fila `armenia` y `PLAZA_BOLIVAR_ARMENIA` (leída con `ast`, sin importar el script ni OSMnx) | misma lat/lon; si está en `no`, la nota es la de CAT-B05 |
| CAT-C06 | Filas cuya nota empieza por `PENDIENTE: buscar lugar real` | si hay alguna, `pytest.skip` con la lista de sus ids; si no hay, pasa. Nunca falla (CAT-B04) |

## Fuera de alcance

- Verificación automática de coordenadas (geocodificación).
- Cambios a R1-B20..R1-B24 o al script de R1.
