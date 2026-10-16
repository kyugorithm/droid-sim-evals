# V8 asset and render refinement

Date: 2026-10-14
Purpose: replace selected visibly synthetic props with redistributable textured
models and produce a higher-resolution, higher-sample visual review. These are
approximate Appendix G reconstructions, not the paper's original assets or
calibrated camera poses.

## Changes in this pass

| Task | Visual change | Source/license | Simulation status |
| --- | --- | --- | --- |
| S03 | Posed pair of dark gloves, less gray under bright lighting | MakeHuman Community `gloves01`, MargaretToigo, CC0; static mesh adaptation | Visual review pending; no cloth physics or inference |
| S05 | Textured natural wicker scan replaces the drawn basket; hidden open-container collision proxy is retained. A textured single-banana scan replaces the segmented banana | Poly Haven Wicker Basket 01, CC0; Innerscene Single Banana, CC0 | Visual review pending; no policy run |
| S16/S17 | Green-grape GLB already selected in v8c; retained for this comparison | Innerscene Bunch of Grapes, CC0; local berry hue adjustment | Visual review pending; no policy run |
| U16 | Textured Poly Haven croissant already selected in v8c; retained for this comparison | Poly Haven Croissant, CC0 | Visual review pending; no policy run |

Inspection rendering is now 2560×1920, 8 samples per pixel, TAA, shadows,
ambient occlusion, reflections, global illumination, and translucency. This is
an inspection-only preset; it does not change evaluation defaults or add
DreamZero inference calls.

## Reproduction and outputs

- Asset specs and licenses: `assets/appendix_g/task_specs/` and
  `assets/third_party/{food_v8,gloves_v8,polyhaven}/`.
- USD review set: private
  `~/.local/share/.private/appendix_g_assets_v8e/` (S03, S05, S16, S17, U16;
  layout 0 only).
- Render gallery: private
  `~/.local/share/.private/runs/scene_previews/assets_quality_v8e/`.
- The earlier v8d render is retained as an intermediate; its S05 USD had an
  overlapping hidden solid collider. Use v8e, where the open basket keeps only
  the separate floor-and-wall collision proxy.
- `assets_quality_v8f` is a one-task camera-visibility probe, not a new scene
  revision. Its attempted robot path did not resolve, so the robot remained
  visible; v8e remains the verified gallery.
- Gallery approval, physics validation, and inference are intentionally still
  pending. Do not describe these previews as successful rollouts.

To view the gallery from the Mac while the pod's preview server is running:

```bash
kubectl -n research port-forward pod/kyuchul-lee-gpu-b300-0 18766:8765
```

Then open `http://localhost:18766/assets_quality_v8e/index.html`.

Build command:

```bash
scripts/build_appendix_g_scenes_b300.sh \
  --output "$HOME/.local/share/.private/appendix_g_assets_v8e" \
  --task S03 --task S05 --task S16 --task S17 --task U16 --layout 0
```

Render command:

```bash
.venv/bin/python scripts/render_appendix_g_review_batch.py \
  --scene-dir "$HOME/.local/share/.private/appendix_g_assets_v8e" \
  --output "$HOME/.local/share/.private/runs/scene_previews/assets_quality_v8e" \
  --quality-review --workers 2 --timeout 300
```
