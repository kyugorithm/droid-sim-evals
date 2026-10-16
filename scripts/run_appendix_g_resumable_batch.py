#!/usr/bin/env python3
"""Resume layout-0 rollouts in one Kit app, with artifact-checked fallback."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def completed_tasks(output: Path) -> set[str]:
    completed = set()
    for path in output.rglob('results.json'):
        try:
            rows = json.loads(path.read_text())
            for row in rows:
                video = Path(row.get('video', ''))
                if (row.get('layout_id') == 0 and row.get('episode') == 0
                        and row.get('steps') == 450 and video.is_file()
                        and video.stat().st_size > 0):
                    completed.add(row['task_id'])
        except (OSError, ValueError, KeyError, TypeError):
            # A writer may be updating a result file; inspect it on the next poll.
            continue
    return completed


def run_tasks(tasks: list[str], args, name: str) -> None:
    repo = Path(__file__).resolve().parents[1]
    command = ['bash', str(repo / 'scripts/run_appendix_g_eval_b300.sh'),
               '--task', ','.join(tasks), '--layout-ids-csv', '0',
               '--episodes', '1', '--max-steps', '450',
               '--scene-dir', str(args.scene_dir), '--output', str(args.output)]
    env = dict(os.environ, SIM_DEVICE='cpu')
    log_path = args.output / 'logs' / f'{name}.log'
    print(f'START {name}: {",".join(tasks)}; log={log_path}', flush=True)
    previous = completed_tasks(args.output)
    last_progress = time.monotonic()
    with log_path.open('a') as log:
        process = subprocess.Popen(command, cwd=repo, env=env,
                                   stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        while process.poll() is None:
            time.sleep(5)
            now_complete = completed_tasks(args.output)
            if now_complete - previous:
                print(f'COMPLETED: {",".join(sorted(now_complete))}', flush=True)
                previous |= now_complete
                last_progress = time.monotonic()
            if time.monotonic() - last_progress > args.stall_seconds:
                print(f'STALLED {name}: no completed episode for {args.stall_seconds}s', flush=True)
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                except ProcessLookupError:
                    process.wait()
                break
        print(f'EXIT {name}: {process.wait()}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scene-dir', type=Path, required=True)
    parser.add_argument('--stall-seconds', type=int, default=600)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.scene_dir = args.scene_dir.resolve()
    (args.output / 'logs').mkdir(parents=True, exist_ok=True)
    tasks = [f'{split}{number:02}' for split in ('S', 'U') for number in range(1, 21)]
    pending = [task for task in tasks if task not in completed_tasks(args.output)]
    print(f'RESUME: {40-len(pending)}/40 saved; {len(pending)} pending', flush=True)
    if pending:
        run_tasks(pending, args, 'persistent_batch')
    # Kit may exit with status zero during shutdown even after an exception.
    # Completion therefore depends on saved full rollouts, not process status.
    for task in tasks:
        if task not in completed_tasks(args.output):
            run_tasks([task], args, f'{task}_fallback')
    missing = [task for task in tasks if task not in completed_tasks(args.output)]
    print(f'FINISHED: {40-len(missing)}/40; missing={missing}', flush=True)
    return bool(missing)


if __name__ == '__main__':
    raise SystemExit(main())
