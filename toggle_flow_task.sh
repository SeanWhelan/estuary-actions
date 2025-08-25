#!/usr/bin/env bash
set -euo pipefail

# Usage: ./toggle_flow_task.sh <catalog_name> [disable|enable]
NAME="${1:?catalog name is required}"
ACTION="${2:-disable}"

WORK_ROOT="/Users/sean/dev/estuary-test"
WORK_DIR="$(mktemp -d "$WORK_ROOT/flow-specs-XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT

printf 'Working directory: %s\n' "$WORK_DIR"
cd "$WORK_DIR"

flowctl catalog pull-specs --name "$NAME" --overwrite > /dev/null

# Find file that defines the full mapping (line ending with ':') for this catalog name
# Prefer the one under captures/materializations/collections; fallback to first match.
mapfile -t MATCHES < <(grep -R -n -- "$NAME:" -- '*.yaml' | sed 's/:\([0-9][0-9]*\):.*/ \1/' )
if [[ ${#MATCHES[@]} -eq 0 ]]; then
  echo "Could not locate a spec definition for '$NAME' in pulled YAML files." >&2
  exit 1
fi

FILE=""
for m in "${MATCHES[@]}"; do
  cand_file="${m% *}"
  if grep -qE '^captures:|^materializations:|^collections:' "$cand_file"; then
    FILE="$cand_file"
    break
  fi
done
# Fallback to the first candidate if none matched parent sections
[[ -n "$FILE" ]] || FILE="${MATCHES[0]% *}"

echo "Spec file: $FILE"

# Ensure 'shards' exists under the catalog spec, with correct disable setting
# We assume keys under the catalog name are indented by 4 spaces
if [[ "$ACTION" == "disable" ]]; then
  if grep -Eq '^ {4}shards:\s*$' "$FILE"; then
    if grep -Eq '^ {6}disable:\s*' "$FILE"; then
      perl -0777 -i -pe 's/^ {6}disable: .+$/      disable: true/m' "$FILE"
    else
      perl -0777 -i -pe 's/^ {4}shards:\s*$/    shards:\n      disable: true/m' "$FILE"
    fi
  else
    perl -0777 -i -pe "s/^  \Q$NAME\E:\s*\n/  $NAME:\n    shards:\n      disable: true\n/m" "$FILE"
  fi
  echo "Applied disable: true"
else
  if grep -Eq '^ {6}disable:\s*' "$FILE"; then
    perl -0777 -i -pe 's/^ {6}disable: .+$/      disable: false/m' "$FILE"
    echo "Set disable: false"
  else
    if grep -Eq '^ {4}shards:\s*$' "$FILE"; then
      perl -0777 -i -pe 's/^ {4}shards:\s*$/    shards:\n      disable: false/m' "$FILE"
    else
      perl -0777 -i -pe "s/^  \Q$NAME\E:\s*\n/  $NAME:\n    shards:\n      disable: false\n/m" "$FILE"
    fi
    echo "Inserted shards.disable: false"
  fi
fi

# Show snippet around shards
nl -ba "$FILE" | sed -n '/^\s*\([[:digit:]]\+\)\s\+\s\{0,\}.*shards:/, +5p' || true

# Validate
if flowctl catalog test --source flow.yaml >/dev/null; then
  echo "flowctl test: PASSED"
else
  echo "flowctl test: FAILED" >&2
  exit 1
fi

echo "Done. To publish, run: flowctl catalog publish --source \"$WORK_DIR/flow.yaml\""
