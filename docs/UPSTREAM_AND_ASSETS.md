# Upstream and asset provenance

## Upstream code

This working tree is based on TiPToP Robotics'
[`droid-sim-evals`](https://github.com/tiptop-robot/droid-sim-evals), commit
`69a914cf56e0da6adafe9428de39b6ceffe9bcc6` (2026-10-12). TiPToP's repository
is itself a fork of [`arhanjain/sim-evals`](https://github.com/arhanjain/sim-evals)
and adds a five-scene DROID benchmark with 51 object-layout variants (10, 10,
11, 10, and 10). Those variants are initial states, not independent language
tasks.

The GitHub repository fork has not yet been created from this machine. Once the
owner account is confirmed, create a native public fork of TiPToP's repository
and push this work there so the parent relationship and upstream history are
visible. Do not replace that relationship with an unrelated source import.

Neither TiPToP's repository nor its original `sim-evals` parent currently
shows a repository-wide license file. Public visibility and GitHub's fork
feature are not equivalent to an unrestricted license for rehosting, relicensing,
or redistributing the inherited code outside the GitHub fork relationship.
This repository therefore does not add a root license that purports to cover
upstream files. Preserve attribution and ask the respective maintainers about
broader reuse before distributing a standalone mirror or applying a new
license to the inherited code.

The DreamZero source repository is separately licensed under Apache-2.0. The
small B300 compatibility patch in [`../patches/dreamzero-b300-compat.patch`](../patches/dreamzero-b300-compat.patch)
is a diff against DreamZero commit `ab790c198fbce33503358efbbd4187ce9a89adf3`;
it contains no model weights. See [`../patches/README.md`](../patches/README.md)
before applying it.

## Asset policy

“Free to download” is not enough to establish permission to include a file in a
public repository. For every bundled third-party model or texture, keep its
original source URL, author/creator, exact license, source revision or asset
ID, modifications, and a copy/link to the required notice. Assets without
clear redistribution terms are either fetched from their original publisher
by a setup script or excluded.

| Source | Terms found | Project handling |
| --- | --- | --- |
| [YCB Object and Model Set](https://ycb-benchmarks.s3.amazonaws.com/index.html) | Dataset: CC BY 4.0; code: MIT, as stated by the dataset maintainers | Suitable for selected object models when the CC BY attribution and change notice travel with each asset. Do not apply the project-code license to these files. |
| [Smithsonian Open Access](https://www.si.edu/openaccess/faq) | Individual records marked CC0 are reusable; non-CC0 records have separate conditions | Candidate source for scene props. Include only records explicitly marked CC0 or individually cleared; retain the item ID and source URL in the manifest. |
| TiPToP [`assets.zip`](https://tiptop-sim-assets.s3.us-east-1.amazonaws.com/assets.zip) | Hosted by TiPToP; a redistribution license was not found in the repository README | Required for the five inherited scenes. Download from the upstream host for local evaluation; do not bundle or mirror until terms are confirmed. |
| [`owhan/DROID-sim-environments`](https://huggingface.co/datasets/owhan/DROID-sim-environments) | Dataset card declares MIT; revision used in the earlier smoke-scene setup: `5b815672a9a2e3ae596ae845188ae4be5c5d2f34` | Separate from TiPToP's `assets.zip`. Keep only if a documented workflow still needs that bundle; pin revision and checksum in run records. |
| TiPToP repository files (`tiptop_assets/` and `docs/scene*_*.png`) | Inherited from the public upstream fork; no repository-wide license was located | Retain as upstream content in a native GitHub fork with visible attribution. Do not claim these files are newly authored or separately licensed by this project. |
| NVIDIA Isaac Sim / Omniverse delivered assets | Covered by NVIDIA's separate Additional Software and Materials License, not by the Isaac Sim source-code Apache license | Do not bundle NVIDIA-delivered assets. Let users install Isaac Sim and retrieve permitted assets through NVIDIA's supported flow. |
| Individual artist/marketplace assets | Varies per item | Not approved until the actual asset page and license are recorded and redistribution/adaptation are permitted. |

The YCB maintainers state that the model dataset is CC BY 4.0 and list
household objects including scissors, markers, fruit, bowls, mugs, pans, and
utensils. This is a strong first source for manipulation props. We will prefer
original geometry for scene furniture and fixtures (tables, drawers, counters,
simple appliances) where that is faster and avoids uncertain asset rights.
The initial YCB 037 scissors model and its notice are included under
`assets/third_party/ycb/037_scissors/`. We also downloaded eight original
Google-scanner 16k archives (apple, lemon, bowl, mug, skillet, knife, spatula,
and large marker; approximately 50 MB total) for the first task-family
prototypes. These retain their original archive format and are not yet
converted or validated in Isaac Sim. After verifying `SHA256SUMS`, extract
only the textured OBJ, material, and texture with
`bash scripts/prepare_ycb_assets.sh`. The unpacked working copies are ignored
by Git. The S01 USD and preview are in the
project asset folders. Their exact provenance and checksums are recorded in
[`../assets/asset_manifest.yaml`](../assets/asset_manifest.yaml).

## Current project files

No upstream simulation bundle, model checkpoint, Isaac Sim installation, or
private experiment output is vendored here. The S01 candidate is included with
its YCB 037 scissors scan and required CC BY 4.0 notice. The user-provided
paper screenshot used as a visual reference is not redistributed; the source
paper is linked from the task manifest and scene README.

For each new asset, update this table and the machine-readable
[`../assets/asset_manifest.yaml`](../assets/asset_manifest.yaml) before adding
the file to Git. Record a SHA-256 for released binaries. The `.gitignore`
defaults to keeping the upstream asset bundle out of Git and allows only the
currently reviewed project-asset paths.
