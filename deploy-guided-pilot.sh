#!/usr/bin/env bash
set +x
set -euo pipefail
umask 077
: "${BP_PROJECT:?Required}" "${BP_REGION:?Required}" "${BP_SERVICE:?Required}"
BP_BUILD=$(mktemp -d)
trap 'rm -rf "$BP_BUILD"' EXIT
BP_BASE=https://raw.githubusercontent.com/jhrdz47tk9-wq/-baryon-performance/ce7c80327348ec36f14f250db40b10fdb7991290/backend/performance
for BP_FILE in Dockerfile requirements-pilot.txt pilot_web.py persist.py run.py engine.py economics.py hazop.py example.json; do
  curl -fsSL "$BP_BASE/$BP_FILE" -o "$BP_BUILD/$BP_FILE"
done
chmod 644 "$BP_BUILD/"*
python3 -m py_compile "$BP_BUILD/pilot_web.py" "$BP_BUILD/run.py"
gcloud run deploy "$BP_SERVICE" --project="$BP_PROJECT" --region="$BP_REGION" --source="$BP_BUILD" --iap --no-allow-unauthenticated --quiet
gcloud run services describe "$BP_SERVICE" --project="$BP_PROJECT" --region="$BP_REGION" --format='yaml(status.latestReadyRevisionName,status.conditions,status.url)'
printf '\nFormulario desplegado. Abre la dirección del servicio y recarga el formulario.\n'
