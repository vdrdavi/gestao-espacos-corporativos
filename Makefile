# Atalhos do projeto. Roda tudo a partir da raiz.
.DEFAULT_GOAL := help

VENV := $(CURDIR)/.venv
PY   := $(VENV)/bin/python
PIP  := $(VENV)/bin/pip
API  := $(CURDIR)/apps/api
WEB  := $(CURDIR)/apps/web

.PHONY: help setup venv node api web seed cenario test test-api test-web gate lint fmt clean

help:  ## mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: venv node  ## instala todas as dependencias

venv:
	@test -d $(VENV) || python3 -m venv $(VENV)
	@$(PIP) install -q --upgrade pip
	@$(PIP) install -q -r $(API)/requirements-dev.txt
	@echo "backend pronto ($(shell $(PY) --version 2>&1))"

node:
	@cd $(WEB) && npm install --no-fund --no-audit
	@echo "frontend pronto"

api:  ## sobe a API em http://localhost:8000 (docs em /docs)
	cd $(API) && $(VENV)/bin/uvicorn app.main:app --reload --port 8000

web:  ## sobe o front em http://localhost:5173
	cd $(WEB) && npm run dev

seed:  ## recria o banco com o cenario de referencia (seed 42)
	cd $(API) && $(PY) -m seed.generate --seed 42 --reset

test: test-api test-web  ## roda toda a suite

test-api:
	cd $(API) && $(PY) -m pytest -q

test-web:
	cd $(WEB) && npm run test

gate:  ## roda so os criterios de aceitacao (o gate do CI)
	cd $(API) && $(PY) -m pytest tests/test_acceptance.py tests/test_metamorphic.py -v

lint:
	cd $(API) && $(PY) -m ruff check .
	cd $(WEB) && npm run typecheck

fmt:
	cd $(API) && $(PY) -m ruff check --fix . && $(PY) -m ruff format .

clean:
	rm -rf $(VENV) $(WEB)/node_modules $(WEB)/dist $(API)/espacos.db
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
