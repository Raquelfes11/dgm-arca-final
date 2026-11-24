### Resumen por cerebro

| Métrica | thinking |
|---|---|
| Éxito en las tareas principales | 11/20 (55 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 5/20 (25 %) |
| Llegan a final_answer | 16/20 (80 %) |
| Casos de borde acertados | 4/5 (80 %) |
| Pasos sin llamada válida | 11/48 (23 %) |
| Llamadas leídas de la etiqueta tool_call | 34/37 (92 %) |
| Llamadas leídas del respaldo Action | 3/37 (8 %) |
| Cumplen el formato (llamada válida con etiqueta) | 34/48 (71 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 4/18 (22 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 2.4 |
| Tokens medios | 10568 |
| Latencia media por tarea | 80.7 s |
| Latencia p95 | 278.3 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | thinking |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 0/18 (0 %) |
| Correcto pero sin ninguna cita | 9/18 (50 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 5/18 (28 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 0/18 (0 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 4/18 (22 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | thinking |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 4/20 (20 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 2/20 (10 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 3/20 (15 %) |

### Resultado por tarea

| Tarea | thinking |
|---|---|
| t01 | fallo |
| t02 | OK |
| t03 | OK |
| t04 | OK |
| t05 | OK |
| t06 | OK |
| t07 | fallo |
| t08 | OK |
| t09 | OK |
| t10 | fallo |
| t11 | fallo |
| t12 | fallo |
| t13 | OK |
| t14 | OK |
| t15 | OK |
| t16 | fallo |
| t17 | fallo |
| t18 | OK |
| t19 | fallo |
| t20 | fallo |
| t21 | OK |
| t22 | fallo |
| t23 | OK |
| t24 | OK |
| t25 | OK |
