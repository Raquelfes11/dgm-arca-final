### Resumen por cerebro

| Métrica | thinking |
|---|---|
| Éxito en las tareas principales | 9/20 (45 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 8/20 (40 %) |
| Llegan a final_answer | 13/20 (65 %) |
| Casos de borde acertados | 2/5 (40 %) |
| Pasos sin llamada válida | 16/47 (34 %) |
| Llamadas leídas de la etiqueta tool_call | 31/31 (100 %) |
| Llamadas leídas del respaldo Action | 0/31 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 31/47 (66 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 1/18 (6 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 2.4 |
| Tokens medios | 12034 |
| Latencia media por tarea | 129.5 s |
| Latencia p95 | 239.6 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | thinking |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 6/18 (33 %) |
| Correcto pero sin ninguna cita | 2/18 (11 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 1/18 (6 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 6/18 (33 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 2/18 (11 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 1/18 (6 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | thinking |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 7/20 (35 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 3/20 (15 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 1/20 (5 %) |

### Resultado por tarea

| Tarea | thinking |
|---|---|
| o01 | fallo |
| o02 | fallo |
| o03 | OK |
| o04 | fallo |
| o05 | OK |
| o06 | OK |
| o07 | fallo |
| o08 | OK |
| o09 | fallo |
| o10 | OK |
| o11 | OK |
| o12 | OK |
| o13 | OK |
| o14 | fallo |
| o15 | fallo |
| o16 | fallo |
| o17 | fallo |
| o18 | OK |
| o19 | fallo |
| o20 | fallo |
| o21 | OK |
| o22 | fallo |
| o23 | fallo |
| o24 | fallo |
| o25 | OK |
