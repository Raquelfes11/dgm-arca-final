### Resumen por cerebro

| Métrica | thinking |
|---|---|
| Éxito en las tareas principales | 12/20 (60 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 3/20 (15 %) |
| Llegan a final_answer | 18/20 (90 %) |
| Casos de borde acertados | 3/5 (60 %) |
| Pasos sin llamada válida | 11/48 (23 %) |
| Llamadas leídas de la etiqueta tool_call | 37/37 (100 %) |
| Llamadas leídas del respaldo Action | 0/37 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 37/48 (77 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 3/18 (17 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 2.4 |
| Tokens medios | 11245 |
| Latencia media por tarea | 96.2 s |
| Latencia p95 | 342.7 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | thinking |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 0/18 (0 %) |
| Correcto pero sin ninguna cita | 10/18 (56 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 6/18 (33 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 0/18 (0 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 2/18 (11 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | thinking |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 2/20 (10 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 4/20 (20 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 2/20 (10 %) |

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
| t13 | fallo |
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
| t24 | fallo |
| t25 | OK |
