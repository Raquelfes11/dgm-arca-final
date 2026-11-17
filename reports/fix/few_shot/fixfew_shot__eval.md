### Resumen por cerebro

| Métrica | base | rlm | thinking |
|---|---|---|---|
| Éxito en las tareas principales | 5/20 (25 %) | 5/20 (25 %) | 15/20 (75 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 0/20 (0 %) | 0/20 (0 %) | 2/20 (10 %) |
| Llegan a final_answer | 20/20 (100 %) | 17/20 (85 %) | 20/20 (100 %) |
| Casos de borde acertados | 0/5 (0 %) | 2/5 (40 %) | 4/5 (80 %) |
| Pasos sin llamada válida | 1/24 (4 %) | 9/26 (35 %) | 3/32 (9 %) |
| Llamadas leídas de la etiqueta tool_call | 22/23 (96 %) | 17/17 (100 %) | 29/29 (100 %) |
| Llamadas leídas del respaldo Action | 1/23 (4 %) | 0/17 (0 %) | 0/29 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 22/24 (92 %) | 17/26 (65 %) | 29/32 (91 %) |
| Respuestas vacías | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 0/18 (0 %) | 0/18 (0 %) | 5/18 (28 %) |
| Con búsqueda automática previa | 20/20 (100 %) | 20/20 (100 %) | 20/20 (100 %) |
| Pasos medios | 1.2 | 1.3 | 1.6 |
| Tokens medios | 5642 | 7063 | 8714 |

### Por qué fallan las tareas principales

| Clase de fallo | base | rlm | thinking |
|---|---|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 0/20 (0 %) | 3/20 (15 %) | 0/20 (0 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 14/20 (70 %) | 12/20 (60 %) | 5/20 (25 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 1/20 (5 %) | 0/20 (0 %) | 0/20 (0 %) |

### Resultado por tarea

| Tarea | base | rlm | thinking |
|---|---|---|---|
| t01 | OK | fallo | OK |
| t02 | fallo | fallo | OK |
| t03 | fallo | fallo | OK |
| t04 | fallo | fallo | fallo |
| t05 | fallo | fallo | OK |
| t06 | fallo | fallo | OK |
| t07 | OK | fallo | OK |
| t08 | OK | OK | OK |
| t09 | OK | fallo | OK |
| t10 | fallo | OK | fallo |
| t11 | fallo | fallo | OK |
| t12 | fallo | fallo | fallo |
| t13 | fallo | fallo | OK |
| t14 | fallo | OK | OK |
| t15 | OK | OK | OK |
| t16 | fallo | fallo | OK |
| t17 | fallo | fallo | fallo |
| t18 | fallo | OK | OK |
| t19 | fallo | fallo | fallo |
| t20 | fallo | fallo | OK |
| t21 | fallo | OK | OK |
| t22 | fallo | fallo | fallo |
| t23 | fallo | OK | OK |
| t24 | fallo | fallo | OK |
| t25 | fallo | fallo | OK |
