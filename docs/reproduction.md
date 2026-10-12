# Setup and first scene preview

This procedure sets up the intended `droid-sim-evals` fork and renders one local
S01 scene without running policy inference. It is a setup/scene-validation
path, not a reproduction of DreamZero's published quantitative results.

## 1. Clone and install

```bash
git clone https://github.com/kyugorithm/droid-sim-evals.git
cd droid-sim-evals
uv sync
source .venv/bin/activate
```

Isaac Sim also needs graphics runtime libraries installed at the operating
system level. A new Ubuntu 24.04 Pod used for this project was missing these
even though its Python environment and NVIDIA driver libraries were present.
Install them in the container image or its startup setup:

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  libegl1 libgl1 libvulkan1 libxt6 libglu1-mesa
```

These packages are outside `.venv`; recreating a Pod can discard packages
installed only in the previous container's writable layer.

Use the Python version pinned by `.python-version` and the lockfile. NVIDIA
driver, Vulkan, Isaac Sim, and Isaac Lab compatibility is host-specific. Check
the currently installed GPU/driver before downloading large assets:

```bash
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
vulkaninfo --summary
```

The upstream simulator's DROID robot and five-scene assets are hosted
separately by TiPToP. Download their `assets.zip` from the upstream README and
extract it at the repository root. The archive is not included in this repo;
its redistribution terms have not been verified, so do not mirror it here.
NVIDIA-delivered assets are also not redistributed:

```bash
curl -fL https://tiptop-sim-assets.s3.us-east-1.amazonaws.com/assets.zip -o assets.zip
uv run python -m zipfile -e assets.zip .
```

The YCB object archives are separate, CC BY 4.0 assets. Verify their checksums
and extract the visual models with:

```bash
bash scripts/prepare_ycb_assets.sh
```

## 2. Check the host Vulkan driver

Find the NVIDIA ICD manifest provided by the container/host. Its path varies;
do not copy one from another machine.

```bash
find /usr/share/vulkan/icd.d /etc/vulkan/icd.d \
  -maxdepth 1 -type f -iname '*nvidia*.json' -print 2>/dev/null
export VK_ICD_FILENAMES=/absolute/path/to/the/host/nvidia_icd.json
python scripts/check_nvidia_vulkan.py
```

`configs/nvidia_icd.example.json` is only a template. If this host requires a
local manifest, place it at `configs/nvidia_icd.local.json`; that file is
ignored by Git. When Isaac Sim is installed, the check uses its bundled Vulkan
loader. Passing it confirms Vulkan instance creation, not full Isaac camera
rendering or CUDA physics.

## 3. Build and review S01 before inference

Keep generated USDs and renders outside Git, for example in the user's private
data directory:

```bash
export PRIVATE_DATA_ROOT="${PRIVATE_DATA_ROOT:-$HOME/.local/share/.private}"
export SIM_EVALS_ROOT="$(pwd)"
export SIM_PYTHON="$SIM_EVALS_ROOT/.venv/bin/python"
export SCENE_DIR="$PRIVATE_DATA_ROOT/appendix_g_scenes"
export RUN_DIR="$PRIVATE_DATA_ROOT/runs"
install -d -m 700 "$SCENE_DIR" "$RUN_DIR"

bash scripts/build_appendix_g_scenes_b300.sh \
  --task S01 --layout 0 --output "$SCENE_DIR"

SIM_DEVICE=cpu bash scripts/preview_appendix_g_scene_b300.sh \
  --task S01 --layout 0 --scene-dir "$SCENE_DIR" \
  --output "$RUN_DIR/scene-preview"
```

The preview saves three DROID camera images and a contact sheet; it does not
connect to DreamZero. Review the resulting `S01/layout0/contact_sheet.png`
before starting inference. The checked-in S01 USD is still a candidate, not a
canonical or paper-exact scene. Its source image is linked from the paper, not
redistributed here.

A historical run on 2026-10-11 rendered RGB cameras using Vulkan while using
CPU physics; the tested PyTorch/Isaac Lab build did not support B300 `sm_103`
physics kernels. On 2026-10-12, installing the missing OS graphics libraries
restored Vulkan initialization and the S01 three-camera preview. See the
[B300 troubleshooting history](b300-isaaclab-history.md) for the exact cause
and result.

## 4. Policy rollout comes later

Only after the scene has been visually reviewed and its task evaluator has
been validated should a policy rollout be run. For paired comparisons, both
policies must use the same task, scene revision, layout seed, camera inputs,
action interface, and episode limit. Record the policy/checkpoint identifier
and all run metadata. Do not call local proxy outcomes reproduced paper scores:
Appendix G does not publish the exact simulator assets, coordinates, camera
calibration, or DROID task-progress formula.
