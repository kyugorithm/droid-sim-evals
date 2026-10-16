# Food asset replacements (v8)

Downloaded 2026-10-14 from the original author Innerscene and Poly Haven.
Both sources publish the assets as CC0. These are candidate visual replacements,
not recovered paper assets.

| File | Source | SHA-256 |
| --- | --- | --- |
| grapes.glb | https://www.innerscene.com/tools/library/3d-parts/bunch-of-grapes-abfcc57f | 7a6ef5fe391129316c8033e84a26cb13e242a41c936ad2793f2b9cdf1de0a378 |
| croissant.glb | https://www.innerscene.com/tools/library/3d-parts/croissant-efa7fce0 | 6911c25dcd4c0272ba61a2de0126d788c95978b914dffe057495b95873d30da6 |
| banana.glb | https://www.innerscene.com/tools/library/3d-parts/single-banana-e42104c0 | fd0ac30d75d0615eac92c15a7fd68a0268975d9c94871eb6f7fe6a18fc630a4c |

Source assets are unmodified GLB downloads. Grapes use a local axis rotation to
lie on the table and scene-spec scaling. Croissant uses Y-up to Z-up conversion.
All collision proxies remain separate, approximate, and unvalidated.

The selected U16 croissant now uses the Poly Haven photogrammetry style model
with 2K albedo, normal, and ARM maps; downloaded source files and checksums are
in `croissant_scan/provenance.json`. The earlier Innerscene croissant remains
available as a CC0 alternative.

Sources can be downloaded without an account from
`https://www.innerscene.com/api/library/<listing-slug>/download`.
The original Y-up mesh extents measured by trimesh are:

- Grapes: 0.0753789 × 0.1273967 × 0.0738645 m; 49 meshes, 4,736 triangles.
- Croissant: 0.1464978 × 0.0449003 × 0.0645270 m; 8 meshes, 10,432 triangles.

The S03 glove pair uses a posed CC0 MakeHuman clothing mesh. Its draped pose is a
static geometric adaptation and has no cloth deformation model.
