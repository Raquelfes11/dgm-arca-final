### Resumen por cerebro

| Métrica | thinking |
|---|---|
| Éxito en las tareas principales | 14/20 (70 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 4/20 (20 %) |
| Llegan a final_answer | 20/20 (100 %) |
| Casos de borde acertados | 5/5 (100 %) |
| Pasos sin llamada válida | 0/33 (0 %) |
| Llamadas leídas de la etiqueta tool_call | 33/33 (100 %) |
| Llamadas leídas del respaldo Action | 0/33 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 33/33 (100 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 5/18 (28 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 1.6 |
| Tokens medios | 11456 |
| Latencia media por tarea | 97.8 s |
| Latencia p95 | 386.0 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | thinking |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 11/18 (61 %) |
| Correcto pero sin ninguna cita | 1/18 (6 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 4/18 (22 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 1/18 (6 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 1/18 (6 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | thinking |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 0/20 (0 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 5/20 (25 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 1/20 (5 %) |

### Resultado por tarea

| Tarea | thinking |
|---|---|
| t01 | OK |
| t02 | OK |
| t03 | OK |
| t04 | OK |
| t05 | OK |
| t06 | OK |
| t07 | OK |
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
| t20 | OK |
| t21 | OK |
| t22 | OK |
| t23 | OK |
| t24 | OK |
| t25 | OK |
