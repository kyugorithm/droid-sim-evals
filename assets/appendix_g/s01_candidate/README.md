# S01 scene candidate

This policy-free Isaac Lab scene is an image-guided reconstruction for the
DreamZero Appendix G(a) task “Move the cup forward then put the marker inside
the cup.” It is a candidate, not an official DreamZero scene and not a
paper-exact reconstruction. The paper image is linked from the paper and is not
redistributed in this repository.

The scene contains procedural cup, marker, table, and backdrop geometry, plus
the YCB `037_scissors` Google 16k scan. The YCB handle material was recolored
blue to resemble the low-resolution reference. The scan's original texture is
retained. See [`../../third_party/ycb/037_scissors/NOTICE.md`](../../third_party/ycb/037_scissors/NOTICE.md)
for attribution and CC BY 4.0 terms.

The USD uses a relative reference to the YCB texture under
`assets/third_party/ycb/037_scissors/google_16k/`. Keep both paths together.
The corresponding rendered three-camera contact sheet is
[`../../previews/S01_candidate_contact_sheet.png`](../../previews/S01_candidate_contact_sheet.png).

This candidate has not yet been accepted as the benchmark's canonical S01
scene. It must be visually reviewed, then physically and task-metric validated
before policy rollouts are treated as evaluation results.
