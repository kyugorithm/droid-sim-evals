#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRIVATE_DATA_ROOT="${PRIVATE_DATA_ROOT:-${HOME}/.local/share/.private}"
SIM_PYTHON="${SIM_PYTHON:-${REPO_ROOT}/.venv/bin/python}"

if [[ ! -x "$SIM_PYTHON" ]]; then
  echo "Set SIM_PYTHON or create the sim-evals virtualenv at $REPO_ROOT/.venv" >&2
  exit 2
fi

# Scene authoring only needs Isaac Sim's bundled USD Python bindings. Avoid
# starting Kit here; this keeps a scene rebuild lightweight and independent of
# any concurrently running inference server.
USD_LIBS_DIR="$("$SIM_PYTHON" -c 'import glob, site; paths = [p for root in site.getsitepackages() for p in glob.glob(root + "/isaacsim/extscache/omni.usd.libs-*")]; print(paths[0] if paths else "")')"
SIM_PYTHON_LIB_DIR="$("$SIM_PYTHON" -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR") or "")')"

ICD_DEFAULT="$REPO_ROOT/configs/nvidia_icd.example.json"
if [[ -f "$REPO_ROOT/configs/nvidia_icd.local.json" ]]; then
  ICD_DEFAULT="$REPO_ROOT/configs/nvidia_icd.local.json"
fi

# Kit can print its full child environment when a helper process fails. Keep
# credentials and unrelated shell/editor variables out of the simulator.
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
  "APPENDIX_G_STANDALONE_PXR=${APPENDIX_G_STANDALONE_PXR:-1}"
  "VK_ICD_FILENAMES=${VK_ICD_FILENAMES:-$ICD_DEFAULT}"
  "PRIVATE_DATA_ROOT=$PRIVATE_DATA_ROOT"
  "SIM_EVALS_ROOT=$REPO_ROOT"
  "LD_LIBRARY_PATH=/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:/usr/lib64:${LD_LIBRARY_PATH:-}"
  "OMNI_KIT_ACCEPT_EULA=YES"
)
if [[ -n "$USD_LIBS_DIR" && -d "$USD_LIBS_DIR/pxr" ]]; then
  clean_env+=("PYTHONPATH=$USD_LIBS_DIR")
  clean_env+=("LD_LIBRARY_PATH=$SIM_PYTHON_LIB_DIR:$USD_LIBS_DIR/bin:/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:/usr/lib64:${LD_LIBRARY_PATH:-}")
else
  echo "Could not locate Isaac Sim's omni.usd.libs extension under $SIM_PYTHON; USD authoring may require Kit." >&2
fi
for env_name in NVIDIA_VISIBLE_DEVICES NVIDIA_DRIVER_CAPABILITIES NVIDIA_REQUIRE_CUDA CUDA_VISIBLE_DEVICES CUDA_DEVICE_ORDER __GLX_VENDOR_LIBRARY_NAME; do
  if [[ -n "${!env_name:-}" ]]; then
    clean_env+=("$env_name=${!env_name}")
  fi
done

cd "$REPO_ROOT"
exec /usr/bin/env -i "${clean_env[@]}" \
  "$SIM_PYTHON" "$REPO_ROOT/scripts/build_appendix_g_scenes.py" "$@"
