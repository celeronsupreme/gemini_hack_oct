SHELL := /bin/bash
PY := python3 -W ignore

.PHONY: setup contracts seed api web dev test demo-check clean

setup:            ## install everything (python deps + pnpm workspace)
	pip install --break-system-packages -q -e apps/api[dev] 2>/dev/null || pip install -q -e "apps/api[dev]"
	pnpm install

contracts:        ## regenerate Pydantic + TypeScript from packages/contracts/schema
	datamodel-codegen --input packages/contracts/schema/contracts.schema.json --input-file-type jsonschema --output packages/contracts/py/contracts/models.py --output-model-type pydantic_v2.BaseModel --use-standard-collections --use-union-operator --field-constraints --use-default --use-schema-description --target-python-version 3.12 --collapse-root-models
	pnpm --filter @seizure/contracts generate

seed:             ## import the demo diary and write fixtures from real numbers
	cd apps/api && $(PY) scripts/seed.py

fixtures:         ## rewrite fixtures from whatever is in the database
	cd apps/api && $(PY) scripts/seed.py --fixtures

api:              ## run the API on :8000
	cd apps/api && python3 -W ignore -m uvicorn app.main:app --reload --port 8000

web:              ## run the web app on :5173 (proxies /api -> :8000)
	pnpm --filter @seizure/web dev

dev:              ## both, with logs interleaved
	$(MAKE) -j2 api web

test:             ## engine + API tests
	cd apps/api && $(PY) -m pytest -q

demo-check:       ## everything the demo needs, end to end
	bash scripts/demo_check.sh

clean:
	rm -f apps/api/data/app.db apps/api/data/test.db
