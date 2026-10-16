# Appendix G unseen tasks U01–U10: scene and asset specifications

These are implementation proposals for this repository's local task proxies,
not recovered DreamZero simulator scenes. Appendix G supplies the instructions,
but not the original USDs, exact props, poses, camera calibration, or per-task
success functions. All dimensions and start states below are reproducible
design choices. The image-grounded bread_v7 meshes are local CC0 inputs; no
additional third-party assets were acquired for this specification pass.

## Image-grounded revision — 2026-10-14

This section and the matching `reference_image_review` / per-task
`reference_inventory` fields in `scene_overrides.yaml` supersede earlier
visual interpretations below. The labeled rows in
`runs/scene_previews/visual_audit_20261014/U01_U05.jpg` and `U06_U10.jpg`
are the task-to-image evidence. Individual `paper_refs/Uxx.png` filenames are
not a reliable task mapping; several depict a different U task than their
basename. Use the labeled comparison row and Appendix G mapping. Inspection
uses the auto-framed reference view (28° elevation from -Y), where screen-right
is world +X and screen-back is world +Y. This is inspection only; policy and
existing review cameras remain unchanged.

| Task | Image-grounded scene requirement | Required parent-builder template |
| --- | --- | --- |
| U01 | Pink open mug; make its side handle and opening visible. Initial handle direction is uncertain in the thumbnail. | `handled_pink_mug_v1` |
| U02 | Expanded off-white radial fan to screen-left of a small teal rounded-square plate; layered burger centered on plate. | `open_folding_fan_with_radial_ribs_v1`, `rounded_square_dish_v1`, `layered_burger_v1` |
| U03 | One horizontal, visually continuous loaf at reset; knife foreground-left, blue scissors foreground-right. Bread halves stay joined at a hidden seam. | `bread_v7_loaf` (new GLB route) with one full loaf visual and hidden collision half |
| U04 | Black QWERTY keyboard spans screen-left/right; irregular green bundle behind it. Preserve uncertainty about bundle identity. | `keyboard_v1` + requested QWERTY/H-I legend atlas variant; `green_soft_bundle_v1` |
| U05 | Tall clear drinking glass with a thin, nearly upright translucent straw through its opening. | `transparent_tall_drinking_glass_v1` (new); `straw_thin_v1` |
| U06 | Blue tapered cup starts inverted over a hidden token; warm red bowl is a separate screen-left distractor. | `inverted_blue_cup_v1`, `warm_red_bowl_v1`, `hidden_yellow_token_v1` |
| U07 | Two yellow open vessels, one blue open vessel, and two loose yellow/blue block-like pieces. No green vessel; exact yellow mapping and shapes remain uncertain. | `shallow_yellow_vessel_v1`, `deeper_yellow_bowl_v1`, `blue_bowl_v1`, `uncertain_colored_block_v1` |
| U08 | Compact light-wood box with genuine top and side apertures; two separate yellow/blue pieces at screen-right. Hole shapes/count unresolved. | `multi_face_shape_sorter_box_v1`, `uncertain_yellow_block_v1`, `uncertain_blue_block_v1` |
| U09 | Shallow rectangular metal tray is upright on an edge. Keep the red cube distinct from the small gray bar-like magnet candidate. | `shallow_rectangular_tray_v1` + requested upright variant; `small_gray_metal_bar_v1`; `red_cube_v1` |
| U10 | Confirmed mapping: three open yellow/green/blue bowls; tiny contents and slim metal implement remain unidentified. The image conflicts with the instruction wording. | `three_open_colored_bowls_v1`, `uncertain_contents_cluster_v1`, `slim_metal_implement_uncertain_v1` |

The parent builder should implement these named templates and consume the
image-grounding fields. These files specify appearance and reset relationships;
they do not establish validated collision geometry, interaction physics, or
task success. No task in this group is marked inference-ready.

### Explicit renderer routing for the parent

| Task | Requested template → renderer | Current route |
| --- | --- | --- |
| U01 | `handled_pink_mug_v1` → mug body + open side handle | Recognized alias. |
| U02 | `project_open_folding_fan_v1` → radial fan; `rounded_square_dish_v1` → soft-corner dish; `burger_layered_v1` → layered burger | All current refs are recognized routes. |
| U03 | `bread_v7_loaf` → textured loaf, joined hidden cut seam | New GLB importer/visual route; keep one full-size visual only. |
| U04 | `keyboard_v1` + requested QWERTY/H-I legend atlas; `green_soft_bundle_v1` → irregular bundle | Keyboard alias and bundle route exist; legend atlas is requested functionality, not a new dispatch key. |
| U05 | `transparent_tall_drinking_glass_v1` → tall clear glass; `straw_thin_v1` → thin straw | Glass route is new; straw alias exists. |
| U06 | `paper_cup_v1` → inverted blue cup; `small_reveal_token_v1` → hidden token; `warm_red_bowl_v1` → red bowl | All current refs are recognized aliases; preserve inverted cup pose. |
| U07 | `shallow_bowl_v1` → recolored open bowls; uncertain block aliases → two loose pieces | All current refs are recognized aliases; retain two yellow vessels and one blue. |
| U08 | `multi_face_shape_sorter_box_v1` → actual top/side through-holes; uncertain block aliases → two pieces | Box route delegated to Ramanujan's hole module; aliases exist. |
| U09 | `shallow_rectangular_tray_v1` + requested upright variant; `small_gray_metal_bar_v1` + `red_cube_v1` → separate objects | Aliases exist; upright support/appearance is a requested variant. Do not substitute a magnet alias for the gray object. |
| U10 | `shallow_bowl_v1` → three open colored bowls; `small_metallic_parts_cluster_v1`; `slim_metal_implement_v1` | All current refs are recognized; contents/count and implement identity remain uncertain. |

## Provenance and license policy

- Innerscene's [Free Parts Library](https://www.innerscene.com/tools/library)
  says the library models are public domain under CC0; individual model pages
  below state the file format, size, and dimensions. CC0 legal text:
  <https://creativecommons.org/publicdomain/zero/1.0/>. Redistribution and
  modification are allowed.
- Existing YCB archives are already present in
  `assets/third_party/ycb/downloads/`. The [official YCB dataset page](https://ycb-benchmarks.s3.amazonaws.com/index.html)
  identifies the data license as CC BY 4.0:
  <https://creativecommons.org/licenses/by/4.0/>. Redistribution and
  modification are allowed with attribution and license notice; retain the
  repository's existing `assets/third_party/ycb/NOTICE.md`.
- For project-generated geometry, there is no third-party asset license. The
  repository currently has no root `LICENSE` file, so the project still needs
  to state its own redistribution terms before describing those generated
  files as openly licensed.

## Task specs

| ID | Scene and object/fixture composition | Source, license, redistribution, format | Evaluator gap / deterministic fallback |
|---|---|---|---|
| **U01 — Orient the mug so the handle is to the right** | One mug with an open cavity and side handle. The existing YCB mesh measures 11.7 × 9.3 × 8.1 cm including the handle; its cup body is about 9 cm across. Start with its measured local +X handle axis pointing to robot-left; target is robot-right (+X in the local convention). No distractors; keep the mug free to yaw on the tabletop. | Reuse local `assets/third_party/ycb/downloads/025_mug_google_16k.tgz`; YCB Google-scanner mesh, textured OBJ/MTL/PNG after extraction. CC BY 4.0; redistribution is allowed with attribution. | Current `orient_object` can measure final handle-axis alignment, but the exterior views do not yet show the handle clearly enough for reliable language grounding. Current score is a local orientation proxy, not a paper metric. |
| **U02 — Fan the burger** | The image clearly includes an open folding fan left of a layered burger on a teal rounded-square dish; this supersedes the earlier no-fan interpretation. | Use the parent-builder visual templates listed above. | Cooling/airflow and task success remain unvalidated. A motion proxy is not cooling success. |
| **U03 — Slice the bread with the knife** | A 24 × 11 × 11 cm loaf on a low cutting board, with a visible crosswise cut line; a kitchen knife lies beside it, blade oriented across that line. Bread starts intact and stationary. | Bread: [Innerscene Bread loaf](https://www.innerscene.com/tools/library/3d-parts/bread-loaf-2d5927d5), 5.0 MB GLB, CC0, redistribution allowed. Knife: local `assets/third_party/ycb/downloads/032_knife_google_16k.tgz`, Google-scanner textured OBJ/MTL/PNG after extraction, CC BY 4.0, redistribution with attribution. | Standard rigid-body physics does not cut a mesh and `tool_interaction` is unimplemented. Deterministic fallback: two loaf halves with a hidden seam and a breakable fixed joint; only release the joint after knife-tip contact and a downward stroke at the cut line. A future evaluator must require both the stroke and piece separation; otherwise mark this task unsupported. |
| **U04 — Type “hi” on the keyboard** | A stable office keyboard on the desk. Verify the source's key layout before use; if it is QWERTY, use the right-hand half and identify H/I with visible legends or contrasting keycaps. If its key topology is not QWERTY or H/I cannot be located reliably, switch to the deterministic generated QWERTY fallback. H and I must be separate pressable parts, in H-then-I order. | [Innerscene Split Key keyboard](https://www.innerscene.com/tools/library/3d-parts/split-key-split-keyboard-b5531053), 492 KB GLB, CC0, redistribution allowed. Source dimensions 37 × 16.4 × 4 cm. CC0 legal text above. | `key_sequence` is unimplemented; a static keyboard mesh cannot establish a keystroke. Deterministic fallback: generate a key grid and two independent H/I keycaps with 1–2 mm travel; record press events and accept only H→I in order. Do not infer presses from the robot merely hovering over the keys. |
| **U05 — Extricate the straw from the cup** | Two deterministic layouts place the static 9 × 9 × 10 cm open-container proxy at `[0.46, 0.022, 0.095]` and `[0.50, -0.038, 0.095]` m. A 15 cm × 6 mm × 6 mm red square-prism straw is centered over each cup and pitched 18° about Y. Geometrically, its lower end is near the cup floor and its upper end protrudes about 5.8 cm above the 14.5 cm rim; the rod's full horizontal extent fits inside the proxy's 76.5 mm opening. These are revised authored poses, not yet re-rendered or physics-checked. | The YCB mug archive `assets/third_party/ycb/downloads/025_mug_google_16k.tgz` is only a candidate reference: the builder resolves it for the object name `mug`, not this task's required object name `cup`, so the current scene remains a procedural four-wall open box. The current builder creates `straw` through its generic box branch, not a cylinder; the spec now documents that honestly. YCB is CC BY 4.0 with attribution; generated geometry's project license is unresolved. | `remove_from_container` checks only source-root displacement `>0.20 m`: it may reject a valid shorter extraction or accept lateral motion without clearing the rim. Replace it with a whole-straw-outside-rim predicate and a cup-reset-pose check. Keep inference disabled until the builder renders reviewed cup/straw geometry, reset/contact behavior is checked, and the evaluator is fixed. |
| **U06 — Reveal the object under the cup** | A handleless opaque cup placed upside down, rim nearly touching the tabletop, completely covering a contrasting small token (e.g. a 3 cm yellow disk). The token begins centered under the cup; the robot must lift or slide the cup so the token becomes visible. | No third-party model needed: reuse/adapt `scripts/build_appendix_g_scenes.py::_define_open_container()` and its project-generated cup geometry; add a separate generated token. Format: native USD geometry. No external license; project-level redistribution terms remain to be declared. | `reveal_object` is unimplemented. Deterministic fallback: keep the token fixed and score cup displacement plus visibility from the evaluation camera (or an explicit cup-footprint/token overlap test). Merely moving the token must not count as revealing it. |
| **U07 — Match the objects to their corresponding bowl** | Two yellow vessels, one blue vessel, and two loose yellow/blue block-like pieces. The piece shapes and intended choice of yellow bowl remain uncertain. Do not add a green vessel or third block. | Reuse a bowl visual family with image-grounded per-instance sizes and colors. | Exact mapping remains ambiguous and `multi_object_sort` is unimplemented. Keep inference disabled. |
| **U08 — Maneuver the blocks through the matching hole** | A horizontal shape-sorter board with three true through-openings (square, round, triangular) and three matching blocks, each slightly smaller than its opening. Put a visible catch tray below the board so passage is observable; start the blocks above the board, not already in the holes. Construct openings from rails/rings or equivalent collision-safe geometry rather than a solid board with painted hole decals. | No external asset required: extend the project's `scripts/build_appendix_g_scenes.py::_define_box()` primitive into deterministic rails/rings and blocks. Native USD format; no third-party license. | `passage_through_hole` is unimplemented. Deterministic fallback: record each block crossing the board plane and ending in the lower catch region; require all three distinct blocks. Center proximity to the board is not success. |
| **U09 — Affix the magnet to the tray** | A shallow, visibly metallic tray (about 30 × 20 cm, raised 1 cm rim) fixed on the table, plus a red/blue bar magnet initially outside the tray. Goal: place the magnet flat and fully inside the tray; treat this as manual placement on a ferromagnetic surface, not a claim to simulate magnetic forces. | Candidate visual: [Innerscene Oval Serve tray](https://www.innerscene.com/tools/library/3d-parts/oval-serve-home-accessory-62b8b712), 800 KB GLB, CC0, redistribution allowed; recolor its shallow-cavity tray material to stainless steel. Generate the bar magnet procedurally. CC0 legal text above. | Current `attach_to_surface` uses only center-to-center distance and can pass with the magnet outside the tray; no magnetic force is modeled. Deterministic fallback: test magnet footprint within tray bounds, near-zero vertical gap, and stable contact for a short hold. The evaluator currently marks this as non-approximate despite the gap; label it a placement proxy, not physical magnetism. |
| **U10 — Combine the nuts and batteries** | The task-to-image mapping is confirmed; the photograph shows three colored open bowls, small unidentified contents and a slim metal implement. | Use the image-grounded templates above; do not label ambiguous contents as nuts or batteries. | Photograph and instruction conflict. No combine interpretation or evaluator is approved; the existing root-distance rule is diagnostic only. |

## Builder/render audit (2026-10-13)

All previews below are Isaac Lab layout-0 camera snapshots, not policy runs.
Every U01–U10 task is explicitly **not inference-ready** at this revision.
User review on 2026-10-13 specifically confirmed that U02, U05, U06, and U09
still show generic/unrecognizable task props; those four remain blocked unless
the builder can render verified task assets.
The scene builder reads `dimensions_m` and `color_rgb`, but does not resolve
`asset_ref`, `material_rgb`, most `shape` declarations, or the external GLB/STEP
sources listed above. A rendered placeholder must not be treated as the named
task object. U07's colors were changed to `color_rgb`; U06's token was given a
contrasting yellow color. The missing geometry, physics, and evaluator support
remain blockers.

No new external assets were downloaded for this pass: the builder has no
task-spec importer for the listed Innerscene GLB/STEP files, so downloading
them would not change these scenes. Existing YCB assets remain under the
repository's current YCB notice and license records. There are therefore no new
asset hashes to report.

| Task | Rendered appearance / audit | Inference readiness and blocker | Layout-0 preview |
|---|---|---|---|
| U01 | Textured YCB mug. The mug was moved toward the nearer exterior camera in each paired layout; its handle is still a small, ambiguous feature in the exterior view (though more visible from the wrist camera). The measured mesh bounds and handle axis are recorded in the YAML. | **Not ready.** Do not infer until an exterior view clearly resolves the handle and initial left/right orientation. Local orientation scoring is only a proxy. | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_c/U01/U01/layout0/contact_sheet.png` |
| U02 | Small yellow-white puck, not a recognizable layered burger (user-reviewed). | **Not ready.** No burger visual is available through the builder; there is no airflow/cooling model or implemented gesture evaluator. | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_c/U02/U02/layout0/contact_sheet.png` |
| U03 | Cutting board/loaf render as plain blocks; only the knife uses a recognizable YCB visual. | **Not ready.** No bread mesh/cuttable joint, cutting dynamics, or evaluator. | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_c/U03/U03/layout0/contact_sheet.png` |
| U04 | Long white keyboard-shaped block; H/I keycaps are not visually identifiable. | **Not ready.** Keyboard asset is not loaded and no articulated key travel/ordered keystroke evaluator exists. | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_c/U04/U04/layout0/contact_sheet.png` |
| U05 | The prior user-reviewed preview shows a generic open-box cup and thin straw proxy. The YAML reset poses have since been revised to a centered 18° insertion with a 5.8 cm protrusion; that changed pose has **not** been rebuilt or rendered, so the linked PNG is stale for the current spec. | **Not ready.** The `cup` alias does not load the cited YCB mug; `straw` is rendered as a square box prism, not a round straw; and no whole-straw-outside-rim evaluator exists. | Previous preview only: `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_c/U05/U05/layout0/contact_sheet.png` |
| U06 | User-reviewed cup is a generic white procedural occluder; the yellow token is placed under it and is hidden initially. | **Not ready.** No camera-visibility/occlusion success evaluator; the generated box-container is not a recognizable household cup. | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_c/U06/U06/layout0/contact_sheet.png` |
| U07 | Refreshed preview uses red/blue/yellow colors, but bowls and items are still rectangular proxy bodies rather than open bowls and distinct objects. | **Not ready.** YCB bowl copies are not resolved from `asset_ref`; multi-object matching evaluator is unimplemented. | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_c/U07/U07/layout0/contact_sheet.png` |
| U08 | Plain frame/board proxy with no visible true apertures; blocks appear as generic cubes. | **Not ready.** No through-holes, catch-tray passage setup, or per-block crossing evaluator. | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_c/U08/U08/layout0/contact_sheet.png` |
| U09 | User-reviewed tray and magnet are generic white primitives: tray is a plain cuboid and the magnet is not visually recognizable. | **Not ready.** CC0 tray source is not loaded; there is no verified magnet asset, footprint/contact evaluator, or magnetic physics. | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_c/U09/U09/layout0/contact_sheet.png` |
| U10 | Nuts and batteries appear as tiny generic blocks. | **Not ready.** STEP asset is not loaded and the existing evaluator does not track all five objects. | `/home/kyuchul-lee/.local/share/.private/runs/scene_previews/group_c/U10/U10/layout0/contact_sheet.png` |

Both layout USDs for U01–U10 were rebuilt under
`/home/kyuchul-lee/.local/share/.private/appendix_g_40_candidate_scenes/`.
These candidates are useful for builder smoke checks only; they are not a
validated 10-task evaluation suite. The U05 YAML poses were edited after that
build, so its saved USDs and preview do not represent the current specification.
This U05 audit did not launch Isaac or run DreamZero inference.

## Build and evaluation blockers before inference

1. The current scene builder treats each configured object name as one generic
   rigid body and uses generic object slots for most unseen tasks. Add explicit
   relative placements before inference: U03 knife across the loaf's cut line,
   U05 straw inside the cup, and U06 token under the inverted cup. U07/U08/U10
   need individually addressable multi-object groups; U03/U04 need explicit
   cutting/keystroke mechanics; U06 needs an occlusion or reveal test.
2. U02 cannot measure cooling without an airflow/temperature model. A motion
   score is only a gesture proxy. U05's 20 cm displacement condition does not
   test extraction: it can reject a valid shorter pull or accept lateral
   movement without clearing the rim, so it must be replaced. U09's current
   center-distance score is not a tray-contact test.
3. Render each completed scene and review collisions/reset state before any
   DreamZero rollout. Do not count an unsupported or proxy-only evaluator as
   a reproduced paper metric.
