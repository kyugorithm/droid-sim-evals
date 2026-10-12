#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRIVATE_DATA_ROOT="${PRIVATE_DATA_ROOT:-${HOME}/.local/share/.private}"
SIM_ROOT="${SIM_EVALS_ROOT:-$REPO_ROOT}"
SIM_PYTHON="${SIM_PYTHON:-${SIM_ROOT}/.venv/bin/python}"
DREAMZERO_ROOT="${DREAMZERO_ROOT:-${PRIVATE_DATA_ROOT}/repo}"
if [[ ! -x "$SIM_PYTHON" ]]; then
  echo "Set SIM_PYTHON or create the sim-evals virtualenv at $SIM_ROOT/.venv" >&2
  exit 2
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
SIM_DEVICE="${SIM_DEVICE:-cpu}"
ICD_DEFAULT="$REPO_ROOT/configs/nvidia_icd.example.json"
if [[ -f "$REPO_ROOT/configs/nvidia_icd.local.json" ]]; then
  ICD_DEFAULT="$REPO_ROOT/configs/nvidia_icd.local.json"
fi

# Kit can dump its child environment when a helper process cannot be spawned.
# Start it with a small allowlist rather than inheriting shell/editor credentials.
clean_env=(
  "HOME=${HOME:-/tmp}"
  "USER=${USER:-$(id -un)}"
  "LOGNAME=${LOGNAME:-$(id -un)}"
  "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  "LANG=${LANG:-C.UTF-8}"
  "TERM=${TERM:-dumb}"
  "OMP_NUM_THREADS=1"
  "OPENBLAS_NUM_THREADS=1"
  "MKL_NUM_THREADS=1"
  "PXR_WORK_THREAD_LIMIT=16"
  "VK_ICD_FILENAMES=${VK_ICD_FILENAMES:-$ICD_DEFAULT}"
  "PRIVATE_DATA_ROOT=$PRIVATE_DATA_ROOT"
  "SIM_EVALS_ROOT=$SIM_ROOT"
  "DREAMZERO_ROOT=$DREAMZERO_ROOT"
  "PYTHONPATH=$DREAMZERO_ROOT:$REPO_ROOT"
  "APPENDIX_G_SCENE_DIR=${APPENDIX_G_SCENE_DIR:-$PRIVATE_DATA_ROOT/appendix_g_scenes}"
  "LD_LIBRARY_PATH=/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:/usr/lib64:${LD_LIBRARY_PATH:-}"
)
for env_name in ISAAC_PATH EXP_PATH XDG_DATA_DIRS XDG_CACHE_HOME OMNI_KIT_ACCEPT_EULA; do
  if [[ -n "${!env_name:-}" ]]; then
    clean_env+=("$env_name=${!env_name}")
  fi
done
while IFS= read -r env_name; do
  case "$env_name" in
    NVIDIA_*|CUDA_*|__GL_*) clean_env+=("$env_name=${!env_name}") ;;
  esac
done < <(compgen -e)

cd "$SIM_ROOT"
exec /usr/bin/env -i "${clean_env[@]}" \
  "$SIM_PYTHON" "$REPO_ROOT/eval/appendix_g_eval.py" \
  --host "$HOST" \
  --port "$PORT" \
  --device "$SIM_DEVICE" \
  "$@"
