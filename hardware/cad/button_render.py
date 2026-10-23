#!/usr/bin/env python3
"""Export B01 fit parts; check actual meshes and continuous rigid clearance."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from .paths import ARTIFACTS, update_previews
from .render import check_solid

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "generated"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad", default="openscad")
    parser.add_argument(
        "--update-previews",
        action="store_true",
        help="Update tracked documentation previews after successful checks",
    )
    args = parser.parse_args()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    version = subprocess.run([args.openscad, "--version"], text=True, capture_output=True, check=True)

    def run(options, empty=False):
        process = subprocess.run(
            [args.openscad, "--hardwarnings", *options, str(ROOT / "button_fixture.scad")],
            text=True,
            capture_output=True,
        )
        log = process.stdout + process.stderr
        if empty:
            if process.returncode != 1 or "Current top level object is empty." not in log:
                raise RuntimeError(f"Expected empty rigid-motion intersection:\n{log}")
        elif process.returncode:
            raise RuntimeError(log)

    report = dict(revision="B01", renderer=(version.stdout + version.stderr).strip(), solids={}, checks={})
    for name, part, settings in [
        (p, p, []) for p in ["key_pad", "key_nudge", "clip", "panel_pad", "panel_nudge"]
    ] + [
        ("guide_020", "guide", ["-D", "guide_clearance=0.2"]),
        ("guide_040", "guide", ["-D", "guide_clearance=0.4"]),
        ("guide_060", "guide", ["-D", "guide_clearance=0.6"]),
    ]:
        path = ARTIFACTS / ("button-" + name + ".stl")
        run(
            [
                "--backend",
                "CGAL",
                "--export-format",
                "binstl",
                "-o",
                str(path),
                "-D",
                f'part="{part}"',
                *settings,
            ]
        )
        report["solids"][name] = check_solid(path, "CGAL")
        print(f"{name}: one closed connected solid", flush=True)
    for sample in ["pad", "nudge"]:
        collision = ARTIFACTS / ("button-" + sample + "-collision.stl")
        run(
            [
                "--backend",
                "Manifold",
                "-o",
                str(collision),
                "-D",
                'part="collision"',
                "-D",
                f'sample="{sample}"',
            ],
            empty=True,
        )
        collision.unlink(missing_ok=True)
        report["checks"][sample + "_rigid_clearance"] = dict(
            result="empty intersection",
            travel_mm=[0, 1.2],
            method="separate continuous vertical sweeps of cap, filled D stem and filled clip envelope",
            intentional_stop_faces_excluded_mm=0.01,
            against=["nominal guide with 0.4 mm total clearance", "2 mm coupon panel"],
            excludes=[
                "intended switch/silicone contact",
                "return spring",
                "fasteners",
                "printed fit and friction",
            ],
        )
    for name, settings in [
        ("assembly", ["-D", 'part="assembly"']),
        ("section", ["-D", 'part="section"']),
        ("pressed", ["-D", 'part="pressed"']),
    ]:
        camera = "35,-50,35,0,0,0" if name == "assembly" else "-35,-50,15,0,0,-2"
        run(
            [
                "--backend",
                "Manifold",
                "--preview",
                "--imgsize",
                "1400,1000",
                "--camera",
                camera,
                "--autocenter",
                "--viewall",
                "--projection",
                "o",
                "--colorscheme",
                "Tomorrow Night",
                "-o",
                str(ARTIFACTS / ("button-" + name + ".png")),
                *settings,
            ]
        )
    report["source_hashes"] = {
        f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
        for f in [
            "button_fixture.scad",
            "button_fixture.py",
            "button_render.py",
            "paths.py",
            "generated/button-fixture.scad",
        ]
    }
    (OUT / "button-solid-validation.json").write_text(json.dumps(report, indent=2) + "\n")
    if args.update_previews:
        update_previews(["button-section", "button-pressed"])
    print("Eight B01 solids and both rigid sweeps passed; physical operation remains unverified.")


if __name__ == "__main__":
    main()
