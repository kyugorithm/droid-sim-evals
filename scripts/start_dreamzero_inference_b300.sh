#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRIVATE_DATA_ROOT="${PRIVATE_DATA_ROOT:-${HOME}/.local/share/.private}"
DREAMZERO_ROOT="${DREAMZERO_ROOT:-${PRIVATE_DATA_ROOT}/repo}"
MODEL_PATH="${MODEL_PATH:-${PRIVATE_DATA_ROOT}/molmo2}"

# B300's bundled Triton ptxas may not understand sm_103a; use CUDA 13.1's.
export TRITON_PTXAS_PATH="${TRITON_PTXAS_PATH:-/usr/local/cuda-13.1/bin/ptxas}"
export ENABLE_TENSORRT="${ENABLE_TENSORRT:-true}"
export ENABLE_DIT_CACHE="${ENABLE_DIT_CACHE:-true}"

PORT="${PORT:-8000}"
NPROC_PER_NODE="${NPROC_PER_NODE:-2}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1}"
PYTHON="$DREAMZERO_ROOT/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "DreamZero Python environment not found: $PYTHON" >&2
  exit 2
fi
if [[ ! -f "$DREAMZERO_ROOT/socket_test_optimized_AR.py" ]]; then
  echo "DreamZero inference entry point not found under $DREAMZERO_ROOT" >&2
  exit 2
fi
if [[ ! -d "$MODEL_PATH" ]]; then
  echo "Model directory not found: $MODEL_PATH" >&2
  exit 2
fi

cd "$DREAMZERO_ROOT"
exec env CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES" \
  "$PYTHON" -m torch.distributed.run \
  --standalone --nproc_per_node="$NPROC_PER_NODE" \
  "$DREAMZERO_ROOT/socket_test_optimized_AR.py" \
  --port "$PORT" \
  --enable-dit-cache \
  --model-path "$MODEL_PATH" \
  "$@"
