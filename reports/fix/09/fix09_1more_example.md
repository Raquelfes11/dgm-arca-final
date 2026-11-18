### Resumen por cerebro

| Métrica | base | rlm | thinking |
|---|---|---|---|
| Éxito en las tareas principales | 5/20 (25 %) | 7/20 (35 %) | 15/20 (75 %) |
| Aciertos casuales (lucky hits) | 1/20 (5 %) | 0/20 (0 %) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 0/20 (0 %) | 0/20 (0 %) | 1/20 (5 %) |
| Llegan a final_answer | 20/20 (100 %) | 18/20 (90 %) | 19/20 (95 %) |
| Casos de borde acertados | 0/5 (0 %) | 3/5 (60 %) | 3/5 (60 %) |
| Pasos sin llamada válida | 0/22 (0 %) | 6/24 (25 %) | 3/31 (10 %) |
| Llamadas leídas de la etiqueta tool_call | 21/22 (95 %) | 18/18 (100 %) | 28/28 (100 %) |
| Llamadas leídas del respaldo Action | 1/22 (5 %) | 0/18 (0 %) | 0/28 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 21/22 (95 %) | 18/24 (75 %) | 28/31 (90 %) |
| Respuestas vacías | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 0/18 (0 %) | 0/18 (0 %) | 5/18 (28 %) |
| Con búsqueda automática previa | 20/20 (100 %) | 20/20 (100 %) | 20/20 (100 %) |
| Pasos medios | 1.1 | 1.2 | 1.6 |
| Tokens medios | 6427 | 7671 | 10443 |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | base | rlm | thinking |
|---|---|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 4/18 (22 %) | 2/18 (11 %) | 12/18 (67 %) |
| Correcto pero sin ninguna cita | 0/18 (0 %) | 2/18 (11 %) | 0/18 (0 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) | 0/18 (0 %) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) | 1/18 (6 %) | 1/18 (6 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 6/18 (33 %) | 6/18 (33 %) | 3/18 (17 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 7/18 (39 %) | 3/18 (17 %) | 1/18 (6 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 1/18 (6 %) | 4/18 (22 %) | 1/18 (6 %) |
| **Total** | 18/18 (100 %) | 18/18 (100 %) | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | base | rlm | thinking |
|---|---|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 0/20 (0 %) | 2/20 (10 %) | 1/20 (5 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 15/20 (75 %) | 11/20 (55 %) | 4/20 (20 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |

### Resultado por tarea

| Tarea | base | rlm | thinking |
|---|---|---|---|
| t01 | fallo | OK | OK |
| t02 | OK | OK | OK |
| t03 | fallo | fallo | OK |
| t04 | fallo | fallo | OK |
| t05 | OK | fallo | OK |
| t06 | fallo | fallo | OK |
| t07 | fallo | fallo | OK |
| t08 | OK | OK | OK |
| t09 | fallo | OK | OK |
| t10 | fallo | fallo | OK |
| t11 | fallo | fallo | fallo |
| t12 | fallo | fallo | fallo |
| t13 | casual | fallo | OK |
| t14 | fallo | OK | OK |
| t15 | OK | OK | OK |
| t16 | fallo | fallo | OK |
| t17 | fallo | fallo | fallo |
| t18 | OK | OK | OK |
| t19 | fallo | fallo | fallo |
| t20 | fallo | fallo | fallo |
| t21 | fallo | OK | OK |
| t22 | fallo | OK | OK |
| t23 | fallo | OK | OK |
| t24 | fallo | fallo | fallo |
| t25 | fallo | fallo | fallo |
