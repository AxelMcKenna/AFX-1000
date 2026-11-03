"""Exercise the native Link adapter using a separate local SDK publisher.

Run on an isolated Link session: this test publishes tempo changes.
"""

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path


def check(probe: Path) -> dict:
    preflight = json.loads(subprocess.run(
        [probe, "--observe", "3"], capture_output=True, text=True, check=True
    ).stdout)
    if preflight["maximum_peers"]:
        raise RuntimeError("Existing Link peers detected; no tempo publisher started")
    results = []
    with tempfile.TemporaryDirectory(prefix="rmx-link-peer-") as directory:
        root = Path(directory)
        command, state = root / "command", root / "state"
        command.write_text("137\n")
        with subprocess.Popen(
            [probe, "--publish", command, state],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ) as publisher:
            try:
                deadline = time.monotonic() + 5
                while not state.exists():
                    if publisher.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("Publisher did not start")
                    time.sleep(0.05)
                for bpm in (137, 91, 30, 120):
                    pending = root / "new-command"
                    pending.write_text(f"{bpm}\n")
                    pending.replace(command)
                    result = subprocess.run(
                        [probe, "--compare", state, str(bpm)],
                        capture_output=True, text=True, check=True,
                    )
                    record = json.loads(result.stdout)
                    if not (record["passed"] and record["maximum_peers"] == 1
                            and record["stable_samples"] >= 20):
                        raise RuntimeError(f"Link comparison failed: {record}")
                    results.append(dict(requested_bpm=bpm, **record))
                command.write_text("stop\n")
                stdout, stderr = publisher.communicate(timeout=5)
                if publisher.returncode or stdout or stderr:
                    raise RuntimeError(f"Publisher failed: {stdout}{stderr}")
            finally:
                if publisher.poll() is None:
                    publisher.terminate()
                    try:
                        publisher.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        publisher.kill()
                        publisher.communicate()
    return dict(
        kind="rmx-link-network-validation", passed=True,
        separate_publisher_and_follower_processes=True,
        preflight=preflight, cases=results,
        scope="Local Link discovery, tempo and four-beat phase at two output "
              "timestamps; 30 BPM fallback and disabling. Does not establish "
              "rekordbox configuration or physical audio-loopback alignment.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("probe", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = json.dumps(check(args.probe.resolve()), indent=2) + "\n"
    if args.output:
        args.output.write_text(report)
    print(report, end="")
