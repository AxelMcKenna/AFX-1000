#!/usr/bin/env python3
"""Remove only native-reported redundant vias/stubs; independent DRC must follow."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from ..common.placement import footprint_root
from ..common.sexpr import children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", required=True)
    args = parser.parse_args()
    cli = Path(args.kicad_cli).resolve()
    out = ROOT / "generated"
    pcb = ROOT / "input_protection.kicad_pcb"
    (out / "routing-verification.json").unlink(missing_ok=True)
    passes = []
    with tempfile.TemporaryDirectory(prefix="rmx-e23-clean-") as folder:
        temp = Path(folder)
        font = temp / "fonts.conf"
        font.write_text(
            f"<fontconfig><dir>/System/Library/Fonts</dir><cachedir>{temp}/cache</cachedir></fontconfig>"
        )
        env = dict(
            os.environ,
            KICAD_CONFIG_HOME=str(temp / "config"),
            FONTCONFIG_FILE=str(font),
            KICAD10_FOOTPRINT_DIR=str(footprint_root(str(cli))),
        )
        for iteration in range(8):
            r = subprocess.run(
                [
                    str(cli),
                    "pcb",
                    "drc",
                    "--refill-zones",
                    "--save-board",
                    "--all-track-errors",
                    "--schematic-parity",
                    "--severity-all",
                    "--format",
                    "json",
                    "-o",
                    str(out / "cleanup-drc.json"),
                    str(pcb),
                ],
                env=env,
                capture_output=True,
                text=True,
            )
            assert r.returncode == 0, (r.stdout, r.stderr)
            report = json.loads((out / "cleanup-drc.json").read_text())
            assert not report["unconnected_items"] and not report["schematic_parity"], (
                "Cleanup requires a fully connected, matching circuit"
            )
            assert all(v["type"] in ("via_dangling", "track_dangling") for v in report["violations"]), report[
                "violations"
            ][:5]
            if not report["violations"]:
                break
            ids = {i["uuid"] for v in report["violations"] for i in v["items"]}
            tree = read_sexpr(pcb.read_text())
            remove = [
                v
                for tag in ("via", "segment")
                for v in children(tree, tag)
                if str(first(v, "uuid")[1]) in ids
            ]
            assert len(remove) == len(ids) and all(first(v, "net")[1] != "/AGND" for v in remove)
            passes.append(
                dict(
                    pass_index=iteration,
                    removed_vias=sum(v[0] == "via" for v in remove),
                    removed_stubs=sum(v[0] == "segment" for v in remove),
                    native_reported_items=report["violations"],
                )
            )
            tree = [v for v in tree if v not in remove]
            pcb.write_text("(kicad_pcb\n" + "\n".join(sexpr(v) for v in tree[1:]) + "\n)\n")
        else:
            raise RuntimeError("Cleanup did not converge; inspect the board")
    (out / "cleanup.json").write_text(
        json.dumps(
            dict(
                revision="E23",
                passes=passes,
                native_issues_after_cleanup=0,
                independent_verification_still_required=True,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        f"E23 removed {sum(p['removed_vias'] for p in passes)} redundant vias and {sum(p['removed_stubs'] for p in passes)} stubs; independent all-severity DRC/refill still required."
    )


if __name__ == "__main__":
    main()
