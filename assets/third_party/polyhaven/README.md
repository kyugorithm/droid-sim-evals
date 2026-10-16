# Poly Haven CC0 assets used by the Appendix G scene previews

All listed assets are from Poly Haven and published under CC0 1.0. They are
included locally so generated USD files can keep their textures available
without a network download. Only 1K-resolution maps are included.

## Wicker Basket 01

- Source: <https://polyhaven.com/a/wicker_basket_01>
- License: CC0 1.0 (<https://polyhaven.com/license>)
- Local scene use: S05 visual mesh; a separate project-authored open-container
  proxy supplies collision geometry. The source's natural wicker color is kept.
- Files: the GLTF mesh, binary buffer, and diffuse, normal-GL, and ARM maps.

## Tabletop — White Maple Veneer (currently used)

- Source: <https://polyhaven.com/a/white_maple_veneer>
- License: CC0 1.0 (<https://polyhaven.com/license>)
- Local scene use: diffuse color texture on the shared tabletop. It changes
  appearance only, not the table dimensions or collision surface. Chosen to
  better match the light, warm tabletop in the Appendix G reference photos;
  the applied warm tint is a local material adjustment.
- File: `white_maple_veneer/white_maple_veneer_diff_1k.jpg`.

The earlier `wood_table/wood_table_diff_1k.jpg` map is retained in the asset
folder for provenance, but is no longer used because its dark, distressed
planks did not match the reference tabletop.

## Terry Cloth

- Source: <https://polyhaven.com/a/terry_cloth>
- License: CC0 1.0 (<https://polyhaven.com/license>)
- Local scene use: normal map on the layered, rigid towel proxy. The diffuse map
  is retained for future material tuning; the scene currently uses the white
  color seen in the paper photos.
- Files: `terry_cloth/terry_cloth_diff_1k.jpg` and
  `terry_cloth/terry_cloth_nor_gl_1k.jpg`.

These props improve image appearance but do not add cloth deformation or
validate contact, task success, or paper-exact geometry.
