#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="1.19.2"
OUT="${1:-/mnt/data/FH6_Scenic_Navigator_v1.19.2_PORTABLE_LAUNCHER.exe}"
PY_EMBED="${FH6_PYTHON_EMBED_ZIP:-}"
ASSET="$ROOT/launcher_native/assets/python_embed.zip"
EXPECTED_PY_SHA="7d2650fd9d1b9d002d4a315d5f354247fd6a44f30517c7ef577b08f57a0fb6d9"

printf '[1/5] Building embedded Navigator payload...\n'
python "$ROOT/scripts/build_launcher_payload.py" --version "$VERSION"

printf '[2/5] Preparing Python runtime payload...\n'
if [[ -n "$PY_EMBED" ]]; then
  python - "$PY_EMBED" "$EXPECTED_PY_SHA" <<'PY'
import hashlib, pathlib, sys
p=pathlib.Path(sys.argv[1]); want=sys.argv[2].lower()
got=hashlib.sha256(p.read_bytes()).hexdigest()
if got != want:
    raise SystemExit(f'Python embed SHA-256 mismatch: {got}')
print(f'      verified {p.name}: {got}')
PY
  cp "$PY_EMBED" "$ASSET"
elif [[ -s "$ASSET" ]]; then
  python - "$ASSET" "$EXPECTED_PY_SHA" <<'PY'
import hashlib, pathlib, sys
p=pathlib.Path(sys.argv[1]); want=sys.argv[2].lower()
got=hashlib.sha256(p.read_bytes()).hexdigest()
if got != want:
    raise SystemExit(f'Existing Python embed SHA-256 mismatch: {got}')
print(f'      using verified embedded runtime: {got}')
PY
else
  echo 'ERROR: verified CPython embed runtime is required for the portable release.' >&2
  echo 'Supply FH6_PYTHON_EMBED_ZIP=python-3.13.5-embed-amd64.zip.' >&2
  exit 3
fi

printf '[3/5] Running Go launcher tests...\n'
(cd "$ROOT" && FH6_RELEASE_VERIFY=1 go test ./...)

printf '[4/5] Cross-compiling Windows GUI executable...\n'
mkdir -p "$(dirname "$OUT")"
(cd "$ROOT" && CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -trimpath -ldflags='-H=windowsgui -s -w' -o "$OUT" ./cmd/fh6-launcher)

printf '[5/5] Validating PE and hashing release...\n'
python "$ROOT/scripts/validate_portable_exe.py" "$OUT"
