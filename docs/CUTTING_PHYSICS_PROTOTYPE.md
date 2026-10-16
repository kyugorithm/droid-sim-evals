# U03 fixed-seam cutting prototype (2026-10-15)

## Scope and limitations

Implemented one experimental physical effect, not all Appendix G mechanics.
This is a pre-segmented, fixed-seam geometric cutting approximation. It is NOT
arbitrary mesh fracture, force-based cutting, or a validated policy benchmark.
Two dynamic convex bread halves are connected by a PhysX FixedJoint. A stateful
blade-edge geometry/stroke gate disables that joint. Thereafter the two bodies
are independent rigid bodies. Rendering is actual simulator output.

**Knife/bread contacts are explicitly filtered**: rigid bread would otherwise
block penetration. No cutting resistance, energy, compliance or force sensor is
modeled. Table and other rigid contacts remain. A blade-center trajectory is
used, not a full swept cutting-volume solver. Single environment only.

The physics prototype uses deliberately simple procedural loaf halves and a
known-axis knife. Existing textured visual-review scenes remain unchanged.
The runtime is enabled only by `appendix_g:cutting_prototype` on the input USD.
Ordinary U03 remains excluded from benchmark scoring. The prototype does not
silently turn its scripted test pass into policy success.

## Verification

- [x] Nine isolated gate tests: valid stroke (one event), wrong seam, wrong
  orientation, missed width, teleport, starting below, upward stroke, leaving
  seam, NaN input.
- [x] Actual Isaac Lab/PhysX positive probe: joint released, independently
  moving halves; measured root separation about 0.0211 m after opposite test velocities.
- [x] Actual negative probe: off-seam stroke leaves joint connected; numeric
  separation and full trajectory stored in its JSON.
- [x] Both actual probes encoded to MP4 using imageio's FFmpeg backend.
- [ ] Robot-held knife integration/grasp test, grasp success and safe force behavior.
- [ ] Force-based cutting/material deformation; arbitrary cut locations.
- [ ] Repeat/reset regression and broader pose/velocity sweep.
- [ ] Match textured visual assets to the split collision model.

The initial positive probe failed because the unheld dynamic knife fell between
scripted commands. The second revision uses a kinematic knife **only in the
scripted test**. Default scene knife remains dynamic. The runner explicitly
labels the videos as scripted, not DreamZero inference. Neither force-based
cutting nor autonomous cutting has been demonstrated.

## Files and usage

- `scripts/build_cutting_prototype.py`: non-overwriting scene author.
  Requires the same Isaac USD bindings/LD_LIBRARY_PATH as the ordinary builder.
  Source: `$PRIVATE_DATA_ROOT/appendix_g_fixes_v11/u03_layout0.usd`.
  Output: `$PRIVATE_DATA_ROOT/appendix_g_cutting_p1/u03_layout0.usd`.
- `src/sim_evals/environments/cutting_physics.py`: gate and reset/step callbacks.
- `tests/test_cutting_gate.py`: simulator-independent gate tests.
- `scripts/preview_appendix_g_scene.py --cutting-probe valid|miss`: scripted
  stroke, opposite-velocity release test, MP4 and JSON output.
- `scripts/publish_cutting_review.py`: checks probe results before publication.

```bash
.venv/bin/python tests/test_cutting_gate.py
bash scripts/preview_appendix_g_scene_b300.sh \
  --scene-dir "$PRIVATE_DATA_ROOT/appendix_g_cutting_p1" \
  --output "$PRIVATE_DATA_ROOT/runs/scene_previews/cutting_new_valid" \
  --task U03 --layout 0 --cutting-probe valid
# Repeat with --cutting-probe miss and a separate output directory.
```

Served page: `/cutting_physics_review/index.html`.
Actual completed probes: `runs/scene_previews/cutting_p2_{valid,miss}/U03/layout0/`.
No checkpoint loading, policy inference, repository push or base scene overwrite.
