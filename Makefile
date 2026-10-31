SHELL := /bin/bash
ifneq ($(filter MINGW% MSYS% CYGWIN%,$(shell uname -s)),)
# Windows: `python3` is the Microsoft Store stub, so use the API's uv venv. PY runs from apps/api.
PY := .venv/Scripts/python.exe -W ignore
CODEGEN := apps/api/.venv/Scripts/datamodel-codegen
PNPM := pnpm.cmd
SETUP_PY := cd apps/api && uv venv -q --allow-existing .venv && uv pip install -q --python .venv/Scripts/python.exe -r pyproject.toml --extra dev
else
PY := python3 -W ignore
CODEGEN := datamodel-codegen
PNPM := pnpm
SETUP_PY := pip install --break-system-packages -q -e apps/api[dev] 2>/dev/null || pip install -q -e "apps/api[dev]"
endif
export PY

.PHONY: setup contracts seed fixtures demo-data demo-data-clear api web dev test demo-check clean

setup:            ## install everything (python deps + pnpm workspace)
	$(SETUP_PY)
	$(PNPM) install

contracts:        ## regenerate Pydantic + TypeScript from packages/contracts/schema
	$(CODEGEN) --input packages/contracts/schema/contracts.schema.json --input-file-type jsonschema --output packages/contracts/py/contracts/models.py --output-model-type pydantic_v2.BaseModel --use-standard-collections --use-union-operator --field-constraints --use-default --use-schema-description --target-python-version 3.12 --collapse-root-models
	$(PNPM) --filter @seizure/contracts generate

seed:             ## import the demo diary and write fixtures from real numbers
	cd apps/api && $(PY) scripts/seed.py

demo-data:        ## synthetic seizures from her own patterns, end of the real diary -> now (SEED=42; replaces old ones)
	cd apps/api && $(PY) scripts/backfill_demo.py --seed $(or $(SEED),42)

demo-data-clear:  ## delete every synthetic (demo) seizure
	cd apps/api && $(PY) scripts/backfill_demo.py --remove

fixtures:         ## rewrite fixtures from whatever is in the database
	cd apps/api && $(PY) scripts/seed.py --fixtures

api:              ## run the API on :8000
	cd apps/api && $(PY) -m uvicorn app.main:app --reload --port 8000

web:              ## run the web app on :5173 (proxies /api -> :8000)
	$(PNPM) --filter @seizure/web dev

dev:              ## both, with logs interleaved
	$(MAKE) -j2 api web

test:             ## engine + API tests
	cd apps/api && $(PY) -m pytest -q

demo-check:       ## everything the demo needs, end to end
	bash scripts/demo_check.sh "$(PY)"

clean:
	rm -f apps/api/data/app.db apps/api/data/test.db
