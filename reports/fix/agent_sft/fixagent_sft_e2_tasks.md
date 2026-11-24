### Resumen por cerebro

| Métrica | thinking |
|---|---|
| Éxito en las tareas principales | 6/20 (30 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 1/20 (5 %) |
| Llegan a final_answer | 8/20 (40 %) |
| Casos de borde acertados | 2/5 (40 %) |
| Pasos sin llamada válida | 18/44 (41 %) |
| Llamadas leídas de la etiqueta tool_call | 26/26 (100 %) |
| Llamadas leídas del respaldo Action | 0/26 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 26/44 (59 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 1/18 (6 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 2.2 |
| Tokens medios | 9934 |
| Latencia media por tarea | 82.5 s |
| Latencia p95 | 256.4 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | thinking |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 2/18 (11 %) |
| Correcto pero sin ninguna cita | 2/18 (11 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 6/18 (33 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 3/18 (17 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 5/18 (28 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | thinking |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 12/20 (60 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 1/20 (5 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 1/20 (5 %) |

### Resultado por tarea

| Tarea | thinking |
|---|---|
| t01 | fallo |
| t02 | fallo |
| t03 | OK |
| t04 | fallo |
| t05 | fallo |
| t06 | fallo |
| t07 | fallo |
| t08 | OK |
| t09 | fallo |
| t10 | fallo |
| t11 | fallo |
| t12 | fallo |
| t13 | fallo |
| t14 | OK |
| t15 | OK |
| t16 | fallo |
| t17 | fallo |
| t18 | OK |
| t19 | OK |
| t20 | fallo |
| t21 | OK |
| t22 | fallo |
| t23 | fallo |
| t24 | fallo |
| t25 | OK |
