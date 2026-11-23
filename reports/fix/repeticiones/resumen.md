## Repeticiones del cerebro `thinking`

| Métrica | tasks_1024 (3 ejecuciones) | tasks_4096 (1 ejecuciones) | ood_1024 (3 ejecuciones) | ood_4096 (1 ejecuciones) |
|---|---|---|---|---|
| Éxito en las tareas principales | 67 % [65 %-70 %] | 70 % | 47 % [40 %-50 %] | 40 % |
| Éxito fiel | 15 % [15 %-15 %] | 20 % | 8 % [5 %-10 %] | 15 % |
| Casos de borde acertados | 73 % [60 %-80 %] | 100 % | 53 % [40 %-60 %] | 60 % |
| Llegan a final_answer | 95 % [95 %-95 %] | 100 % | 92 % [85 %-95 %] | 95 % |
| Pasos sin llamada válida | 5 % [0 %-12 %] | 0 % | 13 % [11 %-14 %] | 5 % |
| Busca él mismo en la base de conocimiento | 20 % [17 %-22 %] | 28 % | 31 % [28 %-33 %] | 33 % |
| Correcto y trazable | 59 % [56 %-61 %] | 61 % | 46 % [39 %-50 %] | 39 % |
| Pasos medios | 1.6 [1.6-1.6] | 1.6 | 2.0 [1.9-2.1] | 1.9 |
| Tokens medios | 11113 [10865-11329] | 11456 | 14041 [12734-14785] | 13349 |
| Latencia media por tarea (s) | 86.2 [75.2-94.0] | 97.8 | 84.4 [78.8-88.3] | 96.9 |

Cada celda es la media de las ejecuciones y, entre corchetes, el valor más bajo y el más alto.

| Tareas principales | tasks_1024 | tasks_4096 | ood_1024 | ood_4096 |
|---|---|---|---|---|
| Acertadas en todas las ejecuciones | 13 | 14 | 8 | 8 |
| Acertadas solo en algunas (ruido) | 1 | 0 | 2 | 0 |
| Falladas en todas | 6 | 6 | 10 | 12 |
