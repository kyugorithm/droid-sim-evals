#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRIVATE_DATA_ROOT="${PRIVATE_DATA_ROOT:-${HOME}/.local/share/.private}"
SIM_ROOT="${SIM_EVALS_ROOT:-$REPO_ROOT}"
SIM_PYTHON="${SIM_PYTHON:-${SIM_ROOT}/.venv/bin/python}"
if [[ ! -x "$SIM_PYTHON" ]]; then
  echo "Set SIM_PYTHON or create the sim-evals virtualenv at $SIM_ROOT/.venv" >&2
  exit 2
fi
SITE_PACKAGES="$("$SIM_PYTHON" -c 'import site; print(site.getsitepackages()[0])')"
USD_EXT_ROOT="$(find "$SITE_PACKAGES/isaacsim/extscache" \
  -mindepth 1 -maxdepth 1 -type d -name 'omni.usd.libs-*' -print -quit)"
if [[ -z "$USD_EXT_ROOT" ]]; then
  echo "Could not locate Isaac Sim's omni.usd.libs extension under $SIM_ROOT" >&2
  exit 2
fi
PYTHON_LIB_DIR="$("$SIM_PYTHON" -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR"))')"

# Isaac Kit may include its environment in helper-process diagnostics. Start
# from a small allowlist so shell/API credentials never enter those logs.
# Scene generation only authors USD; importing the bundled pxr bindings
# directly avoids starting Kit, Vulkan, CUDA physics, and telemetry workers.
exec /usr/bin/env -i \
  HOME="${HOME:-/tmp}" \
  USER="${USER:-$(id -un)}" \
  LOGNAME="${LOGNAME:-$(id -un)}" \
  PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  LANG="C.UTF-8" \
  TERM="dumb" \
  OMP_NUM_THREADS="1" \
  OPENBLAS_NUM_THREADS="1" \
  MKL_NUM_THREADS="1" \
  PXR_WORK_THREAD_LIMIT="8" \
  APPENDIX_G_STANDALONE_PXR="1" \
  PRIVATE_DATA_ROOT="$PRIVATE_DATA_ROOT" \
  SIM_EVALS_ROOT="$SIM_ROOT" \
  PYTHONPATH="$USD_EXT_ROOT" \
  LD_LIBRARY_PATH="$USD_EXT_ROOT/bin:$PYTHON_LIB_DIR:/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:/usr/lib64" \
  "$SIM_PYTHON" \
  "$REPO_ROOT/scripts/build_appendix_g_scenes.py" "$@"
