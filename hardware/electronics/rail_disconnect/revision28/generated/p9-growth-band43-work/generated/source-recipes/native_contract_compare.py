"""Compare complete normalized footprint/pad and zone contracts after SES import.

Run comparison with KiCad Python. Both input boards pass through the same native
SaveBoard serializer before semantic comparison; filled polygons, render caches
and UUID/path metadata are excluded. Actual copper/mask/paste/drill/body geometry
and electrical pad identities remain part of the contract.
"""

import argparse
import hashlib
import json
import tempfile
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ...common.sexpr import Atom, children, first, read_sexpr

VOLATILE = {
    "uuid",
    "tstamp",
    "path",
    "sheetname",
    "sheetfile",
    "render_cache",
    "filled_polygon",
    "fill_segments",
    "filled_areas_thickness",
    "embedded_fonts",
    "locked",
}


def canonical(node):
    if not isinstance(node, list):
        if isinstance(node, Atom):
            try:
                number = Decimal(node)
                if number.is_finite():
                    return ["number", str(number.normalize()) if number else "0"]
            except InvalidOperation:
                pass
            return ["atom", str(node)]
        return ["text", node]
    if not node or str(node[0]) in VOLATILE:
        return None
    atoms = [
        canonical(x)
        for x in node
        if not isinstance(x, list) and not (isinstance(x, Atom) and str(x) == "locked")
    ]
    nested = [canonical(x) for x in node if isinstance(x, list)]
    nested = [x for x in nested if x is not None]
    # Coordinate/control-point sequences retain their exact order. Record
    # attributes may be reordered by the native writer without changing them.
    if str(node[0]) not in ("pts", "layers"):
        nested.sort(key=lambda x: json.dumps(x, sort_keys=True))
    return [atoms, nested]


def fingerprint(node):
    return hashlib.sha256(json.dumps(canonical(node), sort_keys=True).encode()).hexdigest()


def contracts(tree):
    footprints = {}
    for fp in children(tree, "footprint"):
        ref = next(p[2] for p in children(fp, "property") if p[1] == "Reference")
        assert ref not in footprints, "Duplicate footprint reference"
        pads = children(fp, "pad")
        body = [x for x in fp if not (isinstance(x, list) and x and x[0] == "pad")]
        footprints[ref] = dict(
            full=fingerprint(fp),
            body=fingerprint(body),
            # Counter preserves repeated logical pad numbers and paste-only
            # custom apertures instead of silently overwriting them by number.
            pads=Counter(fingerprint(pad) for pad in pads),
            pad_count=len(pads),
        )
    zones = Counter(fingerprint(zone) for zone in children(tree, "zone"))
    edges = Counter(
        fingerprint(node)
        for node in tree
        if isinstance(node, list)
        and node
        and str(node[0]).startswith("gr_")
        and children(node, "layer")
        and first(node, "layer")[1] == "Edge.Cuts"
    )
    stack = [
        canonical(node)
        for node in tree
        if isinstance(node, list) and node and node[0] in ("layers", "general", "setup")
    ]
    return dict(footprints=footprints, zones=zones, edge_cuts=edges, board_setup=stack)


def differences(before, after):
    a, b = contracts(before), contracts(after)
    refs = sorted(set(a["footprints"]) | set(b["footprints"]))
    missing = [ref for ref in refs if ref not in b["footprints"]]
    extra = [ref for ref in refs if ref not in a["footprints"]]
    body, pads, full = [], [], []
    for ref in refs:
        if ref not in a["footprints"] or ref not in b["footprints"]:
            continue
        x, y = a["footprints"][ref], b["footprints"][ref]
        if x["body"] != y["body"]:
            body.append(ref)
        if x["pads"] != y["pads"]:
            pads.append(ref)
        if x["full"] != y["full"]:
            full.append(ref)
    report = dict(
        missing_footprints=missing,
        extra_footprints=extra,
        changed_footprint_bodies_or_attributes=body,
        changed_pad_contracts=pads,
        changed_complete_footprints=full,
        zone_contract_equal=a["zones"] == b["zones"],
        edge_cuts_equal=a["edge_cuts"] == b["edge_cuts"],
        board_setup_equal=a["board_setup"] == b["board_setup"],
        original_footprints=len(a["footprints"]),
        candidate_footprints=len(b["footprints"]),
        original_pad_shapes=sum(x["pad_count"] for x in a["footprints"].values()),
        candidate_pad_shapes=sum(x["pad_count"] for x in b["footprints"].values()),
        original_zones=sum(a["zones"].values()),
        candidate_zones=sum(b["zones"].values()),
    )
    report["contracts_equal"] = not any((missing, extra, body, pads, full)) and all(
        report[key] for key in ("zone_contract_equal", "edge_cuts_equal", "board_setup_equal")
    )
    return report


def compare(original, candidate):
    import pcbnew

    with tempfile.TemporaryDirectory(prefix="rmx-e28-contract-") as directory:
        normalized = []
        for index, path in enumerate((original, candidate)):
            destination = Path(directory) / (str(index) + ".kicad_pcb")
            board = pcbnew.LoadBoard(str(path))
            pcbnew.SaveBoard(str(destination), board)
            normalized.append(destination.read_bytes())
        report = differences(*(read_sexpr(blob.decode()) for blob in normalized))
    report.update(
        method="Both inputs normalized by the same KiCad SaveBoard; semantic complete footprint/pad/body, zone, edge and board-setup comparison",
        kicad_version=pcbnew.GetBuildVersion(),
        original_pcb_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
        candidate_pcb_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
        normalized_input_sha256=[hashlib.sha256(blob).hexdigest() for blob in normalized],
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        excluded_metadata_and_caches=sorted(VOLATILE),
        physical_qualified=False,
        limitations=[
            "Does not compare routed tracks/vias; the source-bound protected-copper lock contract is a separate required check.",
            "Zone-outline equality does not imply filled-force-copper preservation; native filled-polygon comparison is separate.",
            "No resistance, startup, SOA, thermal, fit, dynamic or fabrication acceptance follows.",
        ],
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--require-match", action="store_true")
    args = parser.parse_args()
    result = compare(args.original, args.candidate)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Complete footprint/pad/zone contracts equal:", result["contracts_equal"])
    if args.require_match:
        assert result["contracts_equal"], "Physical/electrical source contract changed"
