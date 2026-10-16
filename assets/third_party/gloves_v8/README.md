# CC0 glove asset

- Source: [MakeHuman Community gloves01](https://static.makehumancommunity.org/assets/assetpacks/gloves01.html)
- Original archive: `gloves01_cc0.zip`
- Selected source mesh: `clothes/toigo_gloves_short/gloves_hand.obj`
- Author: MargaretToigo / MRT
- License: CC0 (as stated by the source asset pack)
- Derived preview: `glove-pair-draped.glb`

The derived GLB contains two scaled, PCA-aligned, paired glove meshes in a
static draped pose, with a near-black matte material. It does not simulate
fabric or glove deformation; its use in S03 remains an approximate visual and
single-rigid-body proxy.

Regenerate the derived asset with:

```bash
.venv/bin/python scripts/prepare_visual_assets_v8.py
```
