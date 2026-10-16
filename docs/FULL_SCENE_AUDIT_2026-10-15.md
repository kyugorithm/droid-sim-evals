# Latest 40-scene review — 2026-10-15

Scope: visually inspected all 40 local paper-reference/render pairs. S01–S20 and U01/U04/U06/U16/U19 use assets_quality_v9; the other 15 U tasks use physical_review_u_v10. These are inspection cameras, not calibrated paper cameras or policy views. No rollout, physics test, scene edit, or new source-paper verification was performed in this audit. Small source objects remain uncertain.

Comparison sheets: `runs/scene_previews/audit_latest_20261015/{S01,S06,S11,S16,U01,U06,U11,U16}.jpg` (five tasks per sheet, paper left / current render right).

## Critical findings

- Rendering completion is not scene approval. Current evidence explicitly says physics_validation and visual_review are pending.
- S08 hat remains beside/partly hidden by the drawer, not supported on its top. S15 does not show a recognizable croissant. U19 is solid boxes instead of usable shelving; the yellow block is not visible.
- U05 cup has severe opaque/jagged-looking glass shading; removing a straw cannot be assessed from this preview alone.
- S06/S07/S10 towel geometry is still a rigid box approximation (`folded_towel_v1`: one convex box for all layers), not cloth. Texture cannot provide cloth dynamics.
- `eval/appendix_g_eval.py::_write_output_catalog` treats null success as `proxy failure`. It must show unscored separately. This is a confirmed display problem, not evidence that every numeric aggregate is wrong.
- U19 is documented as not ready but lacks a physical_evaluation gate in the manifest. Other unflagged tasks must not be assumed validated by default.
- Previous blanket exclusions of fanning/baking/frying based on absent airflow/heat require reconsideration against the intended action-level rubric. Thermal simulation is not automatically required for a robot manipulation benchmark; neither the local proxy nor the paper rubric should be invented.
- Current close-up camera auto-frames objects; it is explicitly not paper calibration. Align the table/camera first, then assess relative dimensions/poses. Do not change policy cameras merely to improve the comparison picture.

## Per-task next improvements

These are review findings, not completed fixes. Pose observations are image-space differences until camera calibration is controlled.

| Task | Finding / next check |
|---|---|
| S01 | Cup should sit slightly forward of scissors/marker; scissor and marker orientations differ; cup pattern absent. |
| S02 | Basket silhouette/rim and marker orientation differ; verify footprint aspect ratio against source. |
| S03 | Drawer shape and glove draping differ; gloves behave as one rigid pair, not two flexible gloves. |
| S04 | Marker top appears white instead of red; cup/target relative framing differs. Validate extraction clearance. |
| S05 | Basket lacks source lining; fruit spacing and basket/target relationship differ. |
| S06 | Towel remains a slab; adjust folds/size and cylinder color, then decide supported rigid vs cloth task. |
| S07 | Towel too small and rectangular; wire bowl differs in density/shape. |
| S08 | Hat not on drawer top; source top-right object absent. Fix initial support before inference. |
| S09 | Drawer cabinet structure differs; verify actual opening/closing joint, not only visual drawer displacement. |
| S10 | Pink material looks like a mesh sheet rather than fluffy fabric; towel and basket scale differ. |
| S11 | Prominent foreground pen not clearly supported by this source thumbnail; check source mapping/instruction before removing it. |
| S12 | Pen type and orientation differ; bowl facets/size and cup pattern need refinement. |
| S13 | Target rectangle is on the opposite image side of bowl; marker/pen orientations differ. |
| S14 | Bowl tilt and marker placement differ; preserve intended initial stable/tilted state. |
| S15 | Second object does not read as croissant; wrong object geometry is a priority. |
| S16 | Red fruit looks like a smooth sphere; grapes form a compact clump; pose/scale need work. |
| S17 | Same fruit issues; grape cluster should be more elongated. |
| S18 | Toaster orientation/body and visible bread state differ; verify initial object inventory against source. |
| S19 | Toaster presents broad face instead of narrow control side; material and geometry differ. |
| S20 | Validate cup insertion clearance using collision geometry, not visible rims; nested initial states remain untested. |
| U01 | Mug has pronounced flat facets; taper, handle thickness and framing differ. |
| U02 | Fan shape/orientation and burger geometry differ substantially; action-level success rubric unresolved. |
| U03 | Round upright loaf replaces long horizontal baguette; cutting physics absent. |
| U04 | Vegetable is a cluster of blobs, keyboard too thick; initial vegetable pose differs. |
| U05 | Glass shading is severely wrong; straw exposed length differs. Require true extraction/stability checks. |
| U06 | Bowl/cup relative placement differs; clarify intended cup orientation and collision/support state. |
| U07 | Small blue object differs; two yellow targets create ambiguity requiring an explicit documented rubric, not assumed paper ground truth. |
| U08 | Box-to-piece scale and camera differ; enlarged real openings still need physical passage tests without excessive clearance. |
| U09 | Tray lacks source metallic/ribbed appearance; magnetic adherence unimplemented. |
| U10 | Small objects/tool not faithfully represented; source identities unresolved. Generic improved nut assets do not prove this scene uses them. |
| U11 | Tripod/hat shapes and accessory inventory differ; hooking contacts/support unvalidated. |
| U12 | Clip is oversized and placed differently; no jaw/spring/release mechanism. |
| U13 | Small bowl is in front instead of behind; toaster orientation and plate proportions differ. Validate slot extraction. |
| U14 | Bag is flat oval instead of rectangular gathered fabric; drawstrings rigid. |
| U15 | Bread appears brown on upper face, bottle lacks source shape/label; fluid deposition absent. |
| U16 | Oven view differs; door opening and interior accessibility need validation. Croissant appearance comparatively improved. |
| U17 | Pan still looks like a shallow plate; handle/body proportions and vegetables differ. Check cooking-action rubric separately from heat simulation. |
| U18 | Fruit appears yellow instead of orange; toaster scale/orientation differs; lever joint absent. |
| U19 | Shelves replaced by solid boxes, yellow block not visible, croissant proxy poor; reconstruct before evaluation. |
| U20 | Cable is a planar rigid coil, box opening layout differs; flexible threading unimplemented. |

## Recommended order

1. Correct evaluation bookkeeping (unscored != failed; explicit validation state for every task).
2. Repair incorrect initial states/object identities: S08/S15/U03/U19 first, then S18/S19/U13/U18.
3. Fix U05 glass and common camera/table/material inconsistencies; re-review policy views as well as inspection views.
4. Validate candidate rigid tasks with settling, collision-clearance and scripted interaction tests before policy trials.
5. Develop articulated/deformable interactions separately, with explicit local benchmark semantics. Do not call them reproductions of an unrecovered paper metric.

The preview server was not listening during this audit and was restarted on 8765. No model inference was started.
