### Resumen por cerebro

| Métrica | base | rlm | thinking |
|---|---|---|---|
| Éxito en las tareas principales | 3/20 (15 %) | 7/20 (35 %) | 13/20 (65 %) |
| Aciertos casuales (lucky hits) | 1/20 (5 %) | 0/20 (0 %) | 1/20 (5 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 0/20 (0 %) | 0/20 (0 %) | 1/20 (5 %) |
| Trazable (correcto, citas válidas y de la evidencia) | 2/18 (11 %) | 2/18 (11 %) | 8/18 (44 %) |
| Respuestas con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) | 0/18 (0 %) | 0/18 (0 %) |
| Llegan a final_answer | 19/20 (95 %) | 20/20 (100 %) | 20/20 (100 %) |
| Casos de borde acertados | 0/5 (0 %) | 2/5 (40 %) | 4/5 (80 %) |
| Pasos sin llamada válida | 3/25 (12 %) | 2/22 (9 %) | 2/29 (7 %) |
| Llamadas leídas de la etiqueta tool_call | 21/22 (95 %) | 20/20 (100 %) | 27/27 (100 %) |
| Llamadas leídas del respaldo Action | 1/22 (5 %) | 0/20 (0 %) | 0/27 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 21/25 (84 %) | 20/22 (91 %) | 27/29 (93 %) |
| Respuestas vacías | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 0/18 (0 %) | 0/18 (0 %) | 5/18 (28 %) |
| Con búsqueda automática previa | 20/20 (100 %) | 20/20 (100 %) | 20/20 (100 %) |
| Pasos medios | 1.2 | 1.1 | 1.4 |
| Tokens medios | 6383 | 6026 | 8798 |

### Por qué fallan las tareas principales

| Clase de fallo | base | rlm | thinking |
|---|---|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 1/20 (5 %) | 0/20 (0 %) | 0/20 (0 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 16/20 (80 %) | 13/20 (65 %) | 7/20 (35 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |

### Resultado por tarea

| Tarea | base | rlm | thinking |
|---|---|---|---|
| t01 | fallo | OK | OK |
| t02 | fallo | fallo | OK |
| t03 | fallo | fallo | OK |
| t04 | fallo | fallo | fallo |
| t05 | fallo | OK | OK |
| t06 | fallo | fallo | OK |
| t07 | fallo | OK | OK |
| t08 | OK | fallo | OK |
| t09 | OK | OK | OK |
| t10 | fallo | fallo | fallo |
| t11 | fallo | fallo | fallo |
| t12 | fallo | fallo | fallo |
| t13 | casual | fallo | fallo |
| t14 | fallo | OK | OK |
| t15 | OK | OK | OK |
| t16 | fallo | fallo | OK |
| t17 | fallo | fallo | fallo |
| t18 | fallo | OK | OK |
| t19 | fallo | fallo | OK |
| t20 | fallo | fallo | casual |
| t21 | fallo | OK | OK |
| t22 | fallo | fallo | fallo |
| t23 | fallo | OK | OK |
| t24 | fallo | fallo | OK |
| t25 | fallo | fallo | OK |
