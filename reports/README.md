# Informes (reports/)

Cada ejecución del banco, o de un experimento, deja aquí un JSON con la respuesta, los pasos y las
métricas de cada tarea. Las entradas de `docs/EXPERIMENTS.md` citan estos ficheros por su ruta.

- `phase1/` a `phase4/`: los informes de las cuatro fases de la práctica (ARCA). `phase4/phase4_eval.json`
  es la línea base del proyecto final y no se sobrescribe; es el valor por defecto de `agent.evaluate`
  y `agent.analyze_eval`, así que pasa siempre `--out` con otra ruta.
- `fix/NN/`: los informes del cambio número NN de la lista del proyecto final (por ejemplo `fix/04/` para
  la búsqueda automática). Los ficheros se llaman `fixNN_<brazo>.json`, y las repeticiones llevan
  `_a`, `_b`, `_c`; los `_rescored` son los mismos informes puntuados de nuevo con
  `python -m agent.rescore`.
- `fix/format_route/`: la medición del formato de las llamadas (etiqueta frente a `Action:`), que no tiene
  número propio en la lista.
- `rag/`, `rlm/`: informes de la fase 3 y de los adaptadores de la fase 1.

Para un cambio nuevo, lanza `make bench FIX=09 LABEL=auto_a`: guarda `reports/fix/09/fix09_auto_a.json`
y el `.md` con las tablas, y se niega a sobrescribir un informe que ya existe. Si usas
`agent.evaluate` a mano, ponle la carpeta en `--out`; crea la carpeta si no existe.
