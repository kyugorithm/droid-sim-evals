# Persistent Appendix G rollout execution

## Failure and repair

The original multi-task evaluator saved its first episode, then failed while
creating the next environment. An explicit traceback before Kit shutdown showed:

```
ValueError: A prim already exists at path: '/World/spehre'.
```

Closing an Isaac Lab environment cleared its SimulationContext but left USD
prims in the stage. The next task attempted to spawn a light at the same path.
Kit fast shutdown also concealed the exception, making process exit status an
unreliable completion indicator.

`eval/appendix_g_eval.py` now deliberately disables/unsubscribes the old STOP
handler, stops the timeline, closes the environment, and creates a clean stage.
The installed Isaac Lab STOP handler contains a render-until-playing loop;
disabling that handler during deliberate teardown also avoids getting trapped
in that loop. Runtime exceptions are printed before closing Kit.

An inference-free lifecycle test rendered S04 and S05 camera observations in a
single application and closed both environments. Both observations had shape
`(720, 1280, 3)` and nonzero pixel variation. The test printed
`PASS: two rendered scenes in one application`. Task setup/render/close times
were 5.00 and 6.80 seconds, excluding application startup. This verifies scene
lifecycle handling, not task success or an end-to-end inference speedup.

## Resumable execution

With the DreamZero inference server already listening on port 8000:

```bash
python scripts/run_appendix_g_resumable_batch.py \
  --scene-dir /path/to/usd_all \
  --output /path/to/full_taskwise
```

The coordinator checks existing result JSON files and nonempty MP4 files, then
runs missing tasks together in one application. The protocol is layout 0,
one episode per task, 450 control steps, and the existing default action horizon
of 8. It does not change inference resolution, model settings, or scoring.

The coordinator verifies saved episodes rather than trusting Kit's exit code.
If the batch exits early, remaining tasks are attempted individually. If no
episode finishes for 600 seconds, it terminates only its own simulator process
group and falls back to individual runs. The inference server is independent.
Logs go under the output directory's `logs/` directory.

Completion here means a full rollout and video were saved. A null/unvalidated
success score remains null; completion is not evidence of task success.

## Runtime restoration

The current container lacked OS graphics runtime libraries. Running
`scripts/setup_graphics_runtime.sh` restored them and the actual Vulkan-instance
preflight passed. These OS packages need persistence in the container image or
restoration after container recreation; Python environments alone do not include
them.

The inference server was restarted once after its previous process disappeared.
Loading existing local weights took about 21 minutes; the first inference then
took about 76 seconds. Subsequent requests began advancing rollout steps normally.
Keep the inference server running across tasks to avoid repeating this startup.

The rollout gallery is served on pod port 8766. Forward that port to a free local
port and open `/full_taskwise/index.html` under that local address.
