# V9 Appendix G asset and render pass

Date: 2026-10-14
Purpose: carry the improved, asset-aware scene presentation through the full
40-task Appendix G set and produce a consistent gallery for visual review.

## Result

- Built 40 layout-0 USD scene candidates (S01–S20 and U01–U20) under the
  private data directory `~/.local/share/.private/appendix_g_assets_v9/`.
- Rendered all 40 with the quality-review preset to
  `~/.local/share/.private/runs/scene_previews/assets_quality_v9/`.
- Batch status: 40/40 rendered, no failed scenes, and zero policy-inference
  calls. The gallery contains 240 PNGs (six camera views per scene) and its
  `index.html` is served successfully by the existing preview server.
- U14's previous pouch was visibly oversized and occluded the blue prop. The
  visual mesh was reshaped to a flatter, smaller gathered pouch; the pouch and
  blue prop poses were adjusted to keep both visible. This is still a static
  visual approximation, not cloth simulation.
- Inspection-only rendering uses 2560×1920, 8 samples per pixel, TAA, shadows,
  ambient occlusion, reflections, global illumination, and translucency. It
  does not change policy inputs or evaluation settings.

The set is not an exact reconstruction of the paper's original assets,
calibrated camera poses, or physical scenes. Scene-specific free assets are
used where the task specs identify a sufficiently close match; other visuals
remain project-authored approximations. Consult the task specs and asset
provenance before redistribution: licenses differ (including CC0 and CC-BY).
The previews have not yet been approved by the user. Collision/articulation,
reset determinism, evaluators, alternate layouts, and policy inference are also
not validated by this render pass.

## View remotely

From the Mac, forward the preview server port (use a free local port):

```bash
kubectl -n research port-forward pod/kyuchul-lee-gpu-b300-0 18766:8765
```

Open `http://localhost:18766/assets_quality_v9/index.html` in a browser.
If local port 18766 is occupied, choose another local port and replace 18766 in
the URL; leave the pod-side port 8765 unchanged.

## Rebuild and rerender

Build all layout-0 scene USDs:

```bash
scripts/build_appendix_g_scenes_b300.sh \
  --output "$HOME/.local/share/.private/appendix_g_assets_v9" \
  --layout 0
```

Render the review gallery:

```bash
.venv/bin/python scripts/render_appendix_g_review_batch.py \
  --scene-dir "$HOME/.local/share/.private/appendix_g_assets_v9" \
  --output "$HOME/.local/share/.private/runs/scene_previews/assets_quality_v9" \
  --quality-review --workers 2 --timeout 300
```

Generated USDs and renders are private run artifacts, not Git-tracked assets.
No DreamZero rollout video was generated in this pass.
