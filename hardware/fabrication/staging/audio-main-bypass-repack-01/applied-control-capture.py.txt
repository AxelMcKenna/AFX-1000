"""Capture a verified partial audio board's native control connectivity."""

import argparse
import shutil
from pathlib import Path

from hardware.fabrication.audio_main_control_routes import CONTROL_NETS
from hardware.fabrication.audio_main_native_capture import capture


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--opens", required=True, type=int)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent / "staging"
    assert all(value and Path(value).name == value and value not in (".", "..") for value in (args.source, args.output))
    source, output = root / args.source, root / args.output
    assert source.is_dir() and args.opens >= 0
    output.mkdir(exist_ok=False)
    applied = output / "applied-control-capture.py.txt"
    shutil.copyfile(Path(__file__), applied)
    capture(source, output, args.opens, CONTROL_NETS, applied)


if __name__ == "__main__":
    run()
