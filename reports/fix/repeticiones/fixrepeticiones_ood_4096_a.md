### Resumen por cerebro

| Métrica | thinking |
|---|---|
| Éxito en las tareas principales | 8/20 (40 %) |
| Aciertos casuales (lucky hits) | 1/20 (5 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 3/20 (15 %) |
| Llegan a final_answer | 19/20 (95 %) |
| Casos de borde acertados | 3/5 (60 %) |
| Pasos sin llamada válida | 2/38 (5 %) |
| Llamadas leídas de la etiqueta tool_call | 36/36 (100 %) |
| Llamadas leídas del respaldo Action | 0/36 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 36/38 (95 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 6/18 (33 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 1.9 |
| Tokens medios | 13349 |
| Latencia media por tarea | 96.9 s |
| Latencia p95 | 231.7 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | thinking |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 7/18 (39 %) |
| Correcto pero sin ninguna cita | 0/18 (0 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 1/18 (6 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 6/18 (33 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 4/18 (22 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 0/18 (0 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | thinking |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 1/20 (5 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 9/20 (45 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 2/20 (10 %) |

### Resultado por tarea

| Tarea | thinking |
|---|---|
| o01 | OK |
| o02 | fallo |
| o03 | OK |
| o04 | fallo |
| o05 | OK |
| o06 | OK |
| o07 | OK |
| o08 | OK |
| o09 | fallo |
| o10 | casual |
| o11 | fallo |
| o12 | fallo |
| o13 | OK |
| o14 | fallo |
| o15 | fallo |
| o16 | fallo |
| o17 | OK |
| o18 | fallo |
| o19 | fallo |
| o20 | fallo |
| o21 | OK |
| o22 | fallo |
| o23 | OK |
| o24 | fallo |
| o25 | OK |
