# Corrida 1 de R2 (descartada, se conserva por transparencia)

Primera ejecución de `scripts/run_r2.py` (2026-11-05). La verificación pasó, pero en
el par `calarca → recuca` la mediana de la cola de prioridad fue 6,98 ms, cuando al
repetirlo 15 veces seguidas da ≈ 2,2 ms (4 829 nodos explorados, 5 294 inserciones en
el heap). Esas 5 repeticiones coincidieron con carga en la máquina y bajaron el
cociente mínimo a 127.

Por decisión del grupo se repitió **el experimento completo una vez**, con el mismo
protocolo. Los resultados vigentes son los de `results/r2/`. Entre las dos corridas
los pares, los costos, los nodos explorados y la matriz son idénticos; solo cambian
los tiempos de ejecución.

| Corrida | Mediana | Mínimo | Máximo |
|---|---|---|---|
| 1 (esta) | 397 | 127 | 456 |
| 2 (vigente) | 427 | 293 | 520 |
