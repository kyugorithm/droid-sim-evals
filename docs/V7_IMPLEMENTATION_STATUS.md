# v7 implementation status — 2026-10-14

## Verified

- [x] Preserve v6 outputs; write v7 separately.
- [x] Add inspection-only, inferred object-framed camera; keep original policy cameras unchanged.
- [x] Read GLB normal and packed metallic/roughness maps when present alongside base-color UV textures.
- [x] Record imported axis-scale distortion in USD (automatic aspect preservation is NOT implemented).
- [x] Add textured loaf/slice assets with provenance and generation script.
- [x] Add visual helpers for wicker/blue baskets, grapes, hat, tripod, perforated sorter and open wire box.
- [x] Reject unrecognized explicit visual templates instead of silently rendering a generic box.
- [x] Fix template routing and bread orientation integration failures.
- [x] Build all 40 layout-0 USDs successfully in `appendix_g_40_pose_matched_v7`.
- [x] Test isolated two-worker rendering on S16/U11: 30.23 / 31.01 seconds. These were integration pilots, not final visual approvals.

## Running / pending

First retry: the six candidate renders failed at Vulkan preflight, before
Isaac launched. `vkCreateInstance` returned
`VK_ERROR_INCOMPATIBLE_DRIVER`; loader debug reports that `libGLX_nvidia.so.0`
does not expose `vkCreateInstance` through `vk_icdGetInstanceProcAddr`.
The driver libraries exist in `/usr/lib64` and `nvidia-smi` sees two B300s
(driver 580.126.09), so CUDA enumeration alone is not a sufficient check.
The current GPU UUIDs differ from those in the earlier successful pilot logs.
Recovery: the previously documented `libegl1` dependency was absent in this
runtime. `sudo -n apt-get install -y libegl1` installed it and dependencies
(190 MB installed size). The real Vulkan instance check then passed. The
six-candidate, two-worker batch was restarted; inspect `batch_status.json`
and logs for current completion rather than assuming all images are ready.
Kit then also exposed missing `libGL.so.1` and `libGLU.so.1`. Restored the
full OS dependency set already documented in `docs/reproduction.md`:
`libegl1 libgl1 libvulkan1 libxt6 libglu1-mesa`. Stopped only this attempt's
batch/child process groups and restarted fresh after installation. Total added
package footprint was approximately 293 MB. Persistent `.venv` alone does not
preserve these container-level libraries across runtime replacement.

- [ ] Render representative final candidates S01/S03/S10/S16/U09/U13 into `runs/scene_previews/pose_review_quality_v7`.
- [ ] Inspect those renders against source photos; correct regressions before whole-suite rendering.
- [ ] Render/review all 40 final candidates.
- [ ] Per-task camera calibration, aspect-preserving import/collider synchronization, glass material and lighting A/B validation.
- [ ] Validate physical contacts, openings, settling, reset and task evaluators.
- [ ] Obtain user visual review before policy rollout.

The Seen/Unseen specification workers stopped at a usage limit. Their saved
changes are present, but their final self-review was not delivered. A successful
USD build is not proof of photo fidelity or valid interaction physics. No new
DreamZero inference was run. Layout 1 is not reviewed in this revision.

## Re-entry

Repository: `/home/kyuchul-lee/.local/share/.private/droid-sim-evals`.
Scene directory: `/home/kyuchul-lee/.local/share/.private/appendix_g_40_pose_matched_v7`.
Gallery: `http://localhost:18766/pose_review_quality_v7/index.html` after the first successful final-candidate render.
Batch evidence: gallery directory `batch_status.json`, per-task logs, and
`TASK/layout0/{render_evidence,batch_evidence}.json`.

`scripts/render_appendix_g_review_batch.py` uses one fresh Kit process per task,
bounded timeout, PNG validation, scene/renderer hashes and atomic publication.
It resumes matching completed jobs but refuses to overwrite stale revisions.
The image gallery labels inferred framing and pending visual/physics approval.
