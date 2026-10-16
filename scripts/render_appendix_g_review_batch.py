#!/usr/bin/env python3
"""Bounded, resumable preview rendering; one isolated Isaac process per scene.

Never calls a policy. Completed output is published only after all images and
scene-hash evidence validate. Failed jobs retain logs, not a misleading image.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", action="append")
    parser.add_argument("--workers", type=int, choices=[1, 2], default=1)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--quality-review", action="store_true")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.scene_dir = args.scene_dir.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    scenes = sorted(args.scene_dir.glob("*_layout0.usd"))
    if args.task:
        wanted = {t.upper() for t in args.task}
        scenes = [s for s in scenes if s.stem.split("_")[0].upper() in wanted]
        if {s.stem.split("_")[0].upper() for s in scenes} != wanted:
            parser.error("Some requested task USDs are missing")
    if not scenes:
        parser.error("No layout0 scenes found")
    sources = [ROOT / "scripts/preview_appendix_g_scene.py",
               ROOT / "scripts/preview_appendix_g_scene_b300.sh",
               ROOT / "src/sim_evals/environments/appendix_g_environment.py"]
    renderer_hashes = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    results = []

    def render(scene):
        task = scene.stem.split("_")[0].upper()
        destination = args.output / task / "layout0"
        fingerprint = {"scene_sha256": digest(scene), "renderer_sha256": renderer_hashes,
                       "quality_review": args.quality_review}
        evidence_file = destination / "batch_evidence.json"
        if evidence_file.exists():
            old = json.loads(evidence_file.read_text())
            if old.get("fingerprint") == fingerprint and old.get("status") == "rendered":
                return old | {"resumed": True}
        if destination.exists():
            raise RuntimeError(f"Refusing to overwrite stale output: {destination}; use a new revision directory")
        temporary = Path(tempfile.mkdtemp(prefix=f".{task}-", dir=args.output))
        log_path = args.output / f"{task}.log"
        # Eight CPU cores per independent Kit session; no unconstrained thread fan-out.
        allowed = sorted(os.sched_getaffinity(0))
        cpus = ",".join(map(str, allowed[:8]))
        command = ["taskset", "-c", cpus, "bash", str(ROOT / "scripts/preview_appendix_g_scene_b300.sh"),
                   "--scene-dir", str(args.scene_dir), "--output", str(temporary), "--task", task, "--layout", "0"]
        if args.quality_review:
            command.append("--quality-review")
        start = time.monotonic()
        status, error = "failed", None
        try:
            with log_path.open("w") as log:
                process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                try:
                    returncode = process.wait(timeout=args.timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    raise TimeoutError(f"Kit exceeded {args.timeout}s")
            if returncode:
                raise RuntimeError(f"Kit exited {returncode}; see {log_path.name}")
            from PIL import Image
            rendered = temporary / task / "layout0"
            for name in ("reference_cam", "review_cam", "external_cam", "external_cam_2", "wrist_cam", "contact_sheet"):
                with Image.open(rendered / f"{name}.png") as image:
                    image.verify()
            evidence = json.loads((rendered / "render_evidence.json").read_text())
            if evidence["scene_sha256"] != fingerprint["scene_sha256"]:
                raise RuntimeError("Scene changed while rendering")
            if any(digest(p) != renderer_hashes[str(p.relative_to(ROOT))] for p in sources):
                raise RuntimeError("Renderer changed while rendering")
            destination.parent.mkdir(exist_ok=True)
            rendered.rename(destination)
            status = "rendered"
        except Exception as exc:
            error = str(exc)
        result = {"task": task, "status": status, "seconds": round(time.monotonic()-start, 2),
                  "fingerprint": fingerprint, "error": error, "visual_approval": "pending",
                  "physics_approval": "pending", "policy_inference_calls": 0, "log": log_path.name}
        if status == "rendered":
            evidence_file.write_text(json.dumps(result, indent=2) + "\n")
            # Only our newly-created staging directory; no user outputs removed.
            shutil.rmtree(temporary)
        print(json.dumps(result), flush=True)
        return result

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        pending = [executor.submit(render, scene) for scene in scenes]
        for future in as_completed(pending):
            results.append(future.result())
            status_path = args.output / "batch_status.json"
            staged = args.output / ".batch_status.tmp"
            staged.write_text(json.dumps({"total": len(scenes), "completed": len(results),
                                         "workers": args.workers, "results": results}, indent=2) + "\n")
            staged.replace(status_path)
            subprocess.run([str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/preview_appendix_g_scene.py"),
                            "--scene-dir", str(args.scene_dir), "--output", str(args.output), "--index-only"],
                           cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    if any(r["status"] != "rendered" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
