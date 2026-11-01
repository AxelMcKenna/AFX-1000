"""Remove external pin-one silk triangles; electrical/manufacturing pads stay exact."""

import hashlib
import json
from pathlib import Path

from hardware.electronics.common.sexpr import first, read_sexpr, sexpr

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = ROOT / "NF03P_Layout.pretty"
    folder.mkdir(exist_ok=True)
    records = {}
    for original in ["Package_TO_SOT_SMD:SOT-363_SC-70-6", "Package_TO_SOT_SMD:SOT-23-5"]:
        alias = original.replace(":", "__")
        source = ROOT / "sources/footprints" / (alias + ".kicad_mod")
        fp = read_sexpr(source.read_text())
        removed = [node for node in fp if isinstance(node, list) and node and node[0] == "fp_poly" and first(node, "layer")[1] == "F.SilkS"]
        assert removed, original
        fp = [node for node in fp if node not in removed]
        fp[1] = alias + "_LocalSilk"
        target = folder / (fp[1] + ".kicad_mod")
        target.write_text(sexpr(fp) + "\n")
        records[original] = dict(alias=fp[1], original_sha256=sha(source),
            local_sha256=sha(target), removed_external_pin1_polygons=removed,
            pads_courtyards_mask_paste_and_Fab_unmodified=True,
            manufacturer_land_acceptance_inferred=False)
    (ROOT / "generated/layout-silk.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
