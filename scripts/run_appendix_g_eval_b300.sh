#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRIVATE_DATA_ROOT="${PRIVATE_DATA_ROOT:-${HOME}/.local/share/.private}"
SIM_ROOT="${SIM_EVALS_ROOT:-$REPO_ROOT}"
SIM_PYTHON="${SIM_PYTHON:-${SIM_ROOT}/.venv/bin/python}"
DREAMZERO_ROOT="${DREAMZERO_ROOT:-${PRIVATE_DATA_ROOT}/repo}"
APPENDIX_G_FFMPEG="${APPENDIX_G_FFMPEG:-}"
if [[ -z "$APPENDIX_G_FFMPEG" && -x "$DREAMZERO_ROOT/.venv/bin/python" ]]; then
  APPENDIX_G_FFMPEG="$("$DREAMZERO_ROOT/.venv/bin/python" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())' 2>/dev/null || true)"
fi
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
if [[ -n "$APPENDIX_G_FFMPEG" ]]; then
  clean_env+=("APPENDIX_G_FFMPEG=$APPENDIX_G_FFMPEG")
fi
clean_env+=("OMNI_KIT_ACCEPT_EULA=${OMNI_KIT_ACCEPT_EULA:-YES}")
for env_name in ISAAC_PATH EXP_PATH XDG_DATA_DIRS XDG_CACHE_HOME; do
  if [[ -n "${!env_name:-}" ]]; then
    clean_env+=("$env_name=${!env_name}")
  fi
done
for env_name in NVIDIA_VISIBLE_DEVICES NVIDIA_DRIVER_CAPABILITIES NVIDIA_REQUIRE_CUDA CUDA_VISIBLE_DEVICES CUDA_DEVICE_ORDER __GLX_VENDOR_LIBRARY_NAME; do
  if [[ -n "${!env_name:-}" ]]; then
    clean_env+=("$env_name=${!env_name}")
  fi
done

cd "$SIM_ROOT"
exec /usr/bin/env -i "${clean_env[@]}" \
  "$SIM_PYTHON" "$REPO_ROOT/eval/appendix_g_eval.py" \
  --host "$HOST" \
  --port "$PORT" \
  --device "$SIM_DEVICE" \
  "$@"
