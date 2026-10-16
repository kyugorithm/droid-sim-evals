# Task-suite implementation plan

Latest visual review (2026-10-14):
[40-task image audit and refinement plan](SCENE_FIDELITY_REVIEW_2026-10-14.md),
[Luna implementation handoff](LUNA_SCENE_REFINEMENT.md).
The v9 quality-review gallery now contains layout-0 previews for all 40 tasks.
These are visual candidates only: user approval, layout-1 review, physics
validation, and inference remain outstanding. See
[V9 asset and render refinement](V9_ASSET_REFINEMENT.md) for exact outputs and
reproduction commands.

Latest physical-interaction update (2026-10-15):
[task-by-task implementation and eligibility](PHYSICAL_INTERACTION_IMPLEMENTATION_V1.md).
Several proxy mechanisms/evaluators are now authored, but none of this update's
new mechanisms has been simulator-validated; pending/excluded tasks remain
unscored.

This is a project checklist for extending the upstream DROID simulator. The
Appendix G prompts are the first task inventory; the project may later add
other tasks and simulators. A paper prompt does not specify a complete scene,
asset, initial state, camera, or evaluator, so those must be designed and
documented rather than guessed silently.

## Scope

- [x] Prepare a local working clone of TiPToP's `droid-sim-evals` at
  `69a914cf56e0da6adafe9428de39b6ceffe9bcc6` (it is itself based on
  `arhanjain/sim-evals`).
- [x] Create the public native GitHub fork under `kyugorithm` and push the
  working branch `dreamzero-appendix-g-suite`.
- [ ] Confirm with upstream maintainers what reuse terms apply beyond GitHub's
  native fork relationship; academic intent alone does not grant redistribution
  rights to unlicensed code or asset bundles.
- [x] Record the inherited baseline: 5 DROID scenes and 51 object-layout
  variants. These are not 51 distinct language tasks.
- [x] Record 20 seen and 20 unseen Appendix G task instructions, objects,
  local environment templates, and proxy evaluator labels in
  `configs/appendix_g_tasks.yaml`.
- [x] Propose reusable scene families: tabletop, drawer, kitchen, sorting,
  office, and deformable-object interaction.
- [x] Map all 40 tasks to required objects, interaction type, fixture,
  candidate licensed asset, license/provenance, and evaluator gaps in four
  independent task-spec groups.
- [x] Convert all four task-spec groups into machine-readable scene overrides
  and generate two draft USD layouts per Appendix G instruction.
- [ ] Replace generic placeholders with task-appropriate visuals/collisions,
  then review and validate each scene before inference.
- [ ] Review the exact Appendix G figures and map their visible object/view
  evidence to scenes; do not infer missing geometry as paper fact.
- [x] Inspect the Appendix G(a) task-2 figure and map its box, marker, and
  scissors to an explicitly approximate S02 scene candidate.
- [x] Create the first S01 scene and render a policy-free three-camera preview.
- [x] Create an image-guided S02 scene and render a policy-free three-camera
  preview; the candidate still needs user visual approval.
- [ ] Get user visual approval for S01 and S02 scene candidates before policy
  inference.
- [ ] Validate collision geometry, articulation, reset determinism, and task
  success metrics per scene.
- [x] Author first explicit task-specific proxy mechanisms for cooling,
  magnetic attraction, clip release, droplet dispensing, lever travel, and
  fixed-seam bread separation; add geometric success checks where defined.
- [ ] Validate each mechanism's actual PhysX response and reset behavior before
  promoting its task to benchmark-eligible; implement or exclude unsupported
  fluid, thermal-cooking, cloth, and rope interactions.
- [x] Add a single-policy rollout runner and machine-readable per-episode JSON.
- [x] Require a non-empty MP4 for every completed policy rollout; maintain a
  per-run video gallery and a catalog under the private run-output directory.
- [ ] Add paired runs that guarantee both policies receive identical initial states.
- [ ] Add further task families only after the first scene family is stable.

## Evaluation design

The paper reports two rollouts per task with object locations changed. Our
planned two layouts are a reproducible local interpretation of that protocol,
not its undisclosed exact poses. Store a manifest for each rollout including
task ID, instruction, model/checkpoint identifier, scene revision, layout
seed, asset revisions, action interface, time/step limit, result, and video
path. Compare policies on the same scene and initial-state seed.

Scene construction/review produces PNG camera contact sheets under
`$PRIVATE_DATA_ROOT/runs/scene_previews/`; each actual DreamZero rollout
produces one MP4 under `$PRIVATE_DATA_ROOT/runs/<experiment>/<task>/<timestamp>/`
and its task/layout subdirectory. The per-run `index.html` embeds that run's
episodes; `$PRIVATE_DATA_ROOT/runs/index.html` embeds every completed rollout
video in one catalog and links to the detailed run galleries. These artifacts
remain in the private data directory and are not committed to Git.
The 40-task suite has not all been inferred yet; only finished rollout episodes
appear in the catalog.

Report scene success criteria and stage metrics independently for each task.
Do not aggregate incompatible task progress values into a paper-comparable
number unless the definition and normalization are justified. Label outcomes
as this project's simulation evaluation, not reproduced DreamZero numbers.

## First pilot

S01 is the first visual pilot because Appendix G provides a scene image with a
cup, marker, and scissor-like object. A policy-free USD candidate and a YCB
scissors mesh are included with their provenance. One complete 450-step
DreamZero rollout has exercised the end-to-end pipeline; it returned an
approximate proxy progress of 0.0 and `success=false`, not a paper result. The
scene remains a local reconstruction, not a paper-exact or validated benchmark
scene. The paper screenshot itself is not copied into this repository.

S02 (“Put the marker in the blue box”) now has two 450-step candidate rollouts.
The first video's final wrist-camera frame was judged visually successful by
the user and assistant; its old center-distance evaluator wrote `success=false`,
so `human_review.json` preserves that judgment without changing the raw result.
A later rerun used the oriented footprint/interior proxy and returned
`success=false`: the measured marker footprint was outside the box interior.
The outcome therefore remains unsettled across runs and is not a paper metric;
inspect both videos before counting S02 as validated.

S03's first automatically generated USDs were previewed as a smoke test. They
showed generic white boxes in place of recognizable gloves and a drawer, so
they were not suitable for inference. The V9 candidate instead uses the
asset-backed glove and drawer scene overrides and is included in the 40-task
quality gallery. User visual approval, physical validation, and evaluator
checks remain before any rollout should be counted.

The first parallel construction wave covered the remaining 37 task IDs (S05
was piloted separately). Its draft audit marked scenes not-ready where there
was placeholder geometry, missing interaction physics, or evaluator gaps.
V9 supersedes those drafts for visual review with updated layout-0 candidates;
it does not by itself clear the physics or evaluator gaps. U13 is a
representative asset-backed repair with verified CC0 visuals, a custom
open-slot collision shell, and a local two-stage evaluator. Its refreshed V9
render is complete; visual approval and synthetic metric checks remain before
launching DreamZero on it.
