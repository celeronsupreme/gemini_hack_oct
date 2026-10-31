#!/usr/bin/env bash
# Runs before every merge to main and before the demo: tests, seed, every demo endpoint, web build.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/packages/contracts/py:$PWD/apps/api"
echo "▶ tests"; (cd apps/api && python3 -W ignore -m pytest -q)
echo "▶ seed + fixtures"; (cd apps/api && python3 -W ignore scripts/seed.py >/dev/null)
echo "▶ api"; pushd apps/api >/dev/null; python3 -W ignore -m uvicorn app.main:app --port 8010 >/tmp/demo_api.log 2>&1 & API_PID=$!; popd >/dev/null; sleep 4
fail=0
for p in "/health" "/risk/now" "/risk/now?at=2026-08-21T18:30:00" "/stats/hourly" "/stats/monthly" "/stats/baseline" "/triggers" "/report/clinic" "/profile" "/risk/now?mock=1" "/triggers?mock=1"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8010$p"); printf "  %-40s %s\n" "$p" "$code"; [ "$code" = "200" ] || fail=1
done
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H 'Content-Type: application/json' -d '{"transcript":"She had one at 19:15, about a minute and a half, head went to the side, just out of the shower."}' http://localhost:8010/transcripts/extract); printf "  %-40s %s\n" "POST /transcripts/extract" "$code"; [ "$code" = "200" ] || fail=1
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H 'Content-Type: application/json' -d '{}' http://localhost:8010/live/token); printf "  %-40s %s\n" "POST /live/token" "$code"; [ "$code" = "200" ] || fail=1
kill $API_PID 2>/dev/null || true
echo "▶ web build"; pnpm --filter @seizure/web build >/dev/null && echo "  ok"
[ $fail = 0 ] && echo "✅ demo-check passed" || { echo "❌ demo-check failed"; exit 1; }
