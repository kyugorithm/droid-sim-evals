# Appendix G scene/asset specs — Group B (S11–S20)

Image-grounded specification pass: 2026-10-14. The YAML records visible
inventory, approximate relative placement, appearance, and reset relations from
the paper thumbnails. Metric dimensions and poses remain local estimates. This
pass changed specifications only: it did not rebuild scenes, render previews,
run inference, validate physics, or change evaluator readiness. Existing preview
and rollout notes below describe the earlier candidate and do not validate the
revised poses.

Status (2026-10-13): both layouts for S11-S20 were built as candidate USDs and
layout 0 was rendered from the three configured cameras. These are local
reconstructions from the public instructions, not the unpublished original
DROID scenes: exact props, poses, camera calibration, and success thresholds
are not provided in the paper. No DreamZero inference has been run for this
group. **S13 is now a candidate for a local proxy pilot** after refreshed
two-layout previews, 60-step pose-stability checks, and a task-specific
approximate evaluator; all other tasks remain blocked as listed below. This is
not an official Appendix G simulator or metric.

## Shared conventions

- Keep the same DROID robot, tabletop, and three-camera profile as the existing
  evaluation setup; make each task's named props visually unambiguous and leave
  reachable grasp space around them.
- The review camera looks from negative Y. For this qualitative scene mapping,
  screen-right is broadly +X, screen-left is broadly -X, photo-back is broadly
  +Y, and photo-front is broadly -Y. This is a project convention, not a
  calibrated camera transform or paper-published coordinate frame. Keep it when
  refining the review camera; do not treat camera-left/right as world Y.
- Keep two deterministic layouts paired across models. Move/reset props only
  enough to vary the stated initial location; do not change the task relation.
- For a procedural fallback, author the USD geometry in this task-spec area or
  the eventual scene generator and dedicate the resulting asset under CC0-1.0.
  Do not silently substitute a primitive that removes the named affordance.

## Candidate build and visual review

Build command (only these task IDs were overwritten in the shared candidate
directory):

```bash
scripts/build_appendix_g_scenes_b300.sh \
  --output /home/kyuchul-lee/.local/share/.private/appendix_g_40_candidate_scenes \
  --task S11 --task S12 --task S13 --task S14 --task S15 \
  --task S16 --task S17 --task S18 --task S19 --task S20
```

Result: 20 USD files (`s11_layout0.usd` through `s20_layout1.usd`), two layouts
per task. The builder completed successfully on CPU. It emitted known B300
Warp/CUDA and Kit helper-process warnings; these did not prevent USD creation.
Layout 0 rendered successfully for every task with the documented preview
wrapper; Vulkan `vkCreateInstance` passed. Rendering used CPU physics and GPU
Vulkan cameras; it made zero DreamZero calls.

### Inference video archive

Every DreamZero rollout episode is recorded as an MP4; results and an HTML
gallery are written alongside it. The default private archive root is
`/home/kyuchul-lee/.local/share/.private/runs` (override with
`APPENDIX_G_RUN_DIR`). A single-task run is stored as
`<root>/<TASK>/<UTC-run-id>/<TASK>/layout<N>/episode_XX.mp4`; matrix runs use
`<root>/matrix/<UTC-run-id>/...`. Each run also has `index.html`, and the root
catalog is `<root>/index.html`. Static USD preview contact sheets are images,
not rollout videos. S13 has no DreamZero rollout video yet; it is ready for a
first clearly labeled local proxy pilot, not for paper-metric claims.

| Task | Layout 0 visual review | Inference-ready? | Preview contact sheet |
|---|---|---:|---|
| S11 | Historical preview predates the updated placement and direction spec below. | **No new readiness conclusion from this spec-only pass.** | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_b/S11/layout0/contact_sheet.png` |
| S12 | Bowl is visible; the pencil renders as a small plain white bar, not the declared mechanical pencil/wood pencil. | **No — key asset is not imported; rim support is not scored.** | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_b/S12/layout0/contact_sheet.png` |
| S13 | Refreshed layout 0 and 1 previews show the textured red YCB bowl and marker. A policy-free 60-step hold leaves both object poses unchanged within numerical tolerance. The marker is small in the exterior views but visible in the wrist view. | **Candidate yes for a local proxy pilot.** The evaluator is approximate and the hidden square collision shell does not match the round bowl scan. | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/s13_refreshed/S13/layout0/contact_sheet.png` |
| S14 | Bowl and marker render as separate objects; marker is visually small. | **No — current next-to proxy does not check a non-overlapping footprint gap.** | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_b/S14/layout0/contact_sheet.png` |
| S15 | Lemon is visibly inside the open bowl after correcting its initial height to rest on the proxy floor. | **No — current scorer does not verify initial containment or final removal.** | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_b/S15/layout0/contact_sheet.png` |
| S16 | The intended grape bunch is a magenta rectangular block in this render. | **No — key object is not recognizable.** | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_b/S16/layout0/contact_sheet.png` |
| S17 | The intended green grape bunch is a green rectangular block in this render. | **No — key object is not recognizable.** | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_b/S17/layout0/contact_sheet.png` |
| S18 | Historical preview predates the revised bread asset/path and toaster-slot scene spec below. | **No — insertion affordance and matching evaluator have not been verified.** | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_b/S18/layout0/contact_sheet.png` |
| S19 | Toaster is a plain white block and the lever is only a small static-looking piece; there is no prismatic joint. | **No — articulation and joint-state evaluator are absent.** | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_b/S19/layout0/contact_sheet.png` |
| S20 | Source and receiver “cups” render as square open boxes rather than recognizable cups. | **No — assets are not imported; evaluator ignores the receiver cup set/nesting relation.** | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_b/S20/layout0/contact_sheet.png` |

### Asset integration limitation

The `asset` entries document candidate provenance and scene-spec visual paths;
they do not establish that the path was used in an earlier preview or that an
affordance is physically functional. S12/S16-S20 remain **not inference-ready**
until suitable visuals are confirmed in a rebuilt scene, affordances are visible,
and physical/evaluator support is verified. This spec now points S18 bread at
the repository's v7 GLB and records its Y-up-to-Z-up dimensions; the historical
preview above predates that edit. No render or inference was run for this pass.
Existing YCB sources and their CC-BY attribution remain as documented below.

## Task specs

### S11 — “Move the bowl on the left to the right side of the table”

- **Scene and state:** One empty, open bowl starts on the screen-left half of
  the table; the bowl is the only manipulated object. Its goal is the screen-
  right half, requiring a clear lateral translation that is
  needed. Layout 1 changes the start position but preserves left-to-right.
- **Asset/source:** Reuse local `assets/third_party/ycb/downloads/024_bowl_google_16k.tgz`.
  It is the textured OBJ/MTL/texture family from the YCB Google-scanner bowl.
  The official YCB page licenses dataset data CC BY 4.0; redistribution is
  allowed with attribution to Calli et al. and the license notice already in
  `assets/third_party/ycb/NOTICE.md`.
- **Fallback:** If the scan cannot be made dynamically stable, retain it as the
  visible bowl and use a convex-decomposition collider; if that still fails,
  make an open, rounded bowl shell in USD with floor and segmented walls, then
  release the project-authored USD under CC0-1.0.
- **Evaluation:** `move_to_region` can score displacement. The updated
  qualitative mapping is +X for screen-right. The listed local
  displacement/region checks remain project proxies, not paper metrics; the
  paper does not publish a camera transform or numeric threshold.

### S12 — “Pick up the pencil and put it on the bowl”

- **Scene and state:** A normal graspable pencil lies on the table, separate
  from a deep red-orange open bowl. A small white printed paper cup is visible
  behind the bowl as a distractor. Interpret “on the bowl” as resting across the top rim /
  top surface, not hidden inside the cavity; render-check that interpretation
  before rollout because the paper gives no success definition.
- **Asset/source:** Candidate `Draft Pencil - Writing Instrument`, Innerscene
  original, GLB, 342 KB, CC0-1.0; nominal 15.7 cm long. The source is a
  mechanical pencil, so the individual part page is the provenance/licence
  source, while suitability for an image showing a conventional wooden pencil
  remains uncertain. Bowl: reuse local YCB 024 bowl archive as in S11 (CC BY
  4.0; attribution required).
- **Fallback:** If the mechanical-pencil silhouette/material is visibly wrong,
  create a 15–18 cm hexagonal wooden pencil in USD (yellow shaft, sharpened
  tip, small eraser) and release that project-authored prop under CC0-1.0.
- **Evaluation:** The current `place_on_object` center-distance proxy can
  reward a pencil inside or merely near the bowl. It cannot verify “on.” Add a
  support/contact test: pencil is above the rim, intersects the bowl's top
  support region, and is at rest; otherwise report proxy progress, not success.

### S13 — “Pick the marker up from the table and put it in the bowl”

- **Scene and state:** A single marker lies on the tabletop beside an empty,
  open bowl. Keep the bowl stationary and its interior visible/reachable. The
  marker may protrude above the rim when placed, but its body should be inside
  the bowl footprint rather than balanced across the rim. Layout 0 places the
  pair at marker `[0.430, -0.220, 0.053]` and bowl `[0.650, 0.030, 0.085]` m;
  layout 1 moves both farther across the reachable tabletop to marker
  `[0.480, -0.300, 0.053]` (15° yaw) and bowl `[0.680, 0.120, 0.085]` m.
  Both preserve a clear, non-overlapping start. The bowl is explicitly
  `static: true`; `mobility: static_rigid` alone is not interpreted as static
  by the current builder.
- **Asset/source:** Reuse local `040_large_marker_google_16k.tgz` and
  `024_bowl_google_16k.tgz` from `assets/third_party/ycb/downloads/`. Both are
  official YCB Google-scanner assets, OBJ/MTL/textures inside TGZ, CC BY 4.0;
  redistribution is allowed with the existing YCB attribution notice.
- **Fallback:** If the marker scan is too large or poorly graspable, use a
  project-authored white cylindrical marker with a colored cap, authored in USD
  and dedicated under CC0-1.0; keep the scanned bowl and its open cavity.
- **Evaluation:** The local evaluator requires the marker's full projected box
  footprint to fit in the circular opening, at least 60% of its vertical AABB
  extent within the floor-to-rim band, an 8 mm center tolerance, a 5 mm lift
  above the rim during the episode, and a 1-second rest below 0.02 m/s. These
  are approximate project thresholds, not paper metrics or contact-sensor
  evidence. The builder still uses a square open collision shell under the
  round YCB bowl visual, so watch for the remaining physics/visual mismatch.

### S14 — “Place the bowl next to the marker”

- **Scene and state:** Empty bowl and one marker start separated on the table;
  the marker stays put and the bowl is moved to a neighboring, non-overlapping
  tabletop position. Preserve a small visible gap so “next to” is distinct
  from “on” or “touching/overlapping.”
- **Asset/source:** YCB Google-scanner 024 bowl and 040 large marker archives
  already in `assets/third_party/ycb/downloads/`; OBJ/MTL/textures, CC BY 4.0,
  redistributable with attribution as documented in `assets/third_party/ycb/NOTICE.md`.
- **Fallback:** Keep the scan visuals and use simple collision proxies. If the
  scanned bowl mesh is unsuitable as a movable rigid body, use a convex
  decomposition; otherwise use a CC0-1.0 project-authored open bowl USD.
- **Evaluation:** `place_next_to` currently uses pair-center distance and moved
  distance, so overlapping objects can be called “next to.” Require both
  objects on the tabletop plus a positive, bounded gap between their projected
  footprints. Paper-specific bounds are unknown.

### S15 — “Remove a lemon from the bowl”

- **Scene and state:** Place one lemon fully inside an open bowl at reset, with
  the fruit resting on the bowl floor. Goal: lemon grasped and left outside the
  bowl, resting on the tabletop; bowl remains in place.
- **Asset/source:** Reuse local `014_lemon_google_16k.tgz` and
  `024_bowl_google_16k.tgz`. Official YCB Google-scanner OBJ/MTL/texture assets,
  CC BY 4.0; redistribution permitted with Calli et al. attribution and the
  existing notice.
- **Fallback:** If the scanned lemon is hard to grasp or the bowl scan's cavity
  collider is incomplete, retain the YCB visuals and build a USD lemon proxy /
  open-shell bowl collider. Release project-authored geometry under CC0-1.0.
- **Evaluation:** Current `remove_from_container` only checks lemon
  displacement, not that it began inside or ended outside the bowl. Require
  initial containment and final separation/outside-tabletop-cavity; merely
  moving the lemon elsewhere in the bowl must not pass.

### S16 — “Move the grapes to the left”

- **Scene and state:** The image shows a compact green irregular bunch on the
  screen-right/front and a small dark-red round distractor on the screen-left/
  back. The distractor identity is uncertain. Treat the manipulated bunch as
  one rigid grasp target, not a field of independent rolling berries.
- **Asset/source:** `Bunch of grapes`, Innerscene original GLB, 4.5 MB,
  75 × 74 × 127 mm, CC0-1.0; downloadable and redistributable. Use its textured
  GLB visual and a convex hull/decomposition collider.
- **Fallback:** If the scan is too visually noisy or its concavity is a physics
  problem, build a compact cluster of spheres plus a short stem in USD, purple
  material, one rigid root, CC0-1.0 project asset.
- **Evaluation:** The specification maps image-left broadly to -X. This is a
  qualitative local convention; the paper does not publish a world
  calibration or metric threshold. The spec edit does not validate the scorer.

### S17 — “Move the green grapes backwards”

- **Scene and state:** Use the compact green irregular bunch on the screen-right
  side and a dark-purple/red round distractor on the screen-left. Move the target
  toward photo-back (+Y) per the broad review-camera convention. Distractor
  identity remains uncertain.
- **Asset/source:** Reuse the same Innerscene `Bunch of grapes` GLB from S16
  (4.5 MB, CC0-1.0, redistributable); recoloring/mesh conversion is permitted.
- **Fallback:** Same project-authored USD cluster fallback as S16, with green
  grapes and one rigid root, released under CC0-1.0.
- **Evaluation:** The updated local mapping treats photo-back as +Y. This is a
  qualitative proxy, not a published paper coordinate. The spec edit does not
  validate physical motion or evaluator behavior.

### S18 — “Put the bread inside the toaster”

- **Scene and state:** A toaster rests at the far side of the tabletop (+X),
  with a clearly visible, upward-accessible slot; one thin bread slice starts
  on the table in front of it. Goal is insertion into the slot, not merely
  placing bread against the toaster body.
- **Asset/source:** Use the repository's `assets/third_party/bread_v7/` slice
  GLB, derived from the Innerscene Bread loaf CC0 model. Its source Y-up bounds
  are 0.114 × 0.109 × 0.014 m; after Y-up to Z-up they are 0.114 × 0.014 ×
  0.109 m. The scene spec uses those oriented dimensions and does not route this
  slice through the Kenney upright-bread mapping. See its README and
  `provenance.json` for derivation, maps, and hashes.
  The toaster source remains the documented CC0 candidate. Both assets are
  redistributable under their stated CC0 terms.
- **Fallback:** If the v7 bread slice does not fit the visible slot at the
  stated bounds, use a compatible project-authored CC0 slice. If the toaster
  mesh has no open slot, keep it as a visible
  shell but add a matching open-slot visual/collider assembly; if it cannot be
  made visually open, replace it with a project-authored CC0 toaster shell
  with a real slot rather than scoring a fake insertion.
- **Evaluation:** Current `contain` checks only bread-to-toaster center
  distance, which can accept bread resting beside the appliance. Add a slot
  volume / orientation and stable-rest test. Report the current score as a
  proxy only until then.

### S19 — “Push the lever on the bread toaster downwards”

- **Scene and state:** Same toaster visual as S18; include one bread slice
  already partly visible in the slot to make this a “bread toaster.” Lever
  starts raised on the toaster's accessible front/side and moves vertically
  down when pressed. The bread is contextual, not the manipulated target.
- **Asset/source:** Kenney Furniture Kit toaster GLB, 15 KB, CC0-1.0, plus a
  project-authored USD lever and joint (CC0-1.0). Use the same CC0 bread source
  as S18 for the visible slice. The toaster model is redistributable, but its
  built-in lever/open-slot suitability must be checked in the preview.
- **Fallback:** If no functional visible lever exists on the downloaded mesh,
  add a distinct external handle and prismatic USD joint with a small bounded
  downward travel; preserve a stable raised reset state. Do not treat a static
  decorative lever as an articulated task asset.
- **Evaluation:** Current `articulation_target` is unimplemented and returns
  `success: null`. A scene change alone cannot score this task: read the lever
  joint coordinate, require downward travel from the raised initial state, and
  distinguish it from moving the whole toaster. Exact travel threshold remains
  a local proxy.

### S20 — “Pick up the cup from the bowl and put it in the other cups”

- **Scene and state:** At reset, one small open cup sits inside a green bowl.
  A purple cylinder is visible to the screen-left. On the screen-right, the
  blue outer receiver cup contains a smaller white receiver cup; the source cup
  is a further distinct object. The photographed nested sequence is an
  appearance/reset requirement. Exact cup variants and inner diameters remain
  unverified, so the listed size fit is a candidate estimate, not a measured
  mesh fit.
- **Asset/source:** Bowl: local YCB 024 archive. Cups: official YCB `065-*_cups`
  models (individual Google-scanner OBJ/MTL/textures; download only selected
  variants from the official object page). The YCB dataset is CC BY 4.0, so
  redistribution is allowed with Calli et al. attribution. Choose the source
  and receiver variants by measuring the actual meshes; the 065-a through -j
  labels alone do not establish that they nest.
- **Fallback:** If the selected YCB scans are not hollow/compatible, keep one
  scan as the visual reference and author open truncated-cone cups with explicit
  inner/outer walls and fitted diameters in USD. Mark generated geometry CC0-1.0.
- **Evaluation:** Current `pick_and_place` only compares object-list entries
  0 and 1 (cup and bowl); it ignores `cup_set`, so it can reward returning the
  cup to the bowl. Replace with staged checks: cup initially inside bowl;
  cup is removed from bowl; cup is finally nested inside a receiver cup. This
  task cannot be validly scored by the current proxy.

## Provenance and license URLs

- YCB object/model dataset (official object downloads and dataset license):
  <https://ycb-benchmarks.s3.amazonaws.com/index.html>
- CC BY 4.0 (YCB redistribution requires attribution):
  <https://creativecommons.org/licenses/by/4.0/>
- Innerscene CC0 library terms:
  <https://www.innerscene.com/tools/library/terms>
- Innerscene public CC0 bunch-of-grapes GLB:
  <https://www.innerscene.com/tools/library/3d-parts/bunch-of-grapes-abfcc57f>
- Innerscene public CC0 draft-pencil GLB:
  <https://www.innerscene.com/tools/library/3d-parts/draft-pencil-writing-instrument-7d3558d0>
- Innerscene public CC0 Kenney toaster GLB:
  <https://www.innerscene.com/tools/library/3d-parts/toaster-939a9f60>
- Kenney Furniture Kit (CC0): <https://kenney.nl/assets/furniture-kit>
- CC0 1.0 legal text:
  <https://creativecommons.org/publicdomain/zero/1.0/>

No binaries are added by this spec. Existing local YCB archives remain the
only bundled source files referenced above; external CC0/CC-BY assets should
be downloaded into the corresponding task-specific asset directory only after
the scene preview confirms scale, shape, and interaction suitability.

## Image-grounded open items

- S12–S15 now specify a deep red-orange bowl family. Preview the selected visual
  against the reference before treating its depth or color as matched.
- S15 includes the second larger yellow/amber object visible in the bowl. Its
  identity is intentionally unresolved; keep it as a visual distractor unless a
  clearer source establishes what it is.
- S20's receiver cup nesting and cavity dimensions need mesh inspection and a
  new preview. No physics or nesting success claim follows from this text.
- Updated relative positions and camera mapping have not been rendered.
  Historical preview images do not verify this pass.
