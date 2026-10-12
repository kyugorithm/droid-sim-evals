# DreamZero B300 compatibility patch

`dreamzero-b300-compat.patch` is an optional patch for the separate DreamZero
checkout, not a patch to this simulator repository. It was prepared against
DreamZero commit `ab790c198fbce33503358efbbd4187ce9a89adf3` and contains no
checkpoint/model data. The DreamZero source project declares Apache-2.0; retain
its license and notices when applying or redistributing derivative changes.

Check applicability first from the DreamZero repository root:

```bash
git rev-parse HEAD
git apply --check /path/to/droid-sim-evals/patches/dreamzero-b300-compat.patch
```

The patch is hardware/version-specific, is not applied automatically, and does
not make Isaac Lab's B300 `sm_103` physics kernels compatible. See
[`../docs/b300-isaaclab-history.md`](../docs/b300-isaaclab-history.md) for the
tested rendering/physics distinction.
