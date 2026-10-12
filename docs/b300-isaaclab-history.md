# B300 / Isaac Lab troubleshooting history

This is a portable summary of the B300 container work recorded on 2026-10-11.
It separates observations from hypotheses so a future machine can be diagnosed
layer by layer. Raw logs are intentionally not copied here: Kit diagnostic
output can include environment details, and the original early smoke-test
commands were not retained well enough to claim an exact replay.

## Environment snapshot

- Two NVIDIA B300 SXM6 devices were visible to the container.
- Recorded NVIDIA driver: `580.126.09`.
- Recorded simulator: Isaac Sim `5.0`, headless.
- The simulation rendered RGB cameras through NVIDIA Vulkan.
- The tested Isaac Lab physics/tensor device was CPU.
- The container's Isaac Lab PyTorch build could not launch B300 `sm_103` CUDA
  physics kernels.

These facts describe one container image and driver combination. They are not a
general compatibility guarantee for B300, Isaac Sim 5.0, or another image.

## What failed, and what later worked

### 1. CUDA visibility was mistaken for graphics readiness

The GPU was visible to `nvidia-smi` and CUDA, but the preflight failed with:

```text
NVIDIA ICD is present but does not expose vkCreateInstance
```

This was a Vulkan driver/loader initialization failure. CUDA and Vulkan are
different driver interfaces: seeing a GPU in CUDA does not prove that the
Vulkan loader can initialize a graphics driver.

### 2. Adding graphics capability alone did not fix it

The Pod was recreated with:

```text
NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics
```

The same `vkCreateInstance` preflight still failed. This is an observed result:
the capability variable by itself was insufficient in that attempt. It does
not prove that the variable is unnecessary; it controls which driver libraries
are exposed to a container, but it does not necessarily select a valid Vulkan
ICD manifest or repair an incompatible host driver.

### 3. Explicit NVIDIA ICD selection passed the earlier pointer preflight

In a later run, an NVIDIA ICD JSON manifest pointing to
`libGLX_nvidia.so.0` was selected explicitly through `VK_ICD_FILENAMES`. The
then-current project check queried `vk_icdGetInstanceProcAddr` for a
`vkCreateInstance` function pointer; it did not actually create a Vulkan
instance. Historical Isaac Sim logs and rendered camera images are separate
evidence that rendering worked in that earlier run. The successful sequence
included more than one environment change, so it does not isolate one
universal root cause. A manifest is machine-specific: use the manifest and
shared-library path supplied by the current host.

The checker calls the Vulkan loader's real `vkCreateInstance`, rather than
inferring success from a function pointer. On 2026-10-12 the first check
returned `VK_ERROR_INCOMPATIBLE_DRIVER`. The NVIDIA ICD manifest and driver
libraries were present, but `libEGL.so.1` was missing from the container's OS
libraries. Installing `libegl1` made Vulkan instance creation pass. Isaac Sim
then reported missing `libGL.so.1`, `libXt.so.6`, and `libGLU.so.1`; installing
`libgl1`, `libxt6`, and `libglu1-mesa` completed the runtime dependencies.
Afterward, the S01 scene rendered successfully through all three DROID cameras
with CPU physics; the preview made zero DreamZero inference calls. No Pod
recreation or GPU change was required. In this container,
`NVIDIA_DRIVER_CAPABILITIES` was unset while Vulkan and camera rendering still
worked once the OS libraries were installed, so that variable was not the
cause of this failure.

The working Python environment and source checkout had persisted under the
home directory, while the container's OS graphics libraries had not. This is
consistent with recreating the Pod and losing packages installed in its
container layer. Keep the OS package list in the Pod image/startup setup as
well as the Python lockfile so future rebuilds restore both layers.

### 4. RGB camera rendering worked; GPU physics did not

Isaac Sim 5.0 initialized headlessly and the DROID RGB camera path rendered
images. The PyTorch CUDA physics path failed because the installed kernels did
not include the B300 `sm_103` target. Setting `SIM_DEVICE=cpu` let the
environment initialize and render while running physics/tensors on CPU.

That is why “GPU graphics works” and “GPU physics works” are not equivalent.
The Vulkan renderer and PyTorch CUDA kernels have separate initialization and
compatibility paths. The CPU fallback is a useful smoke path, not evidence of
GPU-physics performance or exact hardware parity.

### 5. DreamZero inference is another independent layer

The DreamZero model server is separate from the simulator process. In the
recorded B300 setup it used two GPUs for distributed model inference. The
simulation used CPU physics plus Vulkan camera rendering. The optional patch
at [`../patches/dreamzero-b300-compat.patch`](../patches/dreamzero-b300-compat.patch)
updates the tested DreamZero dependencies and handles the
inference-side Triton/compiler path; a CUDA 13.1 `ptxas` was also available as
the `TRITON_PTXAS_PATH` workaround when the bundled assembler rejected the
target.

`sm_103`/`sm_103a` names identify CUDA code-generation targets. A kernel built
for an unsupported target cannot necessarily be launched just because the
driver sees the GPU. `ptxas` compiles PTX into GPU machine code; fixing the
inference assembler does not rebuild the unrelated PyTorch/Isaac Lab physics
kernels.

## Why the earlier three-scene smoke run could pass

If “three smoke tests” refers to the original three-scene DROID smoke bundle,
those scenes primarily exercised simulator startup, cameras, and the inference
loop. They were not evidence that B300 CUDA physics kernels worked. The
recorded successful path used Vulkan RGB rendering with CPU physics, so a
render/control smoke run could pass while a later GPU-physics path failed on
the missing `sm_103` kernels.

The exact commands and complete logs for the earlier three-scene run are
missing. On 2026-10-12, installing the missing OS graphics libraries restored
the real Vulkan-instance check and a fresh S01 camera preview in the same B300
Pod. For future runs, record the command, device setting, exit code, Vulkan
check, and output files.

## Warnings that appeared in the successful render

The headless logs included GLFW/GLInterop and helper-process launch warnings;
they were present in a run that still produced camera images. They were
therefore non-fatal for that particular run, not universally safe to ignore.
Judge them together with the process exit code and the expected output images.
Warp/CUDA warnings also appeared in the CPU-physics path and should not be
interpreted as proof that GPU physics succeeded.

## Policy pilots were not benchmark successes

The recorded S01 “move cup forward” and U01 “orient mug handle” DreamZero runs
each reached 450 steps / 30 seconds. Both reported `progress=0.0` and
`success=false`. The runs checked that observations, cameras, policy
communication, and a stable rollout loop could execute; they did not
demonstrate task completion or reproduce paper numbers. Scene coordinates,
object models, camera calibration, and the exact DROID progress formula are
not specified by the paper, and most local scenes/evaluators remain proxies.

## Reusable diagnostic order

Run checks in this order; each answers a different question:

| Check | What a pass means | What it does not mean |
| --- | --- | --- |
| `nvidia-smi` | Driver exposes GPU/compute devices | Vulkan is initialized; PyTorch has a kernel for this GPU |
| `vulkaninfo --summary` | Vulkan loader enumerates devices | Isaac Sim RTX sensors or all rendering modes are supported |
| `check_nvidia_vulkan.py` | The selected ICD can create and destroy a Vulkan instance through the available loader | Full Isaac Sim app/camera works |
| Isaac Sim camera preview | This app/image rendered these RGB cameras | GPU physics works; benchmark score is valid |
| CUDA tensor/kernel test on the chosen device | That tested CUDA operation works | Every Isaac Lab extension has compatible kernels |
| DreamZero WebSocket inference test | Model server responds to the client | A simulator evaluator is correct or policy succeeds |

Recommended checks:

```bash
nvidia-smi --query-gpu=name,driver_version --format=csv
vulkaninfo --summary
export VK_ICD_FILENAMES=/absolute/path/to/the/host/nvidia_icd.json
python "$PROJECT_ROOT/scripts/check_nvidia_vulkan.py"
SIM_DEVICE=cpu "$PROJECT_ROOT/scripts/preview_appendix_g_scene_b300.sh" \
  --task S01 --layout 0 --scene-dir "$SCENE_DIR" --output "$RUN_DIR/preview"
```

The repository's `configs/nvidia_icd.example.json` is a template, not a
portable NVIDIA driver installation. The launch scripts currently use
`VK_ICD_FILENAMES`; the Khronos loader documents `VK_DRIVER_FILES` as its newer
replacement, but the wrapper/checker plumbing has not yet been migrated.

## Open issues

- Verify the chosen Isaac Sim release's current official GPU/driver support for
  the target machine; enumerated Vulkan extensions alone do not establish
  certification or RTX sensor support.
- The tested PyTorch/Isaac Lab stack needs a B300-compatible physics build
  before using CUDA physics on B300.
- Re-run and archive the original three smoke-test commands if their history
  can be recovered; the exact initial tests are currently unknown.
- Validate each task scene, physical interactions, and evaluator before
  reporting paired DreamZero/our-policy metrics.

## Upstream technical references

- [Isaac Sim system requirements](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html)
- [Khronos Vulkan driver manifest and discovery](https://github.com/KhronosGroup/Vulkan-Loader/blob/main/docs/LoaderDriverInterface.md)
- [Khronos Vulkan loader environment variables](https://github.com/KhronosGroup/Vulkan-Loader/blob/main/docs/LoaderInterfaceArchitecture.md)
- [CUDA compute capability, SM targets, and architecture-specific targets](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html)
- [CUDA PTX, cubins, and GPU code compatibility](https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/cuda-platform.html)
