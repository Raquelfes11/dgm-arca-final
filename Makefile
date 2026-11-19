# ARCA · atajos. Escribe `make` sin argumentos para ver la lista.

.DEFAULT_GOAL := help
UV ?= uv

# Banco de tareas del agente (make bench). Cada ejecucion se guarda como
# reports/fix/FIX/fixFIX_LABEL.json (mas el .md con las tablas), nunca en la linea base de la
# fase 4. Las variables de entorno del agente se pasan en la misma orden, por ejemplo
# make bench FIX=09 LABEL=sin_filtro ARCA_DRUG_FILTER=0
BRAINS ?= vllm
RAG_MODE ?= auto
MAX_STEPS ?= 10
FEW_SHOT ?= True
BENCH_OUT = reports/fix/$(FIX)/fix$(FIX)_$(LABEL)

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Instala todo en .venv con uv (fase 1 + RAG + agente + dev)
	$(UV) sync --extra train --extra rag --extra agent

setup-min: ## Instala solo lo necesario para la API y los tests
	$(UV) sync

lock: ## Regenera uv.lock tras cambiar pyproject.toml
	$(UV) lock

test: ## Ejecuta los tests
	$(UV) run pytest

lint: ## Comprueba estilo con ruff
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Formatea el código con ruff
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

check-gpu: ## Diagnóstico de GPU y librerías
	$(UV) run arca-check-gpu

smoke: ## Entrenamiento GRPO de prueba en GPU (10-15 min)
	$(UV) run arca-smoke

smoke-dry: ## Prueba de instalación en CPU con un modelo diminuto (~1 min)
	$(UV) run arca-smoke --dry-run

bench-check: ## Valida el banco (estructura, aritmetica, evidencias); RETRIEVAL=1 mira tambien el retriever
	$(UV) run python -m agent.validate_bench $(if $(RETRIEVAL),--retrieval)

bench: ## Valida, evalua y analiza: make bench FIX=09 LABEL=auto_a [BRAINS="base rlm thinking"] [RAG_MODE=tool] [NO_TOOLS=1] [IDS="t01 t02"] [FORCE=1] [FEW_SHOT=True]
	$(if $(and $(FIX),$(LABEL)),,$(error Falta FIX o LABEL. Ejemplo: make bench FIX=09 LABEL=auto_a))
	$(if $(and $(wildcard $(BENCH_OUT).json),$(if $(FORCE),,1)),$(error Ya existe $(BENCH_OUT).json. Elige otro LABEL o usa FORCE=1))
	$(MAKE) bench-check
	$(UV) run python -m agent.evaluate --brains $(BRAINS) --rag-mode $(RAG_MODE) --max-steps $(MAX_STEPS) --few-shot $(FEW_SHOT) --out $(BENCH_OUT).json $(if $(IDS),--ids $(IDS)) $(if $(NO_TOOLS),--no-tools)
	$(UV) run python -m agent.analyze_eval --report $(BENCH_OUT).json --markdown $(BENCH_OUT).md
	@echo "Informe guardado en $(BENCH_OUT).json y $(BENCH_OUT).md"

api: ## Levanta la API en local con recarga automática
	$(UV) run uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

enunciado: ## Recompila docs/enunciado.pdf a partir del .tex
	cd docs && pdflatex -interaction=nonstopmode enunciado.tex >/dev/null
	cd docs && pdflatex -interaction=nonstopmode enunciado.tex >/dev/null
	cd docs && rm -f enunciado.aux enunciado.log enunciado.out
	@echo "docs/enunciado.pdf actualizado"

build: ## Construye la imagen Docker
	docker compose build

docker-check-gpu: ## Diagnóstico de GPU dentro del contenedor
	docker compose run --rm check-gpu

docker-smoke: ## Smoke test dentro del contenedor
	docker compose run --rm smoke

docker-api: ## API dentro del contenedor
	docker compose up api

shell: ## Shell interactiva con GPU dentro del contenedor
	docker compose run --rm train

.PHONY: help setup setup-min lock test lint format check-gpu smoke smoke-dry bench-check bench api enunciado build docker-check-gpu docker-smoke docker-api shell
