#!/usr/bin/env bash
set -euo pipefail
: "${PROJECT_ID:?Set project}" "${REGION:?Set region}" "${INSTANCE_CONNECTION_NAME:?Set Cloud SQL connection name}"
: "${RUNTIME_SA:?Set the dedicated runtime service account}" "${ACCOUNTS_SECRET:?Set the account JSON secret name}" "${SECRET_VERSION:?Set its numeric version}"
[[ "$SECRET_VERSION" =~ ^[1-9][0-9]*$ ]]
cd "$(dirname "$0")"
gcloud run deploy baryon-performance-pilot --source=. --project="$PROJECT_ID" --region="$REGION" \
  --service-account="$RUNTIME_SA" --add-cloudsql-instances="$INSTANCE_CONNECTION_NAME" \
  --set-secrets="/var/run/baryon/accounts.json=$ACCOUNTS_SECRET:$SECRET_VERSION" \
  --set-env-vars=BARYON_ACCOUNTS_FILE=/var/run/baryon/accounts.json \
  --no-allow-unauthenticated --max-instances=1
