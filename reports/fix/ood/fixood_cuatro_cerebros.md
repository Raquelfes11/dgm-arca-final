### Resumen por cerebro

| Métrica | base | rlm | thinking | vllm |
|---|---|---|---|---|
| Éxito en las tareas principales | 3/20 (15 %) | 4/20 (20 %) | 9/20 (45 %) | 19/20 (95 %) |
| Aciertos casuales (lucky hits) | 1/20 (5 %) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 0/20 (0 %) | 0/20 (0 %) | 2/20 (10 %) | 15/20 (75 %) |
| Llegan a final_answer | 19/20 (95 %) | 17/20 (85 %) | 19/20 (95 %) | 19/20 (95 %) |
| Casos de borde acertados | 0/5 (0 %) | 1/5 (20 %) | 4/5 (80 %) | 4/5 (80 %) |
| Pasos sin llamada válida | 2/27 (7 %) | 7/24 (29 %) | 3/37 (8 %) | 1/65 (2 %) |
| Llamadas leídas de la etiqueta tool_call | 23/25 (92 %) | 17/17 (100 %) | 34/34 (100 %) | 64/64 (100 %) |
| Llamadas leídas del respaldo Action | 2/25 (8 %) | 0/17 (0 %) | 0/34 (0 %) | 0/64 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 23/27 (85 %) | 17/24 (71 %) | 34/37 (92 %) | 64/65 (98 %) |
| Respuestas vacías | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 1/18 (6 %) | 0/18 (0 %) | 5/18 (28 %) | 4/18 (22 %) |
| Con búsqueda automática previa | 20/20 (100 %) | 20/20 (100 %) | 20/20 (100 %) | 20/20 (100 %) |
| Pasos medios | 1.4 | 1.2 | 1.9 | 3.2 |
| Tokens medios | 8209 | 7915 | 12512 | 22290 |
| Latencia media por tarea | 30.9 s | 49.8 s | 24.2 s | 12.7 s |
| Latencia p95 | 92.8 s | 289.9 s | 48.2 s | 36.3 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | base | rlm | thinking | vllm |
|---|---|---|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 2/18 (11 %) | 2/18 (11 %) | 8/18 (44 %) | 15/18 (83 %) |
| Correcto pero sin ninguna cita | 1/18 (6 %) | 1/18 (6 %) | 0/18 (0 %) | 1/18 (6 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) | 0/18 (0 %) | 0/18 (0 %) | 1/18 (6 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) | 0/18 (0 %) | 1/18 (6 %) | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 7/18 (39 %) | 6/18 (33 %) | 6/18 (33 %) | 0/18 (0 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 8/18 (44 %) | 1/18 (6 %) | 3/18 (17 %) | 0/18 (0 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 0/18 (0 %) | 8/18 (44 %) | 0/18 (0 %) | 1/18 (6 %) |
| **Total** | 18/18 (100 %) | 18/18 (100 %) | 18/18 (100 %) | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | base | rlm | thinking | vllm |
|---|---|---|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 1/20 (5 %) | 3/20 (15 %) | 1/20 (5 %) | 1/20 (5 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 16/20 (80 %) | 13/20 (65 %) | 8/20 (40 %) | 0/20 (0 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 0/20 (0 %) | 0/20 (0 %) | 2/20 (10 %) | 0/20 (0 %) |

### Resultado por tarea

| Tarea | base | rlm | thinking | vllm |
|---|---|---|---|---|
| o01 | fallo | OK | OK | OK |
| o02 | fallo | fallo | fallo | OK |
| o03 | OK | fallo | OK | OK |
| o04 | fallo | fallo | fallo | OK |
| o05 | OK | OK | OK | OK |
| o06 | fallo | fallo | OK | OK |
| o07 | fallo | fallo | OK | OK |
| o08 | fallo | fallo | OK | OK |
| o09 | fallo | fallo | fallo | OK |
| o10 | casual | fallo | OK | OK |
| o11 | fallo | fallo | fallo | OK |
| o12 | fallo | fallo | fallo | OK |
| o13 | OK | fallo | OK | OK |
| o14 | fallo | fallo | fallo | OK |
| o15 | fallo | OK | fallo | OK |
| o16 | fallo | fallo | fallo | fallo |
| o17 | fallo | OK | OK | OK |
| o18 | fallo | fallo | fallo | OK |
| o19 | fallo | fallo | fallo | OK |
| o20 | fallo | fallo | fallo | OK |
| o21 | fallo | fallo | OK | OK |
| o22 | fallo | fallo | OK | OK |
| o23 | fallo | fallo | OK | OK |
| o24 | fallo | fallo | fallo | fallo |
| o25 | fallo | OK | OK | OK |
