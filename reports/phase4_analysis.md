### Resumen por cerebro

| Métrica | base | rlm | thinking |
|---|---|---|---|
| Éxito en las tareas principales | 0/20 (0 %) | 0/20 (0 %) | 2/20 (10 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 0/20 (0 %) | 0/20 (0 %) | 1/20 (5 %) |
| Llegan a final_answer | 3/20 (15 %) | 10/20 (50 %) | 15/20 (75 %) |
| Casos de borde acertados | 0/5 (0 %) | 0/5 (0 %) | 1/5 (20 %) |
| Pasos sin llamada válida | 30/58 (52 %) | 23/34 (68 %) | 22/50 (44 %) |
| Respuestas vacías | 0/20 (0 %) | 9/20 (45 %) | 0/20 (0 %) |
| Usa la base de conocimiento (si la necesita) | 0/18 (0 %) | 1/18 (6 %) | 4/18 (22 %) |
| Pasos medios | 2.9 | 1.7 | 2.5 |
| Tokens medios | 6103 | 4431 | 7728 |

### Por qué fallan las tareas principales

| Clase de fallo | base | rlm | thinking |
|---|---|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 17/20 (85 %) | 10/20 (50 %) | 5/20 (25 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) | 9/20 (45 %) | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 3/20 (15 %) | 1/20 (5 %) | 12/20 (60 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 0/20 (0 %) | 0/20 (0 %) | 1/20 (5 %) |

### Resultado por tarea

| Tarea | base | rlm | thinking |
|---|---|---|---|
| t01 | fallo | fallo | fallo |
| t02 | fallo | fallo | fallo |
| t03 | fallo | fallo | fallo |
| t04 | fallo | fallo | fallo |
| t05 | fallo | fallo | fallo |
| t06 | fallo | fallo | fallo |
| t07 | fallo | fallo | fallo |
| t08 | fallo | fallo | fallo |
| t09 | fallo | fallo | fallo |
| t10 | fallo | fallo | OK |
| t11 | fallo | fallo | fallo |
| t12 | fallo | fallo | fallo |
| t13 | fallo | fallo | OK |
| t14 | fallo | fallo | fallo |
| t15 | fallo | fallo | fallo |
| t16 | fallo | fallo | fallo |
| t17 | fallo | fallo | fallo |
| t18 | fallo | fallo | fallo |
| t19 | fallo | fallo | fallo |
| t20 | fallo | fallo | fallo |
| t21 | fallo | fallo | fallo |
| t22 | fallo | fallo | fallo |
| t23 | fallo | fallo | fallo |
| t24 | fallo | fallo | OK |
| t25 | fallo | fallo | fallo |
