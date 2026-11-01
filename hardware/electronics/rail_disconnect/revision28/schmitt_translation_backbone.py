"""Reroute two ordinary buffered-backbone pieces around new U36 GND land."""

import hashlib
import json
import shutil
import uuid
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr
from .focused import legal_line
from .repair import Router

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/schmitt-receiver-translation-work"
WORK = ROOT / "generated/schmitt-translation-backbone-work"
IDS = {"9aa5e552-0544-5640-9349-f6e6897c554b", "20479c08-e60d-5d94-8586-6549521e3364"}


def main():
    assert not WORK.exists()
    blob = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    t = read_sexpr(blob.decode())
    names = {str(n[1]): str(n[2]).lstrip("/") for n in children(t, "net")}
    removed = []
    for n in list(children(t, "segment")):
        if str(first(n, "uuid")[1]) in IDS:
            assert names[str(first(n, "net")[1])] == "P19_OV_OK_SCHMITT" and first(n, "layer")[1] == "B.Cu"
            removed.append(sexpr(n))
            t.remove(n)
    assert len(removed) == 2
    rt = Router(t)
    net = "P19_OV_OK_SCHMITT"
    path = [(11.125, 12.5), (10.6, 12.275), (9.15, 12.275), (8.125, 11.25)]
    legal = [legal_line(rt, net, 5, p, q, 0.2) for p, q in zip(path, path[1:])]
    assert all(legal), legal
    rt.path(net, 5, path, 0.2)
    for i, n in enumerate(t):
        if isinstance(n, list) and n and n[0] in ("segment", "via") and not children(n, "uuid"):
            n.append(
                [
                    a("uuid"),
                    a(
                        str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                f"rmx:E28:translation-backbone:{hashlib.sha256(blob).hexdigest()}:{i}:{sexpr(n)}",
                            )
                        )
                    ),
                ]
            )
    WORK.mkdir()
    (WORK / "generated").mkdir()
    for p in SOURCE.iterdir():
        if p.is_file() and (
            p.suffix in (".kicad_pcb", ".kicad_sch", ".kicad_pro", ".kicad_sym")
            or p.name in ("components.json", "fp-lib-table", "sym-lib-table")
        ):
            shutil.copy2(p, WORK / p.name)
        elif p.suffix == ".pretty":
            shutil.copytree(p, WORK / p.name)
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(t) + "\n")
    (WORK / "generated/backbone-detour.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(blob).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                removed_two_ordinary_tracks=removed,
                added_real_B_copper_path=path,
                width_mm=0.2,
                all_fixed_pads_quiet_force_ground_and_other_original_Cu_preserved=True,
                no_new_drill=True,
                native_and_PDN_pending=True,
                physical_qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )
    print("Two actual buffered-signal pieces replaced with original-rule B-surface detour")


if __name__ == "__main__":
    main()
