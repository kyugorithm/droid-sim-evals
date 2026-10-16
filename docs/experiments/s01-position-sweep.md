# S01 Position Sweep

## Purpose and interpretation

This is a diagnostic experiment to test whether the current failure depends on
where the image-reconstructed S01 objects sit in the robot workspace. It is
not a reproduction of DreamZero's paper metrics: the scene geometry and success
checker are local proxies, and the paper's exact object poses are unavailable.

The task and policy are held fixed: “Move the cup forward then put the marker
inside the cup.” The cup, marker, and scissors retain the same appearance and
relative arrangement in every variant; only their shared XY translation changes.
One rollout is run per variant. Since this is a stochastic policy and a single
trial, an apparent success is a clue for follow-up, not a reliable success rate.

## Variants

Offsets are in metres in the USD robot frame. Negative X is toward the robot.

| Layout ID | ΔX | ΔY | Label |
|---:|---:|---:|---|
| 0 | 0.00 | 0.00 | baseline |
| 2 | -0.05 | 0.00 | x_toward_05cm |
| 3 | -0.10 | 0.00 | x_toward_10cm |
| 4 | -0.15 | 0.00 | x_toward_15cm |
| 5 | +0.05 | 0.00 | x_away_05cm |
| 6 | +0.10 | 0.00 | x_away_10cm |
| 7 | 0.00 | -0.06 | y_minus_06cm |
| 8 | 0.00 | -0.12 | y_minus_12cm |
| 9 | 0.00 | +0.06 | y_plus_06cm |
| 10 | 0.00 | +0.12 | y_plus_12cm |

Machine-readable variant list: [`../configs/s01_position_sweep.yaml`](../../configs/s01_position_sweep.yaml).

## Results

Completed on 2026-10-12. One rollout was run for each of the 10 variants (10
episodes total), with the same DreamZero inference setup and task instruction;
each episode ran for 450 steps. All 10 rollouts scored `success=false` and
`progress=0.0`. The geometric proxy recorded `0.000 m` cup-forward displacement
for every variant. Marker-to-cup XY distance stayed approximately `0.237697 m`,
as expected because the two objects were translated together.

| Layout ID | ΔX (m) | ΔY (m) | Run ID (UTC) | Success / progress |
|---:|---:|---:|---|---|
| 0 | 0.00 | 0.00 | `20261012T163434Z` | false / 0.0 |
| 2 | -0.05 | 0.00 | `20261012T164513Z` | false / 0.0 |
| 3 | -0.10 | 0.00 | `20261012T164845Z` | false / 0.0 |
| 4 | -0.15 | 0.00 | `20261012T165203Z` | false / 0.0 |
| 5 | +0.05 | 0.00 | `20261012T165521Z` | false / 0.0 |
| 6 | +0.10 | 0.00 | `20261012T165841Z` | false / 0.0 |
| 7 | 0.00 | -0.06 | `20261012T170201Z` | false / 0.0 |
| 8 | 0.00 | -0.12 | `20261012T170517Z` | false / 0.0 |
| 9 | 0.00 | +0.06 | `20261012T170834Z` | false / 0.0 |
| 10 | 0.00 | +0.12 | `20261012T171151Z` | false / 0.0 |

This indicates that changing the shared object placement alone did not resolve
the failure. It does **not** establish why: this is one stochastic-policy trial
per pose, and the local success checker is an approximate geometric proxy, not
the paper's evaluation metric. In particular, this sweep does not test changes
to object appearance, camera view, task wording, or the proxy checker itself.

The per-run metrics and exact video paths are in `results_summary.csv` alongside
the private experiment artifacts. All 10 episode videos and the 10-up montage
were decoded end-to-end with the same FFmpeg binary used for recording; all
passed without decode errors. The montage is arranged in two columns and five
rows, in the same order as the results table above (left-to-right, top-to-bottom).
The original videos' black letterboxing was cropped for this comparison montage;
the individual episode videos were left unchanged.

The CSV's `joint_start_end_max_delta_rad` field compares only the initial and
final joint positions; it is not a measure of the largest joint motion during
the rollout.

## Artifacts

The USDs, episode videos, result JSON, rollout log, CSV, and FFmpeg comparison
video are stored under
`$HOME/.local/share/.private/droid-sim-eval-validation/position-sweep/` on the
B300 host. They are intentionally not committed because videos and scene
bundles are generated artifacts and their recorded paths are host-specific.

- `results_summary.csv`: offsets, run IDs, scores, geometric metrics, video paths
- `position_sweep_10up.mp4`: 10-variant comparison montage (2 columns × 5 rows)
- `runs/S01/<run-id>/S01/layout*/episode_00.mp4`: individual 30-second rollouts
- `runs/S01/<run-id>/results.json`: complete per-episode result and diagnostics
- `scenes/s01_layout*.usd`: the 10 translated scene variants
- `rollout.log`: rollout and renderer logs
