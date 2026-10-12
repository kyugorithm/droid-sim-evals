# Task-suite implementation plan

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
- [ ] Map every task to required objects, interaction type, fixture, and
  candidate licensed asset.
- [ ] Review the exact Appendix G figures and map their visible object/view
  evidence to scenes; do not infer missing geometry as paper fact.
- [x] Create the first S01 scene and render a policy-free three-camera preview.
- [ ] Get user visual approval for the first S01 scene before policy inference.
- [ ] Validate collision geometry, articulation, reset determinism, and task
  success metrics per scene.
- [ ] Add paired evaluation runner and machine-readable trial results.
- [ ] Add further task families only after the first scene family is stable.

## Evaluation design

The paper reports two rollouts per task with object locations changed. Our
planned two layouts are a reproducible local interpretation of that protocol,
not its undisclosed exact poses. Store a manifest for each rollout including
task ID, instruction, model/checkpoint identifier, scene revision, layout
seed, asset revisions, action interface, time/step limit, result, and video
path. Compare policies on the same scene and initial-state seed.

Report scene success criteria and stage metrics independently for each task.
Do not aggregate incompatible task progress values into a paper-comparable
number unless the definition and normalization are justified. Label outcomes
as this project's simulation evaluation, not reproduced DreamZero numbers.

## First pilot

S01 is the first visual pilot because Appendix G provides a scene image with a
cup, marker, and scissor-like object. A policy-free USD candidate and a YCB
scissors mesh are now included with their provenance; the preview still needs
the user's visual approval. The paper screenshot itself is not copied into
this repository.
