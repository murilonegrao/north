#!/usr/bin/env bash
# Load the official files kept locally under spikes/_raw/ (git-ignored) into the compose database.
#
#   docker compose up -d --build
#   scripts/load_local_sample.sh            # state TX
#   STATE=TX scripts/load_local_sample.sh
#
# How to download each file: docs/sources/{ipeds,dhs-stem,sevp,dapip}.md ("Local sample").
# By default the loader runs inside the app image (`docker compose run`), with the files mounted
# read-only, so the database password never leaves compose. If NORTH_DATABASE_URL is set, it
# runs on the host with uv instead (backend/ must be synced).
# Re-running is safe: a file already ingested for the same state is skipped.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW="${RAW:-$ROOT/spikes/_raw}"
STATE="${STATE:-TX}"

# Newest SEVP list by the date in its name (certified-school-list-MM-DD-YY.pdf); a plain sort
# of MM-DD-YY names puts 12-01-25 after 01-15-26.
newest_sevp() {
  local f base best="" best_key="" key
  for f in "$RAW"/sevp/certified-school-list-*.pdf; do
    [ -e "$f" ] || continue
    base="$(basename "$f")"
    if [[ "$base" =~ -([0-9]{1,2})-([0-9]{1,2})-([0-9]{2}|[0-9]{4})\.pdf$ ]]; then
      local mm="${BASH_REMATCH[1]}" dd="${BASH_REMATCH[2]}" yy="${BASH_REMATCH[3]}"
      [ "${#yy}" -eq 2 ] && yy="20$yy"
      key="$(printf '%04d%02d%02d' "$((10#$yy))" "$((10#$mm))" "$((10#$dd))")"
      if [[ -z "$best_key" || "$key" > "$best_key" ]]; then
        best="$f" best_key="$key"
      fi
    fi
  done
  printf '%s' "$best"
}

SEVP_PDF="$(newest_sevp)"
# dhs-stem-list-YYYY-MM-DD.csv: ISO dates sort correctly as text.
DHS_CSV="$(ls "$ROOT"/data/reference/dhs-stem-list-*.csv | sort | tail -n 1)"
DHS_META="${DHS_CSV%.csv}.meta.json"
# The official PDF, when kept locally, is checked against the meta's file_sha256.
DHS_URL="$(sed -n 's/.*"source_url": *"\([^"]*\)".*/\1/p' "$DHS_META" | head -n 1)"
DHS_PDF="${DHS_PDF:-$RAW/dhs_stem/$(basename "$DHS_URL")}"
for need in "$RAW/ipeds" "$RAW/dapip/extracted" "$SEVP_PDF"; do
  if [ -z "$need" ] || [ ! -e "$need" ]; then
    echo "missing: ${need:-SEVP PDF in $RAW/sevp}. See docs/sources/*.md, section 'Local sample'." >&2
    exit 1
  fi
done

if [ -n "${NORTH_DATABASE_URL:-}" ]; then
  cd "$ROOT/backend"
  pdf_arg=()
  [ -f "$DHS_PDF" ] && pdf_arg=(--dhs-pdf "$DHS_PDF")
  exec uv run python -m north.ingest.us.cli load-all --state "$STATE" \
    --ipeds-dir "$RAW/ipeds" --dhs-csv "$DHS_CSV" "${pdf_arg[@]}" --sevp-pdf "$SEVP_PDF" \
    --dapip-dir "$RAW/dapip/extracted" --isced-csv "$ROOT/data/reference/cip-isced-f.csv"
fi

cd "$ROOT"
pdf_mount=() pdf_arg=()
if [ -f "$DHS_PDF" ]; then
  pdf_mount=(-v "$DHS_PDF:/data/dhs/$(basename "$DHS_PDF"):ro")
  pdf_arg=(--dhs-pdf "/data/dhs/$(basename "$DHS_PDF")")
fi
exec docker compose run --rm --no-deps -T \
  -v "$RAW:/data/raw:ro" -v "$ROOT/data/reference:/data/reference:ro" "${pdf_mount[@]}" \
  app python -m north.ingest.us.cli load-all --state "$STATE" \
  --ipeds-dir /data/raw/ipeds \
  --dhs-csv "/data/reference/$(basename "$DHS_CSV")" "${pdf_arg[@]}" \
  --sevp-pdf "/data/raw/sevp/$(basename "$SEVP_PDF")" \
  --dapip-dir /data/raw/dapip/extracted \
  --isced-csv /data/reference/cip-isced-f.csv
