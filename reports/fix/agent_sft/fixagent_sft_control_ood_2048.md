### Resumen por cerebro

| Métrica | thinking |
|---|---|
| Éxito en las tareas principales | 11/20 (55 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 4/20 (20 %) |
| Llegan a final_answer | 20/20 (100 %) |
| Casos de borde acertados | 2/5 (40 %) |
| Pasos sin llamada válida | 4/38 (11 %) |
| Llamadas leídas de la etiqueta tool_call | 34/34 (100 %) |
| Llamadas leídas del respaldo Action | 0/34 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 34/38 (89 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 3/18 (17 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 1.9 |
| Tokens medios | 8506 |
| Latencia media por tarea | 96.8 s |
| Latencia p95 | 321.9 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | thinking |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 0/18 (0 %) |
| Correcto pero sin ninguna cita | 11/18 (61 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 5/18 (28 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 0/18 (0 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 2/18 (11 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | thinking |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 0/20 (0 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 7/20 (35 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 2/20 (10 %) |

### Resultado por tarea

| Tarea | thinking |
|---|---|
| o01 | OK |
| o02 | fallo |
| o03 | OK |
| o04 | OK |
| o05 | OK |
| o06 | OK |
| o07 | OK |
| o08 | OK |
| o09 | fallo |
| o10 | OK |
| o11 | fallo |
| o12 | OK |
| o13 | fallo |
| o14 | fallo |
| o15 | fallo |
| o16 | fallo |
| o17 | OK |
| o18 | OK |
| o19 | fallo |
| o20 | fallo |
| o21 | OK |
| o22 | fallo |
| o23 | fallo |
| o24 | fallo |
| o25 | OK |
