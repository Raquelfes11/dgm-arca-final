### Resumen por cerebro

| Métrica | thinking |
|---|---|
| Éxito en las tareas principales | 7/20 (35 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 4/20 (20 %) |
| Llegan a final_answer | 10/20 (50 %) |
| Casos de borde acertados | 2/5 (40 %) |
| Pasos sin llamada válida | 12/57 (21 %) |
| Llamadas leídas de la etiqueta tool_call | 45/45 (100 %) |
| Llamadas leídas del respaldo Action | 0/45 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 45/57 (79 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 2/18 (11 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 2.9 |
| Tokens medios | 13688 |
| Latencia media por tarea | 109.5 s |
| Latencia p95 | 175.4 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | thinking |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 4/18 (22 %) |
| Correcto pero sin ninguna cita | 1/18 (6 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 1/18 (6 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 6/18 (33 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 3/18 (17 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 3/18 (17 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | thinking |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 10/20 (50 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 0/20 (0 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 3/20 (15 %) |

### Resultado por tarea

| Tarea | thinking |
|---|---|
| t01 | fallo |
| t02 | fallo |
| t03 | OK |
| t04 | fallo |
| t05 | fallo |
| t06 | fallo |
| t07 | OK |
| t08 | OK |
| t09 | OK |
| t10 | fallo |
| t11 | fallo |
| t12 | OK |
| t13 | fallo |
| t14 | fallo |
| t15 | OK |
| t16 | fallo |
| t17 | fallo |
| t18 | OK |
| t19 | fallo |
| t20 | fallo |
| t21 | OK |
| t22 | OK |
| t23 | fallo |
| t24 | fallo |
| t25 | fallo |
