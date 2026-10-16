# Appendix G unseen-task physical-validity review

> Status note (2026-10-15): the implementation status below was updated after
> this review. U02, U05, U07, U09, U12, U13, U15, U18, and U19 now have
> authored proxy mechanisms and/or evaluators, but remain unvalidated and are
> still blocked from scoring. See
> [PHYSICAL_INTERACTION_IMPLEMENTATION_V1.md](PHYSICAL_INTERACTION_IMPLEMENTATION_V1.md)
> for the current task-by-task boundary. The original review is retained as
> history, not as the latest implementation status.

This review records the user's scene/physics concerns and separates a visually
plausible USD from an interaction that the current simulator can actually
execute and score. The task photos are low-resolution; dimensions and layouts
remain local estimates, not recovered paper parameters. No DreamZero inference
or rollout was run for this revision.

## Changes made in this revision

- **U05:** Increased the glass sidewall/rim visibility and applied the glass
  tint to the bottom as well as the side surfaces. The reset pose already puts
  the straw through the cup mouth, with its lower end just above the floor;
  the previous render made the cup nearly disappear.
- **U07:** Kept the two shallow yellow vessels because both are visible in the
  task-mapped paper thumbnail. The yellow piece may go in either yellow bowl;
  the task is color-solvable but does not specify a unique yellow-bowl instance.
  Changing the left vessel into a different object would be an unverified
  reinterpretation, not a faithful correction.
- **U08:** Enlarged the sorter apertures to leave clearance around the colored
  blocks. Removed the solid hidden collision box and applied collision to the
  aperture-bearing static meshes; the old box blocked every opening.
- **U10:** Replaced the fake cylindrical nut with a six-sided ring mesh and
  gave AA-style battery proxies recognizable terminals/end caps/label bands.
  The task-mapped image still does not let us identify its tiny objects with
  confidence, so these assets must not be substituted into U10 as if confirmed.
- **U11:** Reduced the oversized tripod shoe and added a slender pointed top
  post. This improves the picture only; the hat/tripod collision and hooking
  success condition are not yet validated.
- **U13:** Changed the plate from a flat disk to a shallow concave vessel profile.
- **U15:** Laid the bread flat on the plate. Its previous 90-degree roll made
  it stand on edge.
- **U17:** Enlarged and darkened the pan body and added a clearly visible long
  metal shank and grip, so it reads as a frying pan rather than a plate.
- **U20:** Enlarged the visual and collision apertures on the box walls. The
  box is open-topped and has side holes, instead of a solid top with decorative
  dots.

## What can and cannot be scored as physical success

| Task | Physical status in the current implementation | Evaluation disposition |
|---|---|---|
| U02 — Fan the burger | There is no airflow or cooling model. Moving a fan over a burger only imitates the gesture. | Exclude from physical-success metrics. |
| U03 — Slice the bread | Rigid-body contact does not cut bread; the split-body/breakable-joint idea is not implemented. | Exclude until actual fracture/cut behavior and a stroke-plus-separation evaluator exist. |
| U05 — Remove the straw | Rigid extraction is feasible, but the existing displacement-only success rule can accept a straw that never cleared the rim. | Scene visibility fixed; do not score until whole-straw-outside and cup-stability checks are implemented and tested. |
| U07 — Match objects to bowls | Rigid sorting is feasible. The reference shows two yellow vessels, so either one is a valid yellow destination. | Keep both vessels; score only after an evaluator checks each piece is in a same-color vessel. |
| U08 — Blocks through holes | Enlarged openings now have mesh collision rather than a solid proxy. | Candidate rigid task, but excluded until a physics settling/pass-through test and a matching-hole evaluator pass. |
| U09 — Attach magnet to tray | Ordinary rigid contact has no magnetic attraction/adhesion. | Exclude unless magnetic interaction or a clearly labeled snap/constraint proxy is implemented. |
| U10 — Combine nuts and batteries | Better nut/battery proxy geometry exists, but the mapped photo shows bowls and blurred small contents; identities and intended arrangement are unresolved. | Exclude pending source-object identification and a semantic success rule. |
| U11 — Hook hat onto tripod | The pointed post is visual geometry; the hat has no validated hook loop, detailed contact, or supported-hook evaluator. | Exclude until geometry, collision, and stable support are tested. |
| U12 — Pinch clip to release papers | The binder clip handles are static geometry; there is no articulated spring/jaw or paper-release interaction. | Exclude. |
| U13 — Remove toast and place on plate | Ordinary rigid pick-and-place is feasible; the plate is now visibly concave and bread lies flat. | Candidate task, but require actual slot/plate collision and stable-placement tests before scoring. |
| U14 — Cinch drawstring | The bag and cords are visual proxies, not deformable cloth/cord dynamics. | Exclude. |
| U15 — Dispense mustard | The bead/coverage proxy is not fluid and does not model bottle squeezing or flow. | Exclude from physical-success metrics. |
| U16 — Bake croissant | Placement in an oven is possible, but heat transfer/baking state is not modeled. | Exclude if success means baking; do not count mere insertion as baking. |
| U17 — Fry vegetables | Pan/spatula contact can represent stirring, but there is no heat or frying-state model. | Exclude as “fry”; a separately named stirring proxy would be a different task. |
| U18 — Depress toaster lever | The lever is not connected to a validated joint and the evaluator does not read joint travel. | Exclude until a real joint/contact/evaluator is added. |
| U19 — Raise block to highest platform | Rigid pick-and-place is possible, but the current builder/evaluator does not provide three validated landings. | Candidate task, not ready to score. |
| U20 — Weave wire through holes | Larger apertures are real mesh openings, but the wire is not a validated flexible rope; the current rigid proxy cannot weave. | Exclude until rope dynamics and ordered hole-crossing checks are validated. |

“Exclude” means do not include the trial in a physical benchmark success rate;
it does not delete the Appendix G prompt or the visual scene. Scene image
approval is also not physics approval. All affected scenes remain unapproved
for policy inference pending the next render review and, for candidate tasks,
physics/evaluator validation.

## Evaluation safeguards and verification

The task manifest now carries `physical_evaluation` status for the reviewed
tasks. The local evaluator returns a null score and success for both
`excluded` and `pending_validation` tasks, with the reason included in the
result. This prevents gesture-only proxies (for example, bringing a magnet
near a tray) from being counted as task success. These prompts and scenes are
retained for visual review; they have not been deleted from the Appendix G
catalog.

For this revision:

- Python syntax, both edited YAML scene specifications, and `git diff --check`
  passed.
- The scene builder generated 15 layout-0 USDs for U02, U03, U05, U07–U15,
  U17, U18, and U20 under the private data directory, using the final U05
  glass/straw adjustment.
- USD structure inspection found authored collision geometry in U08 and U20.
  This verifies USD authoring only, not PhysX passage, settling, or flexible
  wire behavior.
- The Vulkan failure was fixed by installing the missing OS graphics runtime
  packages with `bash scripts/setup_graphics_runtime.sh`. The NVIDIA ICD did
  export `vk_icdGetInstanceProcAddr`; the earlier report blaming that symbol
  was incorrect. `scripts/check_nvidia_vulkan.py` passed afterward.
- All 15 high-quality policy-free previews rendered successfully (90 PNGs,
  six images per scene) and are served from
  `$PRIVATE_DATA_ROOT/runs/scene_previews/physical_review_u_v10/`. This is
  visual evidence only; visual approval and physics/evaluator validation are
  still pending.
- No DreamZero inference or policy rollout was run.
