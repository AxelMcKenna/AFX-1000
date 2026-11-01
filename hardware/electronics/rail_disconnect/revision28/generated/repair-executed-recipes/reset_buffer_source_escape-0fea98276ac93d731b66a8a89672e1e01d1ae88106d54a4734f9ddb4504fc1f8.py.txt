"""Restore the exact unchanged U19 package escape on its new raw RESET net."""

import copy
import hashlib
import json
import shutil
from pathlib import Path

from ...common.sexpr import a, children, first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "generated/reset-triple-ready-reconnect1-work"
ORIGINAL = ROOT / "generated/timeout-pullup-placement-work"
WORK = ROOT / "generated/reset-triple-source-escape-work"


def main():
    assert not WORK.exists()
    data = (SOURCE / "rail_disconnect.kicad_pcb").read_bytes()
    tree = read_sexpr(data.decode())
    old = read_sexpr((ORIGINAL / "rail_disconnect.kicad_pcb").read_text())
    code = next(n[1] for n in children(tree, "net") if n[2] == "/E28_AUX_RESET_RAW")
    ids = {
        "e793736a-fc80-53f5-ab99-8a2ad286995a",
        "e5b7c8ac-dd78-5cf1-8bf0-dced20fb6706",
        "c28e0ce7-4ffc-5674-9baf-13609dde8557",
        "d8c9ecde-cf64-5342-81d4-1ee8617e0476",
        "e74e9828-e74b-5ce5-99e0-bcd52887c7fa",
    }
    restored = []
    for n in old:
        if (
            not isinstance(n, list)
            or not n
            or n[0] not in ("segment", "via")
            or str(first(n, "uuid")[1]) not in ids
        ):
            continue
        assert not any(
            str(first(q, "uuid")[1]) == str(first(n, "uuid")[1])
            for k in ("segment", "via")
            for q in children(tree, k)
        )
        q = copy.deepcopy(n)
        first(q, "net")[1] = a(str(code))
        tree.append(q)
        restored.append(dict(original=sexpr(n), new=sexpr(q)))
    assert len(restored) == 5
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
    (WORK / "rail_disconnect.kicad_pcb").write_text(sexpr(tree) + "\n")
    (WORK / "generated/restored-U19-escape.json").write_text(
        json.dumps(
            dict(
                source_pcb_sha256=hashlib.sha256(data).hexdigest(),
                original_pcb_sha256=hashlib.sha256(
                    (ORIGINAL / "rail_disconnect.kicad_pcb").read_bytes()
                ).hexdigest(),
                recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                restored=restored,
                only_declared_control_net_changed=True,
                qualified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
