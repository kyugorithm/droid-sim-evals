# Appendix G physical-interaction implementation status

Updated 2026-10-15. This document separates scene appearance, authored
interaction models, and benchmark eligibility. The local mechanisms below are
engineering proxies, not DreamZero's undisclosed simulator or success metric.

## Implemented mechanisms

| Task | Authored mechanism | What it does not represent | Evaluation status |
|---|---|---|---|
| U02 — Fan the burger | Orientation/distance-gated lumped burger cooling state | No spatial airflow, pressure, or actual convective simulation | Pending validation; not scored yet |
| U03 — Slice bread | Fixed-seam split prototype from `CUTTING_PHYSICS_PROTOTYPE.md` | Not free cutting through arbitrary bread; the probe used a prescribed knife motion | Excluded from benchmark scoring |
| U05 — Remove straw | Whole-straw/rim-clearance and cup-displacement predicate | Proxy dimensions and long-axis convention still need simulator confirmation | Pending validation |
| U07 — Sort into bowls | Color-to-vessel footprint, height, and low-speed predicate; either yellow vessel accepted | Simplified bowl interior; no mesh-volume/contact validation yet | Pending validation |
| U09 — Attach magnet | Bounded distance-dependent attraction toward the tray surface | No magnetic field, material response, or real adhesion | Pending validation |
| U12 — Pinch clip | Two revolute handle bodies; paper fixed joint releases after both handles close | No calibrated spring, detailed clip flexure, or validated finger/contact response | Pending validation |
| U13 — Toast onto plate | Toaster-clearance, plate-support, and hold-time geometric predicate | Simplified collision/concave support geometry | Pending validation |
| U15 — Dispense mustard | Sixteen individually simulated rigid droplets released by an inverted, aligned nozzle | No squeeze mechanics, continuous/viscous fluid, splashing, or spreading | Pending validation |
| U18 — Depress toaster lever | Limited prismatic slider with a return drive; evaluator checks downward travel and toaster stability | No measured hardware force curve or contact validation | Pending validation |
| U19 — Raise block | Highest-platform-frame support predicate plus a 0.5 s low-speed hold | Proxy block/platform dimensions; support contact not yet validated | Pending validation |

`pending_validation` and `excluded` tasks intentionally return a null success
score. Adding a scene mechanism alone does not make a task benchmark-eligible.

## Still excluded / not implemented as physical effects

| Task | Reason |
|---|---|
| U08 — Blocks through matching holes | The current task scene does not yet define a confidently identified set of individual blocks and matching apertures for ordered passage scoring. |
| U10 — Combine nuts and batteries | The source image does not establish the small-object identities/arrangement well enough to assign a defensible success condition. |
| U11 — Hook hat on tripod | Hat loop, post contact, and stable hanging support are not yet represented and scored robustly. |
| U14 — Cinch drawstring | The bag and cord are rigid visual proxies; cloth/rope deformation is absent. |
| U16 — Bake croissant | The current “oven” is a toaster-like visual proxy without a validated cavity or thermal state. Insertion is not baking. |
| U17 — Fry vegetables | Pan/spatula motions do not create a validated heat-transfer or frying-state model. Stirring alone is not frying. |
| U20 — Weave wire through holes | The wire is rigid, so it cannot perform ordered multi-hole weaving. |

These tasks remain visible in the task catalog, but their local physical success
must not be reported as measured until the missing interaction is modeled and
validated. A new scalar state or constraint must be labeled as a proxy rather
than described as fluid, thermal, magnetic, or deformable-body simulation.

## Validation boundary

For this implementation update, no simulator rollout, renderer run, or test
suite was run. The authored USD joints and runtime event callbacks therefore
remain unvalidated. Before any task is promoted to eligible, inspect the
resulting USD, verify reset/replay behavior and contact response in Isaac Lab,
and inspect policy-free and policy rollout videos. The existing eligibility
gate should remain in place until those steps pass.
