#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

with_dev=0
with_asr=0
for argument in "$@"; do
  case "$argument" in
    --dev) with_dev=1 ;;
    --asr) with_asr=1 ;;
    *) echo "Unknown option: $argument" >&2; exit 2 ;;
  esac
done

python_launcher=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 \
    && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    python_launcher="$candidate"
    break
  fi
done

if [[ -z "$python_launcher" ]]; then
  echo "[ACTION_REQUIRED] Python 3.11 or later is not installed." >&2
  if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "Use the signed Python Software Foundation installer." >&2
    echo "Official guide: https://docs.python.org/3/using/mac.html" >&2
  else
    echo "Use your operating system's supported Python package." >&2
    echo "Official guide: https://docs.python.org/3/using/unix.html" >&2
  fi
  exit 10
fi

echo "[1/6] Checking Python 3.11+"
"$python_launcher" -c 'import sys; print("      Python " + sys.version.split()[0])'

echo "[2/6] Preparing .venv"
if [[ ! -x .venv/bin/python ]]; then
  "$python_launcher" -m venv .venv
else
  echo "      Existing .venv will be reused."
fi

echo "[3/6] Installing the application"
extras=()
[[ "$with_dev" -eq 1 ]] && extras+=(dev)
[[ "$with_asr" -eq 1 ]] && extras+=(asr)
package_spec="."
if [[ "${#extras[@]}" -gt 0 ]]; then
  joined="$(IFS=,; echo "${extras[*]}")"
  package_spec=".[$joined]"
fi
./.venv/bin/python -m pip install --editable "$package_spec"

echo "[4/6] Preparing .env"
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "      Created .env. The safe API-key guide follows."
else
  echo "      Existing .env was preserved."
fi

echo "[5/6] Checking the bundled production defaults"
./.venv/bin/python -c "from video_storyboard.knowledge import load_builtin_guidance; print(load_builtin_guidance().profile.profile_id)"

echo "[6/6] Running local diagnostics (no generation API calls)"
./.venv/bin/python scripts/doctor.py

echo "Base installation finished. Open scripts/open_setup.py only if diagnostics say Google API setup is required. An existing unchanged API setup does not need to be repeated."
