#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Limpieza segura por cursor; no se usa KEYS *.
# Se borra únicamente el namespace del Hito 7.
CURSOR=0
while :; do
  RESULT=$(docker compose exec -T redis redis-cli --raw SCAN "$CURSOR" MATCH 'f2030:*' COUNT 100)
  CURSOR=$(printf '%s\n' "$RESULT" | head -n1)
  KEYS=$(printf '%s\n' "$RESULT" | tail -n +2)
  if [[ -n "$KEYS" ]]; then
    while IFS= read -r key; do
      [[ -z "$key" ]] && continue
      docker compose exec -T redis redis-cli UNLINK "$key" >/dev/null
    done <<< "$KEYS"
  fi
  [[ "$CURSOR" == "0" ]] && break
done

echo "Namespace f2030:* limpiado con SCAN + UNLINK."
