#!/usr/bin/env bash
# Sync Starvo data by month over a range using the Sales-Manager API
# Default range: 2021-01 through 2025-09
# Usage:
#   ./sync_starvo_months.sh
# Optional environment variables:
#   BASE_URL  (default: http://localhost:8000)
#   PROVIDER  (default: starvo)
#   TENANT    (default: default)
#   START_Y   (default: 2021)
#   START_M   (default: 1)
#   END_Y     (default: 2025)
#   END_M     (default: 9)
#   AUTH_TOKEN (default: none)
#   SLEEP_EVERY (default: 6) - sleep after processing this many months
#   SLEEP_SECS (default: 3) - how many seconds to sleep at each pause

set -u -o pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}
PROVIDER=${PROVIDER:-starvo}
TENANT=${TENANT:-default}
START_Y=${START_Y:-2021}
START_M=${START_M:-1}
END_Y=${END_Y:-2025}
END_M=${END_M:-9}
AUTH_TOKEN=${AUTH_TOKEN:-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkeXRoaWEucHJheXVkaGF0YW1hQGludGVyb3BlcmEuY28iLCJyb2xlIjoic3VwZXJfYWRtaW4iLCJ0ZW5hbnQiOiIxIiwiZXhwIjoxNzU5NzYwNzYzLCJ0b2tlbl90eXBlIjoiYWNjZXNzIn0.Z2dGUoHvVLL3NQnj7eLrWwe3_js2MFv0Aa5Fcr93DPM}
SLEEP_EVERY=${SLEEP_EVERY:-6}
SLEEP_SECS=${SLEEP_SECS:-3}

# Validate numeric inputs
is_number() { [[ $1 =~ ^[0-9]+$ ]]; }
if ! is_number "$START_Y" || ! is_number "$START_M" || ! is_number "$END_Y" || ! is_number "$END_M"; then
  echo "ERROR: START_Y/START_M/END_Y/END_M must be integers" >&2
  exit 1
fi
if (( START_M < 1 || START_M > 12 || END_M < 1 || END_M > 12 )); then
  echo "ERROR: START_M and END_M must be within 1..12" >&2
  exit 1
fi

# Ensure BASE_URL has no trailing slash
BASE_URL=${BASE_URL%/}

AUTH_HEADER=()
if [[ -n "${AUTH_TOKEN}" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${AUTH_TOKEN}")
fi

echo "Starting monthly sync: ${START_Y}-$(printf %02d "$START_M") to ${END_Y}-$(printf %02d "$END_M")"
echo "Target: ${BASE_URL}/ev-stations-integration/data_sync_by_month (provider=${PROVIDER}, tenant=${TENANT})"

y=$START_Y
m=$START_M
failed_months=()
processed_count=0

while true; do
  ym=$(printf "%04d-%02d" "$y" "$m")
  url="${BASE_URL}/ev-stations-integration/data_sync_by_month?year_month=${ym}&provider=${PROVIDER}&tenant=${TENANT}"
  echo "\n==> Syncing ${ym}..."

  # -f: fail on HTTP errors (>=400). -S: show errors. -s: silent progress. 
  if curl -fSs -X POST "$url" "${AUTH_HEADER[@]}" -H 'accept: application/json' -d '' ; then
    echo "\nOK: ${ym}"
  else
    status=$?
    echo "\nFAIL (${status}): ${ym}" >&2
    failed_months+=("$ym")
  fi

  # Throttle: sleep after every N months processed
  processed_count=$((processed_count + 1))
  if (( SLEEP_EVERY > 0 )) && (( processed_count % SLEEP_EVERY == 0 )); then
    echo "Sleeping for ${SLEEP_SECS}s after processing ${processed_count} months..."
    sleep "${SLEEP_SECS}"
  fi

  # Exit condition (after processing END_Y/END_M)
  if [[ $y -eq $END_Y && $m -eq $END_M ]]; then
    break
  fi

  # Increment month
  m=$((m + 1))
  if (( m > 12 )); then
    m=1
    y=$((y + 1))
  fi

done

echo "\nAll months processed."
if (( ${#failed_months[@]} > 0 )); then
  echo "Some months failed:" >&2
  for f in "${failed_months[@]}"; do
    echo "  - $f" >&2
  done
  exit 2
else
  echo "All months succeeded."
fi
