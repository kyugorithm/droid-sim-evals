# Appendix G unseen task scene specs — Group D (U11–U20)

These are implementation specs for the local DROID/Isaac scene proxies, not
recovered paper scene files. Appendix G provides the language instructions but
does not publish exact prop meshes, dimensions, poses, camera calibration, or
per-task success functions. Treat dimensions and placements below as local
design choices and record them as such in scene metadata.

## Image-grounded revision — 2026-10-14

The `reference_image_review` section in `scene_overrides.yaml` is the current
visual source of truth and supersedes conflicting descriptions below. Use the
labeled rows in the visual-audit comparison sheets; individual
`paper_refs/Uxx.png` basenames are not a reliable task mapping. The inspection
camera is auto-framed at 28° elevation from -Y, with screen-right +X and
screen-back +Y. It is inspection-only; policy and existing review cameras are
unchanged.

| Task | Required parent-builder template |
| --- | --- |
| U11 | `tripod_v1`, `wide_brim_hat_v1` |
| U12 | `gently_curved_paper_stack_v1`, `binder_clip_v1` |
| U13 | `toaster_with_real_slots_v1`, `bread_v7_slice`, `plate_round_v1`, `shallow_bowl_v1` |
| U14 | `drawstring_pouch_v1`, `folded_towel_v1` |
| U15 | `bread_v7_slice`, `mustard_bottle_v1`, `shallow_round_plate_v1`, `scissors` |
| U16 | `metal_toaster_oven_with_glass_door_rack_and_knobs_v1`, `croissant_v1` |
| U17 | `handled_metal_pan_v1`, `tomato_chopped_cluster_v1`, `broccoli_floret_cluster_v1`, `spatula_v1`, `paper_cup_v1` |
| U18 | `toaster_v1`, `toaster_lever_v1`, `bread_v7_slice`, `orange_round_v1` |
| U19 | `vented_fixture_v1`, `open_two_cubby_shelf_v1`, `yellow_block_v1`, `croissant_v1` |
| U20 | `open_side_hole_box_v1`, `cable_coil_v1` |

The bread agent's local CC0 assets are integrated by path in this spec:
`assets/third_party/bread_v7/bread-slice-v7.glb` and
`assets/third_party/bread_v7/bread-loaf-v7.glb`. Their source is Y-up; the
specified conversion is Y-up to Z-up. U15's broad face is placed flat by a
90° root rotation, preserving the source dimensions and aspect ratio. U03,
U13 and U18 use the loaf or slice proportions appropriate to their scene.
These are visual specifications only. None of U11–U20 is physics-validated or
inference-ready by this revision.

### Explicit renderer routing for the parent

| Task | Requested template → renderer | Current route |
| --- | --- | --- |
| U11 | `tripod_v1` → splayed legs/crossbar; `wide_brim_hat_v1` → fedora | Both are recognized aliases. `dark_olive_fedora_v1` is not; the pilot's green cube came from that fallback. |
| U12 | `gently_curved_paper_stack_v1` → bowed sheets; `binder_clip_v1` → clip and wire handles | Curved paper and clip routes are recognized. |
| U13 | `toaster_with_real_slots_v1` → slotted shell; `bread_v7_slice` → upright textured slice; `plate_round_v1` → warm plate | Toaster variant and bread importer need explicit routes; plate alias exists. Preserve source aspect ratio. |
| U14 | `drawstring_pouch_v1` → broad black fabric pouch with open mouth/free cord; `folded_towel_v1` → blue item | Pouch/towel aliases exist; image-specific cloth and loose-cord routing need explicit variants. |
| U15 | `bread_v7_slice` → flat slice via root 90° rotation; `shallow_round_plate_v1` → tan plate; `mustard_bottle_v1` → shaped bottle | Bread importer is new; plate/bottle aliases exist. No anisotropic scaling. |
| U16 | `metal_toaster_oven_with_glass_door_rack_and_knobs_v1` → oven shell, glass door, rack and controls; `croissant_v1` → crescent | Croissant alias exists; oven variant is new. |
| U17 | `handled_metal_pan_v1` → pan/handle; broad spatula visual; `tomato_chopped_cluster_v1`, `broccoli_floret_cluster_v1`, `paper_cup_v1` | Tomato, broccoli and cup aliases exist; pan and broad-spatula variants need explicit routing. |
| U18 | `toaster_v1` → compact toaster with control face toward -Y; `toaster_lever_v1` → attached raised lever; `bread_v7_slice` → vertical slice; `orange_round_v1` → orange | Toaster, lever and orange aliases exist; bread importer is new. |
| U19 | `vented_fixture_v1` → vented box; `open_two_cubby_shelf_v1` → two lower cubbies and one top; yellow block + uncertain bread-like item | Vented fixture alias exists; shelf variant is new. |
| U20 | `open_side_hole_box_v1` → open top and real side apertures; `cable_coil_v1` → loose wire/free connector | New box route delegated to Ramanujan's hole module; cable alias exists. |

Route each template key explicitly. Unsupported refs must not silently fall
through to generic primitives while being described as image-faithful.

### U11 pilot check

The existing `quality_v7_parallel_pilot/U11/layout0/reference_cam.png` shows
the new tripod structure, but the hat is still a solid green cuboid. The
current builder dispatches `wide_brim_hat_v1` to its fedora visual; it does not
recognize `dark_olive_fedora_v1`, which caused the generic fallback. The U11
override now selects the recognized alias and records the desired dark olive
appearance. The corrected final render is pending; U11 remains not ready.

## Build and preview review — 2026-10-13

The builder wrote both deterministic layouts for U11–U20 (20 USD files) to
`/home/kyuchul-lee/.local/share/.private/appendix_g_40_candidate_scenes`.
Layout-0 camera contact sheets were rendered with
`scripts/preview_appendix_g_scene_b300.sh` under
`/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_d/<TASK>/layout0/contact_sheet.png`.
These are diagnostic previews of the current builder output, not approved or
paper-faithful task scenes. **None of U11–U20 is inference-ready.** The builder
currently ignores most `asset_ref` entries and renders generic primitives;
generating a USD or a preview does not mean the task geometry, physics, or
success condition is implemented.

| Task | Preview observation / blocker | Readiness |
| --- | --- | --- |
| U11 | `U11/layout0/contact_sheet.png` — hat and tripod appear as two plain boxes; no cap opening, stand legs, or crossbar. Hang evaluator is absent. | **Not inference-ready** |
| U12 | `U12/layout0/contact_sheet.png` — paper/clip are not a recognizable paper stack and articulated binder clip; no handles/joints or release evaluator. | **Not inference-ready** |
| U13 | The earlier `U13/layout0/contact_sheet.png` is stale: it shows generic placeholders. A new candidate now imports CC0 toaster/bread/plate visuals, authors a slotted toaster shell and separate bread/plate collision proxies, honors `static: true`, and uses a task-specific staged evaluator. Must render and inspect the replacement before deciding readiness. | **Pending refreshed preview and physics review** |
| U14 | `U14/layout0/contact_sheet.png` — the bag is rendered as a single white cube; there is no open mouth, cloth, or drawcord. It is not a validated deformable body. | **Not inference-ready** |
| U15 | `U15/layout0/contact_sheet.png` — bottle is a plain light cylinder and bread a flat tan box; no actual dispensing or mustard coverage model. | **Not inference-ready** |
| U16 | `U16/layout0/contact_sheet.png` — oven is a closed white box and croissant an untextured ellipsoid; no door/rack articulation or heat/cooking model. The oven mobility tag does not make its body kinematic in the current builder. | **Not inference-ready** |
| U17 | `U17/layout0/contact_sheet.png` — skillet and spatula use local textured YCB scans; tomato/broccoli are generic light-colored shapes. The pan mobility tag does not make its body kinematic in the current builder. No frying/thermal or tool-interaction evaluator. Broccoli pose was moved from x=0.40 m to x=0.36 m in both layouts so its specified footprint clears the pan's x-boundary. | **Not inference-ready** |
| U18 | `U18/layout0/contact_sheet.png` — toaster and lever render as undifferentiated white blocks; no registered movable lever/joint or press evaluator. | **Not inference-ready** |
| U19 | Yellow block and a neutral static cuboid can use builder-supported rigid primitives, but the three-level target is not built and `place_at_height` is not evaluated. Selected as the next *scene-proxy candidate* only; no rollout should be scored yet. | **Not inference-ready** |
| U20 | `U20/layout0/contact_sheet.png` — box is a solid cuboid with no apertures and wire is a thin rigid line, not a flexible chain; no ordered threading evaluator. | **Not inference-ready** |

U13's current visual candidates are now vendored and connected to the scene
builder: the Innerscene **Toast Two** toaster (CC0 1.0; [source page](https://www.innerscene.com/tools/library/3d-parts/toast-two-small-appliance-4abfe108)) and Kenney's **Food Kit** bread/plate models (CC0 1.0; [official source](https://kenney.nl/assets/food-kit)). File hashes and adaptation notes are in `assets/third_party/innerscene/README.md` and `assets/third_party/kenney_food_kit/README.md`. The Kenney bread is a stylized model, not a photographic bread-slice scan. Import and evaluator implementation alone do not validate the rendered scene or DreamZero performance.

## Asset and licensing policy

- Existing reusable local assets: YCB Google-scanner models are CC BY 4.0;
  retain the existing notice and add per-file attribution for any newly fetched
  YCB object. Current local archives include the skillet and spatula but not
  the mustard bottle.
- Candidate Innerscene library models below are individually marked CC0 1.0;
  its terms permit copying, modification, redistribution, and commercial use.
  CC0 legal text: <https://creativecommons.org/publicdomain/zero/1.0/>.
  Keep each original source page and a short provenance notice with any vendored
  file. An asset's CC0 status does not make it mechanically articulated.
- Do not bundle an asset whose page/terms do not explicitly permit
  redistribution. Project-authored USD fallbacks described below are proposals
  until implemented and preview-checked; do not confuse the builder's current
  generic primitives with those task-specific fallbacks. Keep imported render
  meshes distinct from PhysX collision/joint geometry.
- All suggested sizes and placements are engineering starting points for the
  current tabletop proxy, not values reported by DreamZero.
- For paired layouts 0/1, preserve the same object, interaction, and target
  geometry; change only deterministic object placement within reachable space.

## U11 — “Hook the hat onto the tripod”

- **Scene and initial state:** tabletop, compact camera-style tripod, and one
  baseball cap. Use a three-legged, splayed stand with a central column and a
  clearly exposed horizontal hook/crossbar between 18–25 cm above the table.
  Start the cap flat on the table within reachable distance; point its rear
  adjustment opening/strap toward the robot and keep the brim clear of the
  tripod legs. The intended interaction is to grasp the cap and pass its rear
  opening over the crossbar, leaving the cap supported by the stand.
- **Asset/reuse:** no suitable, verified, redistributable hat-and-camera-tripod
  pair exists in the local assets. Smithsonian has a cap record with CC0
  metadata (<https://www.si.edu/es/object/3d/colorado-rockies-owners-baseball-cap:1184e2d2-33f3-490c-946c-5a79017625dd>),
  but its reuse page (<https://3d.si.edu/disclaimer>) also states
  non-commercial/educational/personal restrictions; do not use it as a
  redistributed asset. No existing local asset should be substituted just
  because its name contains “tripod.”
- **Format / redistribution:** use project-authored USD primitives/meshes for
  the stand and cap; there is no third-party asset to redistribute. Rights to
  the project-authored files follow the repository's eventual license, which
  must be set before claiming that these files are openly reusable.
  Model the cap crown and curved bill as separate visible surfaces, plus a
  collision-relevant rear loop/adjustment strap with a real opening. Make the
  crossbar round and thin enough for that loop to pass over.
- **Deterministic fallback:** low-poly sewn-cap proxy with a 25–35 mm rear loop
  and a 10–15 mm diameter stand crossbar. If the cap loop cannot be grasped
  robustly, expose a short rear fabric tab and label that simplification.
- **Evaluation gap:** current `hang_object` scoring is not implemented. Success
  must test that the cap loop encloses the crossbar and remains supported for a
  hold interval; distance between cap and tripod alone is insufficient.

## U12 — “Pinch the binder clip to release the papers”

- **Scene and initial state:** a stack of 5–8 thin sheets on the tabletop, one
  binder clip clamped over a short corner/edge, with the two wire handles
  raised and facing the robot. Leave enough sheet edge accessible to see and
  grasp. The task action is to squeeze the two handles together so the clip
  jaws open, then let the papers slide free; do not start with already-loose
  paper.
- **Asset/reuse:** Innerscene **Fold Clip – Stationery** is a close semantic
  match; its page describes a folded spring body and two pivoting wire handles:
  <https://www.innerscene.com/tools/library/3d-parts/fold-clip-stationery-86d1fa5e>.
  The page identifies the downloadable model as **GLB, 99 KB, CC0 1.0** and
  allows redistribution. No suitable loose-paper asset is currently local.
- **Interaction implementation:** use the GLB as the appearance reference or
  visual mesh, but author separate USD rigid parts for clip body and each
  handle. Add two revolute joints and a jaw-gap proxy driven by handle angle;
  represent the papers as individual thin sheets or a stack with a movable top
  sheet. Do not assume the source GLB contains a usable rig/physics joints.
- **Deterministic fallback:** project-authored black wedge body, two silver
  wire loops, and a 5-sheet rectangular stack. If separate paper contacts are
  unstable, use a single rigid stack and define release by the stack moving
  away after the clip jaw opens.
- **Evaluation gap:** `articulated_tool_interaction` is currently
  `not_implemented`. A valid task score needs both a handle/jaw-opening event
  and paper release, not just object displacement.

## U13 — “Withdraw the bread from the toaster and place on the plate”

- **Scene and initial state:** a compact two-slot toaster, one slice of bread
  partly protruding vertically from a slot, and an empty plate within one
  gripper transfer of the toaster. Keep the bread visibly graspable above the
  slot; do not start it entirely hidden inside. Success intent: bread clears
  the toaster and comes to rest on the plate.
- **Assets:**
  - **Toaster:** Innerscene **Toast Two – Small Appliance**, a recessed twin-slot
    toaster with side lever and crumb tray; **GLB, 219 KB, CC0 1.0**:
    <https://www.innerscene.com/tools/library/3d-parts/toast-two-small-appliance-4abfe108>.
  - **Bread slice:** Sketchfab **Bread, Toast, and Grilled Cheese (Game Ready)**
    states **CC0** and describes low-poly bread/toast with 1024×1024 PBR maps
    (2.1k triangles):
    <https://sketchfab.com/3d-models/bread-toast-and-grilled-cheese-game-ready-2af8c059607d430f834aa8b4ee8e95dd>.
    The model page does not specify the exact download archive format; inspect
    the downloaded package, convert the selected slice to GLB, and preserve its
    CC0 notice before bundling.
  - **Plate:** Innerscene **Sandwich plate – Original Tableware and Food Prop**,
    **GLB, 99 KB, CC0 1.0**:
    <https://www.innerscene.com/tools/library/3d-parts/sandwich-plate-original-tableware-and-food-prop-092f7ec3>.
- **Physics/fallback:** imported meshes are visual assets only unless validated.
  Provide a custom toaster collision shell with an open, slot-shaped cavity;
  fit bread dimensions to the slot and keep the plate's support surface
  collision-enabled. If the Sketchfab package cannot be normalized or is
  unsuitable at the gripper scale, use a deterministic project-authored rounded
  bread slice with a brown crust and pale center.
- **Local evaluator implementation:** U13 now uses
  `withdraw_and_place_on_plate`. At each policy step it checks approximate
  oriented-AABB clearance from the toaster, bread-center distance to the plate,
  bread-bottom gap to a configured plate surface, and a 1-second consecutive
  hold. The result is explicitly `approximate=true`; it is not a DreamZero
  paper metric. A synthetic geometry test and refreshed preview are still
  required before inference readiness can be granted.

## U14 — “Cinch the drawstring of the bag”

- **Scene and initial state:** one soft bag standing on its base with an open
  mouth, gathered rim, and two visible drawstring ends separated by at least
  4 cm. Place it stable on the table with the cord ends facing the robot. The intended
  action is to grasp and pull the two ends so the mouth circumference visibly
  contracts; a closed rigid box is not a valid stand-in.
- **Asset/reuse:** a candidate **Drawstring token bag** is available from
  3DAssets.dev:
  <https://3dassets.dev/assets/tabletop-game-components-draw-bag-0fb18c84>.
  Its asset page claims **CC0 1.0**, provides a self-contained **GLB (30.6 KB)**,
  dimensions 0.07×0.064×0.051 m, and says it is static with no animations. The
  page also labels it AI-generated; retain that provenance caveat and inspect
  its visual suitability before bundling. It is a token-sized static visual,
  not a ready cloth simulation.
- **Interaction implementation:** if the candidate passes visual review, scale
  it only as a static outer-shell reference; add a separately authored cloth
  body and two collision-visible cord ends. Prefer a small number of linked
  cord segments or a deterministic mouth-shape morph over an unvalidated
  general cloth solver.
- **Deterministic fallback:** project-authored open cloth pouch as a tapered
  mesh with a circumferential drawcord; animate/drive the cord and mouth radius
  using a fixed, documented mapping. This avoids relying on unverified AI
  provenance; redistribution rights follow the repository's eventual license.
- **Evaluation gap:** `deformable_articulation` is currently
  `not_implemented`. Measure initial/final mouth radius and require a minimum
  reduction plus cord displacement; no current proxy score can certify success.

## U15 — “Dispense the mustard onto the bread”

- **Scene and initial state:** one unbranded yellow squeeze bottle with a
  distinct nozzle, and one broad bread slice lying flat within reach. Start the
  nozzle closed/upright and the bread dry; leave the top face clear. The task
  means a visible yellow mustard stripe/dollop on the bread, not merely moving
  the bottle over it.
- **Asset/reuse:** official YCB object **005 mustard bottle**, Google-scanner
  16k textured mesh, from the [YCB Object and Model Set download page]
  (https://ycb-benchmarks.s3.amazonaws.com/index.html). The official dataset
  page declares **CC BY 4.0**, which permits redistribution with attribution:
  <https://creativecommons.org/licenses/by/4.0/>. No 005 archive is in the
  local YCB downloads yet; verify that its archive is under the per-file 25 MB
  limit before fetching. Reuse the U13 bread slice if that CC0 asset passes
  import review.
- **Format/notice:** use the Google 16k archive's textured OBJ/MTL/image files
  or convert to GLB while preserving YCB attribution and documenting changes.
  The scan may show product branding; replace/neutralize label texture in the
  derived simulation visual (document the modification) rather than implying
  the CC-BY copyright license grants separate trademark rights.
- **Deterministic fallback:** if the scan is too large, branded, or hard to
  manipulate, use a project-authored yellow squeeze-bottle mesh with a
  graspable waist and a separate nozzle. Add mustard as a fixed number of
  yellow beads/short capsules or a bread-surface decal emitted from a nozzle
  trigger; document that this is a visual dispense proxy, not fluid.
- **Evaluation gap:** `pour_or_dispense` is currently `not_implemented`; task
  success needs a minimum mustard quantity/coverage on the bread. Bottle motion
  or proximity is not enough.

## U16 — “Bake the croissant in the oven”

- **Scene and initial state:** countertop oven on the table, door hinged open and
  rack reachable, one croissant on the table just outside the opening. Keep the
  croissant small enough to fit through the opening. Start the oven in an
  explicitly documented preheated/on state if the scene claims actual baking;
  otherwise label it an insertion-only placement proxy.
- **Croissant asset:** Innerscene **Croissant**, **GLB, 5.6 MB, CC0 1.0**,
  nominal size 146×65×45 mm:
  <https://www.innerscene.com/tools/library/3d-parts/croissant-efa7fce0>.
  Redistribution/modification is permitted under CC0. This is below the
  per-download 25 MB limit.
- **Oven fixture:** author the functional oven as deterministic project USD
  geometry: hollow shell, rack, and a separately jointed drop-down door. An
  Innerscene Bake Mini visual (GLB, 261 KB, CC0 1.0) is an optional shell
  reference, but a static downloaded visual alone does not provide a working
  door/cavity:
  <https://www.innerscene.com/tools/library/3d-parts/bake-mini-small-appliance-87a969dc>.
- **Deterministic fallback:** project-authored single croissant mesh proxy and
  openable box oven with a collision-safe cavity.
- **Evaluation gap:** current `place_in_appliance` is not implemented. Even a
  geometric “inside oven” check does not prove “baked”; thermal state, cooking
  duration, and baked-state change are absent. Any insertion-only score must be
  named accordingly, not “bake success.”

## U17 — “Fry the vegetables in the pan with the spatula”

- **Scene and initial state:** YCB skillet on the tabletop, two or three pieces
  of vegetables just outside the pan, and a reachable spatula beside them.
  The opening must face up and be large enough for the vegetables. Start with
  vegetables outside so the first stage (“vegetables in pan”) is observable;
  then make the spatula reachable for contact/stirring. Avoid starting the
  target state as already complete.
- **Existing assets:** reuse local YCB 027 skillet and YCB 033 spatula from
  `assets/third_party/ycb/downloads/`; both are Google-scanner 16k archives
  under the existing YCB **CC BY 4.0** notice. For recognizable vegetables,
  Innerscene **Tomato** (**GLB, 5.2 MB, CC0 1.0**)
  <https://www.innerscene.com/tools/library/3d-parts/tomato-31f10d5c> and
  **Broccoli** (**GLB, 4.3 MB, CC0 1.0**)
  <https://www.innerscene.com/tools/library/3d-parts/broccoli-5867de0c> are
  small enough to vendor and redistribute. Use one tomato and one broccoli
  head (or deterministic smaller broccoli pieces), rather than an unidentifiable
  green sphere.
- **Physics/fallback:** use convex collision proxies sized to the imported
  scans; retain the detailed scans for rendering. If either food mesh is
  difficult to grasp, project-authored tomato/broccoli proxies with fixed
  colors and collision bounds are a deterministic fallback.
- **Evaluation gap:** `tool_interaction` is currently `not_implemented`.
  Also, “fry” requires heat/time/state-change; current scene has no cooking
  simulation. A future staged proxy may test vegetables moved into pan, spatula
  contact, then a defined stirring trajectory, but must be called a
  manipulation proxy rather than a fry-success metric.

## U18 — “Depress the lever on the toaster”

- **Scene and initial state:** reuse the U13 toaster model by identical asset
  hash/revision, but omit bread/plate as distractors. Keep the toaster fixed
  and the side lever raised, visible, and reachable. The robot must push the
  lever down, not pick up the whole appliance.
- **Asset/reuse:** same Innerscene **Toast Two** **GLB, 219 KB, CC0 1.0** as
  U13: <https://www.innerscene.com/tools/library/3d-parts/toast-two-small-appliance-4abfe108>.
  The existing local repository does not yet contain this appliance asset.
- **Interaction implementation:** do not assume the GLB's lever is separately
  articulated. Keep the imported model as visual shell; build a separate
  collision lever with a prismatic joint (or a short guided rotational joint),
  hard stops at raised/down positions, and a documented spring/detent. Bind the
  lever to the visible lever location after import inspection.
- **Deterministic fallback:** toaster shell assembled from project-authored
  boxes/cylinders plus a colored independent lever; same joint limits for all
  resets and both layouts.
- **Evaluation gap:** `articulation_target` is currently
  `not_implemented`; success should be based on lever joint position below a
  threshold for a hold interval, while confirming the toaster body stayed
  fixed. Current generic object-distance scoring cannot establish this.

## U19 — “Elevate the yellow block to the highest platform”

- **Why this is the next scene-proxy candidate:** among U11–U20 (excluding U13),
  this instruction needs only a movable colored rigid cuboid and a fixed
  support fixture. Those primitive types and per-layout center poses are
  accepted by the current builder; no download or unverified asset is needed.
  This is a prioritization for scene work, **not** a claim that U19 is ready to
  infer or score.
- **Explicit paired starts:** layout 0 places the 5 cm block at
  `[0.40, -0.12, 0.0701]` m and the 30×18×24 cm fixture at
  `[0.66, -0.12, 0.1651]` m. Layout 1 translates that pair by `[0.02, 0.20,
  0]` m: block `[0.42, 0.08, 0.0701]` m and fixture
  `[0.68, 0.08, 0.1651]` m. Both objects start supported by the table, the
  block is separated from the fixture, and the relative transfer is held
  constant. These are local deterministic poses, not paper coordinates.
- **Builder limitation:** the current builder creates the fixture as **one
  solid cuboid**. It ignores multi-level/stair semantics, so this rendered
  proxy would have a top surface but would not represent “the highest platform”
  in the task. No stair geometry is being smuggled into the spec as if the
  builder supported it.
- **Evaluator limitation:** the manifest names `place_at_height`, but the
  current evaluator does not implement it. The scene spec therefore sets the
  local metric to `not_implemented`; it does not infer success from height,
  displacement, or proximity. Readiness remains **not ready** until shared
  code builds distinct landings and a support-aware stable-placement evaluator
  is implemented and reviewed.

## U20 — “Weave the wire through the holes of the box”

- **Scene and initial state:** rigid rectangular box with at least three
  clearly visible through-holes distributed across two opposite walls; stagger
  their centers laterally/vertically so the required path is not a straight
  line. A flexible wire with a visible free tip starts outside and within
  reach. Orient the holes toward the cameras and robot. The task
  sequence is to thread the wire tip through each designated hole in order,
  leaving wire segments visibly crossing the wall apertures. Use a wire radius
  well below hole radius, with enough clearance to tolerate collision margins.
- **Asset/reuse:** no local suitable box/wire asset. Innerscene **Cable Hide**
  (**GLB, 964 KB, CC0 1.0**) is a legal candidate but has only a pair of large
  end cord openings and is not a multi-hole threading fixture:
  <https://www.innerscene.com/tools/library/3d-parts/cable-hide-cable-organizer-08a5f83f>.
  Do not relabel those two openings as a faithful multi-hole box. Author the
  fixture and flexible wire in project USD instead.
- **Model format/redistribution:** box = project-authored mesh/convex collision
  pieces; wire = deterministic chain of capsule links with documented ball
  joints (or a validated rope solver). No external asset is needed for the
  selected implementation; redistribution rights follow the repository's
  eventual license. If Cable Hide is later adopted as a visual
  distractor, its CC0 GLB may be redistributed with its source notice, but it
  does not replace the task-specific drilled box.
- **Deterministic fallback:** fixed four-hole box and 12–20 capsule-link chain;
  record the required hole IDs and detect centerline/aperture crossings in
  sequence. If articulated-wire physics is unstable, use an explicitly
  labeled kinematic wire path for a perception/replay smoke test only, not a
  policy manipulation score.
- **Evaluation gap:** `multi_waypoint_path` is currently
  `not_implemented`. Success requires ordered crossings and a final stable
  threaded configuration; object-to-box distance or wire endpoint position
  alone is inadequate.

## Build handoff / implementation order

1. Import and visually inspect the small CC0 assets first (U12 binder clip;
   U13/U18 shared toaster, plate, bread; U16 croissant; U17 vegetables). Store
   originals only under their task-specific asset folders with provenance and
   checksums; keep each download below 25 MB.
2. Build task-specific collision/articulation geometry separately from render
   meshes. Make both U13/U18 reference the exact same toaster asset revision.
3. Render policy-free multi-view previews and inspect scale, grasp access, and
   initial-state semantics before any rollout.
4. Implement or explicitly defer each listed evaluator gap before using any
   `success` field. A generated scene and a completed rollout are not evidence
   that the language task succeeded.
