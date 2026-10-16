# Innerscene public models

## Bake Mini - Small Appliance (toaster oven)

- Source: [Innerscene 3D Parts Library](https://www.innerscene.com/tools/library/3d-parts/bake-mini-small-appliance-87a969dc)
- Local file: `toaster-oven.glb` (267,264 bytes)
- License: CC0 1.0, as stated on the source listing.
- Source description: countertop oven with glazed drop door, two knobs,
  interior rack, rear vents, embedded PBR materials, and about 8k triangles.
- Local scene use: U16 visual mesh; the model is rescaled to the scene proxy.
  Door articulation, thermal behavior, and cooking success are not implemented.

## Stack Bin - Storage Bin

- Source: [Innerscene 3D Parts Library](https://www.innerscene.com/tools/library/3d-parts/stack-bin-storage-bin-31047c8f)
- Original file: `stackable-storage-bin.glb` (about 150 KiB)
- License: CC0 1.0, public domain dedication. The source page permits use,
  modification, and redistribution; attribution is not required. The source is
  recorded here for provenance.
- Source dimensions: 35.4 × 43 × 22.4 cm (W × D × H), according to the source
  listing.
- Local scene adaptation: converted into USD mesh geometry, scaled to the S02
  tabletop prop, and recolored blue. The source's front access cutout remains.

This is a freely reusable substitute, not the original physical prop from the
DreamZero paper photograph.

## Toast Two - Small Appliance

- Source: [Innerscene 3D Parts Library](https://www.innerscene.com/tools/library/3d-parts/toast-two-small-appliance-4abfe108)
- Local file: `toast-two-small-appliance.glb` (224,384 bytes)
- License: CC0 1.0, as stated on the source listing.
- SHA-256: `26e4e3c449b00452cca00edf2534643114d8c8447e320df5a41c9696bf0321a0`
- Source bounds: approximately 32.25 × 16.7 × 19.05 cm after Y-up to Z-up
  axis conversion. Local scene scale is stored in the U13 override.
- Local scene use: render mesh only. U13 adds a separate hidden open-slot
  collision shell; the GLB is not treated as a physics-ready collider.

## Low Store - Storage Drawer

- Source: [Innerscene 3D Parts Library](https://www.innerscene.com/tools/library/3d-parts/low-store-storage-drawer-11b51d87)
- Local file: `low-store-storage-drawer.glb` (849,492 bytes)
- License: CC0 1.0, as stated on the source listing.
- SHA-256: `f5972d725c35e09541396a6a13309e04df075d59f02667f17a8abb38f1bf8056`
- Source bounds: approximately 75.6 × 56.2 × 19.6 cm. This is a candidate
  visual reference only; no articulated drawer joint or evaluator is implemented.
