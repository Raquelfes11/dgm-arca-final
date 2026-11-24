### Resumen por cerebro

| Métrica | thinking |
|---|---|
| Éxito en las tareas principales | 4/20 (20 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 3/20 (15 %) |
| Llegan a final_answer | 9/20 (45 %) |
| Casos de borde acertados | 2/5 (40 %) |
| Pasos sin llamada válida | 20/44 (45 %) |
| Llamadas leídas de la etiqueta tool_call | 24/24 (100 %) |
| Llamadas leídas del respaldo Action | 0/24 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 24/44 (55 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 1/18 (6 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 2.2 |
| Tokens medios | 9958 |
| Latencia media por tarea | 92.8 s |
| Latencia p95 | 172.4 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | thinking |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 3/18 (17 %) |
| Correcto pero sin ninguna cita | 1/18 (6 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 7/18 (39 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 4/18 (22 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 3/18 (17 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | thinking |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 11/20 (55 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 3/20 (15 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 2/20 (10 %) |

### Resultado por tarea

| Tarea | thinking |
|---|---|
| o01 | fallo |
| o02 | fallo |
| o03 | OK |
| o04 | fallo |
| o05 | OK |
| o06 | fallo |
| o07 | fallo |
| o08 | OK |
| o09 | fallo |
| o10 | fallo |
| o11 | fallo |
| o12 | fallo |
| o13 | OK |
| o14 | fallo |
| o15 | fallo |
| o16 | fallo |
| o17 | fallo |
| o18 | fallo |
| o19 | fallo |
| o20 | fallo |
| o21 | OK |
| o22 | fallo |
| o23 | fallo |
| o24 | fallo |
| o25 | OK |
