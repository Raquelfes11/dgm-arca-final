### Resumen por cerebro

| Métrica | vllm |
|---|---|
| Éxito en las tareas principales | 20/20 (100 %) |
| Aciertos casuales (lucky hits) | 0/20 (0 %) |
| Éxito fiel (correcto y con las herramientas requeridas) | 17/20 (85 %) |
| Llegan a final_answer | 20/20 (100 %) |
| Casos de borde acertados | 5/5 (100 %) |
| Pasos sin llamada válida | 1/53 (2 %) |
| Llamadas leídas de la etiqueta tool_call | 52/52 (100 %) |
| Llamadas leídas del respaldo Action | 0/52 (0 %) |
| Cumplen el formato (llamada válida con etiqueta) | 52/53 (98 %) |
| Respuestas vacías | 0/20 (0 %) |
| Busca él mismo en la base de conocimiento (si la necesita) | 3/18 (17 %) |
| Con búsqueda automática previa | 20/20 (100 %) |
| Pasos medios | 2.6 |
| Tokens medios | 16650 |
| Latencia media por tarea | 8.4 s |
| Latencia p95 | 20.0 s |

### Trazabilidad de las tareas que usan la base de conocimiento

| Clase | vllm |
|---|---|
| Correcto y trazable (citas válidas y de la evidencia) | 17/18 (94 %) |
| Correcto pero sin ninguna cita | 1/18 (6 %) |
| Correcto pero con citas inventadas (no devueltas por la búsqueda) | 0/18 (0 %) |
| Correcto con citas válidas, pero no de la ficha que contiene la evidencia | 0/18 (0 %) |
| Incorrecto y la evidencia nunca llegó al modelo (fallo del retriever) | 0/18 (0 %) |
| Incorrecto aunque tenía la evidencia y la citó bien (fallo de cálculo o lectura) | 0/18 (0 %) |
| Incorrecto, con la evidencia recuperada pero sin cita válida de ella | 0/18 (0 %) |
| **Total** | 18/18 (100 %) |

### Por qué fallan las tareas principales

| Clase de fallo | vllm |
|---|---|
| No llega a dar una respuesta (se agotan los pasos o no hay llamada válida) | 0/20 (0 %) |
| Llama a final_answer pero sin respuesta | 0/20 (0 %) |
| Responde sin usar las herramientas necesarias | 0/20 (0 %) |
| El valor aparece pero sin la unidad correcta o fuera de la respuesta final (lucky hit) | 0/20 (0 %) |
| Usa las herramientas necesarias pero el resultado es incorrecto | 0/20 (0 %) |

### Resultado por tarea

| Tarea | vllm |
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
| t10 | OK |
| t11 | OK |
| t12 | OK |
| t13 | OK |
| t14 | OK |
| t15 | OK |
| t16 | OK |
| t17 | OK |
| t18 | OK |
| t19 | OK |
| t20 | OK |
| t21 | OK |
| t22 | OK |
| t23 | OK |
| t24 | OK |
| t25 | OK |
