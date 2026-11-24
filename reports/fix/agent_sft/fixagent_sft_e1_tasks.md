### Resumen por cerebro

| Métrica | thinking |
|---|---|
| Éxito en las tareas principales | 9/20 (45 %) |
| Aciertos casuales (lucky hits) | 1/20 (5 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 0/20 (0 %) |
| Llegan a final_answer | 15/20 (75 %) |
| Casos de borde acertados | 1/5 (20 %) |
| Pasos sin llamada válida | 11/26 (42 %) |
| Llamadas leídas de la etiqueta tool_call | 15/15 (100 %) |
| Llamadas leídas del respaldo Action | 0/15 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 15/26 (58 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 0/18 (0 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 1.3 |
| Tokens medios | 5684 |
| Latencia media por tarea | 68.6 s |
| Latencia p95 | 228.6 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | thinking |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 1/18 (6 %) |
| Correcto pero sin ninguna cita | 6/18 (33 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 6/18 (33 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 1/18 (6 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 4/18 (22 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | thinking |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 5/20 (25 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 6/20 (30 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 0/20 (0 %) |

### Resultado por tarea

| Tarea | thinking |
|---|---|
| t01 | OK |
| t02 | OK |
| t03 | fallo |
| t04 | OK |
| t05 | fallo |
| t06 | fallo |
| t07 | OK |
| t08 | OK |
| t09 | OK |
| t10 | fallo |
| t11 | casual |
| t12 | fallo |
| t13 | OK |
| t14 | OK |
| t15 | OK |
| t16 | fallo |
| t17 | fallo |
| t18 | fallo |
| t19 | fallo |
| t20 | fallo |
| t21 | OK |
| t22 | fallo |
| t23 | fallo |
| t24 | fallo |
| t25 | fallo |
