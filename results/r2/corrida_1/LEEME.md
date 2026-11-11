# Corrida 1 de R2 (descartada, se conserva por transparencia)

Primera ejecución de `scripts/run_r2.py` (2026-11-05), con el **borrador** del catálogo.
La verificación pasó, pero en el par `calarca → recuca` la mediana de la cola de
prioridad fue 6,98 ms, cuando al repetirlo 15 veces seguidas da ≈ 2,2 ms (4 829 nodos
explorados, 5 294 inserciones en el heap). Esas 5 repeticiones coincidieron con carga
en la máquina y bajaron el cociente mínimo a 127.

Por decisión del grupo se repitió **el experimento completo una vez**, con el mismo
protocolo y el mismo catálogo (corrida 2, 2026-11-05). Entre las corridas 1 y 2 los
pares, los costos, los nodos explorados y la matriz fueron idénticos; solo cambiaron
los tiempos de ejecución.

El 2026-11-10 se ejecutaron de nuevo R1 y R2 con el **catálogo verificado** (commit
`ff3aa32`). Las coordenadas cambiaron, así que cambiaron los nodos de los lugares, los
pares sorteados (R2-B12) y la matriz. Esa es la corrida vigente, en `results/r2/`; la
corrida 2 no se conservó aparte.

| Corrida | Catálogo | Mediana | Mínimo | Máximo |
|---|---|---|---|---|
| 1 (esta) | borrador | 397 | 127 | 456 |
| 2 (reemplazada) | borrador | 427 | 293 | 520 |
| Vigente (`results/r2/`) | verificado | 270 | 185 | 439 |

Los cocientes de la corrida vigente no se comparan uno a uno con los de las corridas
1 y 2, porque los pares son distintos.
