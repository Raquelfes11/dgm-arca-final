### Resumen por cerebro

| Métrica | base | rlm | thinking | vllm |
|---|---|---|---|---|
| Éxito en las tareas principales | 6/20 (30 %) | 9/20 (45 %) | 14/20 (70 %) | 20/20 (100 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 1/20 (5 %) | 0/20 (0 %) | 4/20 (20 %) | 17/20 (85 %) |
| Llegan a final_answer | 20/20 (100 %) | 20/20 (100 %) | 19/20 (95 %) | 20/20 (100 %) |
| Casos de borde acertados | 0/5 (0 %) | 2/5 (40 %) | 3/5 (60 %) | 5/5 (100 %) |
| Pasos sin llamada válida | 0/22 (0 %) | 1/21 (5 %) | 6/34 (18 %) | 0/53 (0 %) |
| Llamadas leídas de la etiqueta tool_call | 15/22 (68 %) | 20/20 (100 %) | 28/28 (100 %) | 53/53 (100 %) |
| Llamadas leídas del respaldo Action | 7/22 (32 %) | 0/20 (0 %) | 0/28 (0 %) | 0/53 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 15/22 (68 %) | 20/21 (95 %) | 28/34 (82 %) | 53/53 (100 %) |
| Respuestas vacías | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 0/18 (0 %) | 0/18 (0 %) | 3/18 (17 %) | 3/18 (17 %) |
| Con búsqueda automática previa | 20/20 (100 %) | 20/20 (100 %) | 20/20 (100 %) | 20/20 (100 %) |
| Pasos medios | 1.1 | 1.1 | 1.7 | 2.6 |
| Tokens medios | 6558 | 6674 | 11433 | 16862 |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | base | rlm | thinking | vllm |
|---|---|---|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 4/18 (22 %) | 2/18 (11 %) | 12/18 (67 %) | 18/18 (100 %) |
| Correcto pero sin ninguna cita | 0/18 (0 %) | 5/18 (28 %) | 0/18 (0 %) | 0/18 (0 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) | 0/18 (0 %) | 0/18 (0 %) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) | 0/18 (0 %) | 0/18 (0 %) | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 7/18 (39 %) | 5/18 (28 %) | 4/18 (22 %) | 0/18 (0 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 6/18 (33 %) | 2/18 (11 %) | 1/18 (6 %) | 0/18 (0 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 1/18 (6 %) | 4/18 (22 %) | 1/18 (6 %) | 0/18 (0 %) |
| **Total** | 18/18 (100 %) | 18/18 (100 %) | 18/18 (100 %) | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | base | rlm | thinking | vllm |
|---|---|---|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 0/20 (0 %) | 0/20 (0 %) | 1/20 (5 %) | 0/20 (0 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 13/20 (65 %) | 11/20 (55 %) | 4/20 (20 %) | 0/20 (0 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 1/20 (5 %) | 0/20 (0 %) | 1/20 (5 %) | 0/20 (0 %) |

### Resultado por tarea

| Tarea | base | rlm | thinking | vllm |
|---|---|---|---|---|
| t01 | fallo | fallo | OK | OK |
| t02 | fallo | OK | OK | OK |
| t03 | fallo | fallo | OK | OK |
| t04 | fallo | fallo | OK | OK |
| t05 | OK | fallo | OK | OK |
| t06 | fallo | fallo | OK | OK |
| t07 | OK | OK | OK | OK |
| t08 | fallo | fallo | OK | OK |
| t09 | OK | OK | OK | OK |
| t10 | fallo | OK | fallo | OK |
| t11 | fallo | fallo | fallo | OK |
| t12 | fallo | OK | fallo | OK |
| t13 | fallo | OK | OK | OK |
| t14 | OK | OK | OK | OK |
| t15 | OK | OK | OK | OK |
| t16 | fallo | fallo | OK | OK |
| t17 | fallo | fallo | fallo | OK |
| t18 | OK | OK | OK | OK |
| t19 | fallo | fallo | fallo | OK |
| t20 | fallo | fallo | fallo | OK |
| t21 | fallo | OK | OK | OK |
| t22 | fallo | OK | fallo | OK |
| t23 | fallo | fallo | OK | OK |
| t24 | fallo | fallo | OK | OK |
| t25 | fallo | fallo | fallo | OK |
