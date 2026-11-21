# Banco de tareas de la fase 4

`tasks.jsonl` tiene 25 tareas del asistente de cálculo de medicación para estudiantes de
enfermería: **20 principales** (cuentan para la tasa de éxito) y **5 de borde** (se miden
aparte). Cada tarea necesita al menos dos herramientas en las principales, tiene una forma
automática de comprobar la respuesta final y, cuando la respuesta sale de una ficha, cita
literalmente el pasaje del corpus en el que se apoya.

## Formato

Una tarea por línea, en JSON:

| Campo | Para qué sirve |
|---|---|
| `id` | `t01`…`t25`; se pasa a `--ids` para repetir solo algunas |
| `category` | `ficha_calculo`, `ficha_conversion`, `cima_calculo`, `dos_fichas`, `larga` (principales) y `fuera_del_corpus`, `hoja_preparacion`, `herramienta_con_error` (borde) |
| `core` | `false` en las de borde; si falta, vale `true` |
| `task` | La pregunta, tal como la escribiría un estudiante |
| `required_tools` | Herramientas que tiene que usar para resolverla bien (`evaluate` anota si las usó) |
| `check` | Cómo se comprueba la respuesta (ver abajo) |
| `answer_exprs` | La aritmética que da cada número esperado, para que `validate_bench` la recalcule |
| `evidence` | `[{file, text}]`: pasaje literal de `rag/corpus/<file>` del que sale el dato |
| `solution` | Resolución paso a paso, para humanos |
| `live_api` | `true` si la tarea depende de la API de CIMA en vivo (t14, t15) |
| `expected_behaviour` | En las de borde, qué se espera que haga el agente |

### Tipos de `check`

* `{"type": "number", "value": 480}`: algún número de la respuesta vale 480 (con
  `"tolerance"` opcional). Lee `7,5` como 7,5 y `2.310` o `2,310` como 2310; `1.050` lo
  acepta como 1,05 y como 1050 porque el texto no dice cuál de los dos es.
* `{"type": "contains", "value": "..."}`: subcadena, sin distinguir mayúsculas ni acentos.
* `{"type": "regex", "value": "..."}`: expresión regular tal cual (usad `(?i)` para ignorar
  mayúsculas).
* `{"type": "all" | "any", "checks": [...]}`: todas o alguna de las comprobaciones.
* Cualquiera admite `"negate": true`, que exige lo contrario. Se usa en las de borde: "no
  da ninguna dosis" es una regex de dosis con `negate`.

## Las tareas

* **t01–t09** (`ficha_calculo`): se busca la dosis en la ficha y se calcula con el peso o la
  concentración del enunciado.
* **t10–t13** (`ficha_conversion`): además hay que cambiar de unidades o elegir un valor de un
  rango (µg/kg/min a mg/h, días a horas, volumen de una dosis de carga, extremo alto de un
  rango).
* **t14, t15** (`cima_calculo`): la concentración sale de CIMA, no del corpus.
* **t16–t18** (`dos_fichas`): hay que consultar dos medicamentos y combinarlos.
* **t19, t20** (`larga`): tres y cuatro cálculos seguidos en la misma pregunta; ponen a
  prueba la memoria y el límite de pasos.
* **t21–t25** (borde): medicamento que no está en el corpus (t21, t22), hoja PDF que el agente
  tiene que generar y cuya ruta debe citar (t23), conversión imposible (t24) y medicamento
  que no existe en CIMA (t25). Acierta quien reconoce que no puede, no quien inventa.

## Cómo se usa

En la DGX, con el corpus descargado (`rag/corpus/` no está en git):

```bash
uv run python -m rag.download_corpus --from-manifest     # una vez
uv run python -m agent.validate_bench                    # estructura, aritmética y evidencias
uv run python -m agent.validate_bench --retrieval        # ¿llega el pasaje al top-5?
uv run pytest tests/test_agent_bench.py
uv run python -m agent.evaluate --bench agent/bench/tasks.jsonl --brains base rlm thinking
```

Para repetir la evaluación sin acordarse de los tres pasos hay un atajo, `make bench`. Valida el
banco, evalúa y saca las tablas, y guarda cada ejecución con su propio nombre en
`reports/fix/NN/fixNN_<etiqueta>.json` (y el `.md` con las tablas al lado). Así nunca pisa la
línea base de la fase 4. Si el fichero ya existe se niega a sobrescribirlo, salvo con `FORCE=1`.

```bash
make bench FIX=09 LABEL=auto_a                              # cerebro thinking, rag_mode auto
make bench FIX=09 LABEL=auto_b BRAINS="base rlm thinking"   # varios cerebros
make bench FIX=09 LABEL=sin_filtro ARCA_DRUG_FILTER=0       # las variables ARCA_* se pasan igual
make bench FIX=09 LABEL=sin_kb RAG_MODE=off NO_TOOLS=1 IDS="t01 t02"
make bench-check RETRIEVAL=1                                # solo validar, mirando también el retriever
```

Variables: `FIX` (número del cambio o nombre de la carpeta, obligatorio), `LABEL` (obligatorio),
`BRAINS` (por defecto `thinking`), `RAG_MODE` (`auto`), `MAX_STEPS` (10), `IDS`, `NO_TOOLS`,
`FORCE`. Con `make` sin argumentos sale la lista.

Sin `--out`, `evaluate` escribe `reports/phase4/phase4_eval.json` (la línea base): por cerebro, tasa de éxito, pasos y tokens
medios de las tareas principales, las mismas cifras de las de borde en `edge`, el desglose
por `category` y cada fila con las herramientas que usó.

Para entender los resultados, y no solo la tasa de éxito, `analyze_eval` saca las tablas del
informe (éxito fiel, pasos sin llamada válida, respuestas vacías, uso de la base de
conocimiento, clases de fallo y resultado por tarea):

```bash
uv run python -m agent.analyze_eval --markdown reports/phase4/phase4_analysis.md
```

`validate_bench` hay que pasarlo cada vez que se vuelva a descargar el corpus: CIMA actualiza
las fichas y una cifra puede cambiar.

## Limitaciones

* El `check` numérico acepta **cualquier** número de la respuesta que coincida. Un modelo
  puede acertar por casualidad si el valor es pequeño (un 2 o un 4 aparecen en casi
  cualquier texto). Por eso `tools_used` y `required_tools_used` se guardan en cada fila:
  mirad también cuántas veces usó las herramientas que debía.
* t14 y t15 dependen de la API de CIMA: sin red o con un cambio en la ficha pueden fallar
  por motivos ajenos al agente.
* `create_preparation_sheet` tiene efectos secundarios: el agente solo la ejecuta si la tarea la
  pide de forma explícita, y t23 la pide. t23 mide que la genere y cite la ruta real del PDF;
  la versión anterior, en la que la hoja se bloqueaba, ya no se mide.
* En t21 y t22 el `check` rechaza que la respuesta dé una cifra, pero acepta cifras entre
  comillas (t21): el agente puede citar lo que buscó ("omeprazol 40 mg") sin que cuente como dosis.
* Las dosis son las de las fichas descargadas el día de la descarga, con pesos y
  concentraciones inventados. Es un banco para comparar cerebros, no una referencia clínica.

## Banco OOD (`tasks_ood.jsonl`)

25 tareas más (20 principales + 5 de borde, ids `o01`…`o25`, mismas categorías y formato que
`tasks.jsonl`) para comprobar que no hay sobreajuste a las 25 originales. Usan **solo
medicamentos que no aparecen en `tasks.jsonl`**, otras secciones de la ficha (conservación,
velocidades de perfusión, dosis pediátricas, topes máximos) y, en CIMA en vivo, ketorolaco y
haloperidol (o14, o15). Los datos salen de las fichas técnicas de CIMA, y cada `evidence` es un
pasaje literal de `rag/corpus/`.

```bash
uv run python -m agent.validate_bench --bench agent/bench/tasks_ood.jsonl
uv run python -m agent.evaluate --bench agent/bench/tasks_ood.jsonl --brains thinking
```
