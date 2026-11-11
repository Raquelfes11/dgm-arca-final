### Resumen por cerebro

| Métrica | base | rlm | thinking |
|---|---|---|---|
| Éxito en las tareas principales | 1/20 (5 %) | 1/20 (5 %) | 5/20 (25 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 0/20 (0 %) | 0/20 (0 %) | 1/20 (5 %) |
| Llegan a final_answer | 14/20 (70 %) | 19/20 (95 %) | 18/20 (90 %) |
| Casos de borde acertados | 0/5 (0 %) | 0/5 (0 %) | 2/5 (40 %) |
| Pasos sin llamada válida | 3/63 (5 %) | 5/27 (19 %) | 11/60 (18 %) |
| Respuestas vacías | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Usa la base de conocimiento (si la necesita) | 3/18 (17 %) | 1/18 (6 %) | 10/18 (56 %) |
| Pasos medios | 3.1 | 1.4 | 3.0 |
| Tokens medios | 6819 | 3715 | 9644 |

### Por qué fallan las tareas principales

| Clase de fallo | base | rlm | thinking |
|---|---|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 6/20 (30 %) | 1/20 (5 %) | 2/20 (10 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 13/20 (65 %) | 18/20 (90 %) | 10/20 (50 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 0/20 (0 %) | 0/20 (0 %) | 3/20 (15 %) |

### Resultado por tarea

| Tarea | base | rlm | thinking |
|---|---|---|---|
| t01 | fallo | fallo | OK |
| t02 | fallo | fallo | fallo |
| t03 | fallo | fallo | fallo |
| t04 | fallo | fallo | OK |
| t05 | fallo | fallo | OK |
| t06 | fallo | fallo | OK |
| t07 | fallo | fallo | fallo |
| t08 | fallo | fallo | fallo |
| t09 | fallo | fallo | fallo |
| t10 | fallo | fallo | fallo |
| t11 | fallo | fallo | fallo |
| t12 | fallo | fallo | fallo |
| t13 | fallo | fallo | fallo |
| t14 | fallo | OK | fallo |
| t15 | OK | fallo | OK |
| t16 | fallo | fallo | fallo |
| t17 | fallo | fallo | fallo |
| t18 | fallo | fallo | fallo |
| t19 | fallo | fallo | fallo |
| t20 | fallo | fallo | fallo |
| t21 | fallo | fallo | fallo |
| t22 | fallo | fallo | fallo |
| t23 | fallo | fallo | OK |
| t24 | fallo | fallo | OK |
| t25 | fallo | fallo | fallo |
