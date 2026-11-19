### Resumen por cerebro

| Métrica | base | rlm | thinking |
|---|---|---|---|
| Éxito en las tareas principales | 4/20 (20 %) | 6/20 (30 %) | 14/20 (70 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 0/20 (0 %) | 0/20 (0 %) | 4/20 (20 %) |
| Llegan a final_answer | 20/20 (100 %) | 17/20 (85 %) | 20/20 (100 %) |
| Casos de borde acertados | 0/5 (0 %) | 1/5 (20 %) | 3/5 (60 %) |
| Pasos sin llamada válida | 0/21 (0 %) | 7/24 (29 %) | 5/36 (14 %) |
| Llamadas leídas de la etiqueta tool_call | 17/21 (81 %) | 17/17 (100 %) | 31/31 (100 %) |
| Llamadas leídas del respaldo Action | 4/21 (19 %) | 0/17 (0 %) | 0/31 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 17/21 (81 %) | 17/24 (71 %) | 31/36 (86 %) |
| Respuestas vacías | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 0/18 (0 %) | 0/18 (0 %) | 3/18 (17 %) |
| Con búsqueda automática previa | 20/20 (100 %) | 20/20 (100 %) | 20/20 (100 %) |
| Pasos medios | 1.1 | 1.2 | 1.8 |
| Tokens medios | 6243 | 7856 | 12159 |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | base | rlm | thinking |
|---|---|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 2/18 (11 %) | 2/18 (11 %) | 12/18 (67 %) |
| Correcto pero sin ninguna cita | 0/18 (0 %) | 2/18 (11 %) | 0/18 (0 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) | 0/18 (0 %) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) | 0/18 (0 %) | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 8/18 (44 %) | 7/18 (39 %) | 4/18 (22 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 7/18 (39 %) | 4/18 (22 %) | 1/18 (6 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 1/18 (6 %) | 3/18 (17 %) | 1/18 (6 %) |
| **Total** | 18/18 (100 %) | 18/18 (100 %) | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | base | rlm | thinking |
|---|---|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 0/20 (0 %) | 3/20 (15 %) | 0/20 (0 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 15/20 (75 %) | 11/20 (55 %) | 5/20 (25 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 1/20 (5 %) | 0/20 (0 %) | 1/20 (5 %) |

### Resultado por tarea

| Tarea | base | rlm | thinking |
|---|---|---|---|
| t01 | fallo | fallo | OK |
| t02 | fallo | fallo | OK |
| t03 | fallo | fallo | OK |
| t04 | fallo | fallo | OK |
| t05 | OK | OK | OK |
| t06 | fallo | fallo | OK |
| t07 | OK | fallo | OK |
| t08 | fallo | fallo | OK |
| t09 | fallo | OK | OK |
| t10 | fallo | fallo | fallo |
| t11 | fallo | fallo | fallo |
| t12 | fallo | OK | fallo |
| t13 | fallo | OK | OK |
| t14 | OK | OK | OK |
| t15 | OK | OK | OK |
| t16 | fallo | fallo | fallo |
| t17 | fallo | fallo | fallo |
| t18 | fallo | fallo | OK |
| t19 | fallo | fallo | fallo |
| t20 | fallo | fallo | OK |
| t21 | fallo | OK | OK |
| t22 | fallo | fallo | OK |
| t23 | fallo | fallo | fallo |
| t24 | fallo | fallo | OK |
| t25 | fallo | fallo | fallo |
