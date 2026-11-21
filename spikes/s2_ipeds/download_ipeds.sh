#!/usr/bin/env bash
# S-2: download IPEDS raw files into spikes/_raw/ipeds/ (untrusted data; never executed).
# Usage: bash spikes/s2_ipeds/download_ipeds.sh spikes/_raw/ipeds
# Retries because nces.ed.gov reset/timed out connections during the spike (2026-11-21).
set -u
DEST="$1"; mkdir -p "$DEST"
FILES="C2024_A C2024_A_Dict HD2024 HD2024_Dict IC2023_AY IC2023_AY_Dict IC2024_AY IC2024_AY_Dict"
for attempt in 1 2 3 4 5 6 7 8; do
  missing=0
  for t in $FILES; do
    [ -s "$DEST/$t.zip" ] && continue
    code=$(curl -sS -A "north-research-spike" --max-time 300 -o "$DEST/$t.zip.part" -w '%{http_code}' \
      "https://nces.ed.gov/ipeds/datacenter/data/$t.zip")
    if [ "$code" = "200" ]; then mv "$DEST/$t.zip.part" "$DEST/$t.zip"; echo "ok $t"
    else rm -f "$DEST/$t.zip.part"; echo "attempt $attempt: $t -> $code"; missing=1; fi
    sleep 2
  done
  [ $missing = 0 ] && break
  sleep 150
done
ls -la "$DEST"
