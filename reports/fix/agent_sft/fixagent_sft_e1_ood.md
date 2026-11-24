### Resumen por cerebro

| Métrica | thinking |
|---|---|
| Éxito en las tareas principales | 4/20 (20 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 0/20 (0 %) |
| Llegan a final_answer | 10/20 (50 %) |
| Casos de borde acertados | 1/5 (20 %) |
| Pasos sin llamada válida | 20/30 (67 %) |
| Llamadas leídas de la etiqueta tool_call | 10/10 (100 %) |
| Llamadas leídas del respaldo Action | 0/10 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 10/30 (33 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 0/18 (0 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 1.5 |
| Tokens medios | 7010 |
| Latencia media por tarea | 75.9 s |
| Latencia p95 | 240.7 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | thinking |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 1/18 (6 %) |
| Correcto pero sin ninguna cita | 3/18 (17 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 6/18 (33 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 2/18 (11 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 6/18 (33 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | thinking |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 10/20 (50 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 6/20 (30 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 0/20 (0 %) |

### Resultado por tarea

| Tarea | thinking |
|---|---|
| o01 | OK |
| o02 | fallo |
| o03 | OK |
| o04 | fallo |
| o05 | fallo |
| o06 | fallo |
| o07 | fallo |
| o08 | fallo |
| o09 | fallo |
| o10 | fallo |
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
| o21 | fallo |
| o22 | fallo |
| o23 | OK |
| o24 | fallo |
| o25 | fallo |
