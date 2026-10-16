# Appendix G image-grounded scene specs — Group A (S01–S10)

Specification pass: 2026-10-14. `scene_overrides.yaml` records visible object
counts, identities or explicit identity uncertainty, approximate proportions,
relative placement, colors, and reset relations from the paper thumbnails.
Metric dimensions and robot-frame poses are local estimates, not measurements
published by the paper. The reference photos are small and do not establish
hidden geometry or exact camera calibration.

## Camera and pose convention

The review camera looks from negative Y. Screen-right is broadly +X, screen-left
is broadly -X, photo-back is broadly +Y, and photo-front is broadly -Y. This is
a qualitative mapping for the visible tabletop, not a calibrated projection.
Keep this convention when the parent review camera is refined. The two layouts
remain deterministic variations of each task's image-grounded relations.

## Per-task visual targets

| Task | Visible inventory and reset relation |
|---|---|
| S01 | Blue-handled scissors, a small tapered white cup, and a slim white marker with a red end. The cup sits between the scissors and marker, slightly toward the photo-front. |
| S02 | A rounded, tapered turquoise perforated basket with a warm orange-brown upper rim; blue-handled scissors and a white/red marker sit separately in front, with the dark tape rectangle to the left. |
| S03 | A low honey-oak cabinet with an open drawer and visible cabinet body/fascia. The paired glove object is at the open drawer edge; exact glove identity/color remains uncertain. A dark tape rectangle is in front-left of the cabinet. |
| S04 | A small white patterned open cup behind the tape rectangle; the white/red marker is inserted upright in the cup, with its red end protruding above the rim. This records the photographed reset state without inferring how the instruction began. |
| S05 | A light woven open basket with red/pink checked lining near the back-center; a yellow banana is front-left and a red apple front-right. The basket uses the integrated rounded wicker/gingham helper; the apple's named YCB object selects the repository scan. |
| S06 | A small white cup back-left, a thick irregular folded white towel front-right, and a tall purple cup/bottle-like distractor behind the towel. The purple item's identity is uncertain. |
| S07 | A shallow open metal container at left/back, a folded towel near the front-center, and a deep red-orange bowl at right/back. The exact mesh/perforation of the metal item is uncertain. |
| S08 | A black fedora leans across the left side of a low wooden drawer cabinet. The fixture has drawer fronts and objects on top; it is not a standalone tray or simple tool caddy. The dark tape rectangle is left/front of the cabinet. |
| S09 | A low wooden cabinet with an open upper drawer and visible lower drawer fronts. Blue-handled scissors are front-right, a white/red marker front-left, and the tape rectangle left of the cabinet. |
| S10 | A thick folded white towel lies in the foreground-left, in front of an open woven basket with red/pink lining at back-center. A vivid pink loose net/fabric-like pile is foreground-right; its identity is unresolved and it is not task-critical. |

## Implementation limits and unresolved requirements

- The YAML is a scene specification, not evidence that the current scene builder
  renders every declared template. In particular, the drawer/cabinet, towel,
  cup, fedora, and glove visuals need an updated preview to confirm their shape
  and scale. The cabinet must read as a cabinet with drawer fronts and a body;
  a tray alone does not match S03, S08, or S09.
- S04's inserted marker is an observed reset relation. A marker held in a cup is
  not proof of the original task's initial-state protocol or of a valid success
  evaluator.
- S03, S06, S07, S08, S09, and S10 include rigid visual/collision proxies for
  objects that may be flexible or articulated. Their appearance specifications
  do not claim glove, cloth, drawer, scissor-hinge, or grasp physics fidelity.
- S05/S10 basket lining, S06 purple-object identity, S07 metal-container detail,
  and S10 pink-pile identity remain uncertain at thumbnail resolution.
- S02's turquoise basket keeps its existing project template reference; the
  separate image-matched blue-basket helper is still pending integration.
- No scenes were rebuilt or rendered for this pass, and no inference or physics
  verification was run. Existing readiness/evaluator status must not be
  inferred from the added visual descriptions.
