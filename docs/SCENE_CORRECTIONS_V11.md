# Actual scene corrections v11 — 2026-10-15

This is a four-task incremental correction, not completion of the 40-task audit.
No DreamZero inference was run. Preview cameras and policy cameras remain separate.

## Checked work

- [x] S08: moved fedora from tabletop/inside cabinet to above left cabinet top; authored -20 degree pitch. Closed-cabinet collision now includes its supporting top instead of using an open-container proxy.
- [x] S08: inspected a newly rendered initial view and a policy-free 60-step settling preview. Hat stays on cabinet in the resulting image, but becomes upright. **The paper-like leaned pose is NOT physically reproduced yet.** Do not freeze the hat or call this a completed physical task.
- [x] S15: replaced spherical distractor with the already downloaded Poly Haven CC0 croissant, using the user's image interpretation. Kept its internal ID for compatibility. Rotated it 90 degrees in a second render to separate it from the lemon.
- [x] U03: full visual loaf no longer squeezed into half-loaf width; explicit Z-up import, 24 x 6.5 x 4.5 cm silhouette and table-height placement. It remains a stretched approximation, not the exact baguette; cutting unsupported.
- [x] U19: rotated existing shelf and vented-fixture fronts toward the camera. Moved yellow block out of overlapping distractor footprint and replaced bead-like bread with existing croissant scan. New image visibly shows shelf openings and block.
- [x] U19: added missing pending_validation evaluation gate. The shelf still has a coarse bounding-box collision; interior interaction is not validated.
- [x] Evaluation catalog: null result now shown as unscored, separately from false/true. Isolated test covers all three values and unscored count.
- [x] Initial S08 settling telemetry bug found: manifest names did not match scene override names, yielding empty pose dictionaries. Changed collection to actual registered rigid bodies and added steps_completed. Empty-body scene now raises an error.
- [ ] S08: physically supported tilted brim/crown contact matching reference; correct extra top-right prop and cabinet proportions.
- [ ] Other 36 tasks: audit findings remain open, including U05 glass, towels, lever/clip/rope mechanics, camera calibration, material/scale refinements.

## Artifacts

Served comparison page: `/corrections_v11/index.html` (paper / before / actual new render).
Generated using `scripts/publish_v11_review.py`; refuses to publish missing required images.

Data root: `/home/kyuchul-lee/.local/share/.private/`

- `appendix_g_fixes_v11/`: S08, S15 initial iteration, U03, U19 USDs.
- `appendix_g_fixes_v11b/`: revised S15 orientation.
- `runs/scene_previews/fixes_v11/`: first four scene renders, six camera images each.
- `runs/scene_previews/fixes_v11b/`: final S15 render.
- `runs/scene_previews/s08_settle_v11/`: first settling images; pose dictionaries empty, so not valid quantitative telemetry.
- `runs/scene_previews/s08_settle_v11b/`: rerun with corrected telemetry collection.

Corrected telemetry rerun succeeded: fedora center changed from
`[0.7050, 0.1600, 0.2534]` to `[0.70998, 0.15999, 0.22500]` m;
cabinet center stayed fixed. This supports the observed settling onto the top,
not preservation of the leaned initial pose or grasp-task success.

The current pod again lacked OS graphics packages. Running
`bash scripts/setup_graphics_runtime.sh` restored rendering. This is an ephemeral
system dependency issue, not a new model download or a scene-geometry failure.

Python compilation and `git diff --check` passed. Rendering success and visible
support are not substitutes for grasp/contact/evaluator validation. No commit or push.
