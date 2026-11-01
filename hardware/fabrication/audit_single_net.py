"""Check a single-net copper replacement against exact saved native sources."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from hardware.electronics.common.netlists import netlist
from hardware.electronics.common.sexpr import first, read_sexpr, sexpr
from hardware.fabrication.audit_candidate import authored, geometry_delta, native_evidence_errors, sha

ROOT = Path(__file__).resolve().parent


def open_counts(report):
    result = Counter()
    for row in report["unconnected_items"]:
        names = [re.search(r"\[([^]]+)\]",item["description"]) for item in row["items"]]
        assert names and all(names)
        nets = {n.group(1) for n in names}
        assert len(nets) == 1
        result[nets.pop()] += 1
    return result


def unchanged_except_net(before,after,net):
    def selected(node):
        return isinstance(node,list) and node and node[0] in ("segment","via") and str(first(node,"net")[-1]) == net
    # Ignore only generated zone fill; the authored zones and all other objects
    # including original component/pad geometry must remain exact.
    return [authored(n) if isinstance(n,list) and n and n[0] == "zone" else sexpr(n)
            for n in before if not selected(n)] == [
                authored(n) if isinstance(n,list) and n and n[0] == "zone" else sexpr(n)
                for n in after if not selected(n)]


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before",required=True)
    parser.add_argument("--after",required=True)
    parser.add_argument("--net",required=True)
    args = parser.parse_args()
    for label in (args.before,args.after):
        assert label and all(c.isalnum() or c in "-_" for c in label)
    old,new = [ROOT/"staging"/n for n in (args.before,args.after)]
    output = new/"single-net-audit.json"
    assert not output.exists()
    projects = [next(p.glob("*.kicad_pro")) for p in (old,new)]
    reviews = [json.loads((p/"review.json").read_text()) for p in (old,new)]
    for project,review in zip(projects,reviews):
        assert not native_evidence_errors(project,review)
        assert review["status"]["counts"]["violations"] == review["status"]["counts"]["schematic_parity"] == 0
    assert reviews[0]["status"]["counts"]["erc"] == reviews[1]["status"]["counts"]["erc"]
    assert sha(projects[0]) == sha(projects[1])
    pcbs = [p.with_suffix(".kicad_pcb") for p in projects]
    trees = [read_sexpr(p.read_text()) for p in pcbs]
    assert unchanged_except_net(*trees,args.net)
    old_parts,old_pins = netlist(old/"netlist.xml")
    new_parts,new_pins = netlist(new/"netlist.xml")
    assert old_pins == new_pins and set(old_parts) == set(new_parts)
    assert all(all(old_parts[r].findtext(k) == new_parts[r].findtext(k) for k in ("value","footprint")) for r in old_parts)
    counts = [open_counts(json.loads((p/"drc.json").read_text())) for p in (old,new)]
    assert all(counts[1][n] <= counts[0][n] for n in counts[0].keys()|counts[1].keys())
    assert counts[1][args.net] < counts[0][args.net]
    assert all(counts[0][n] == counts[1][n] for n in counts[0].keys()|counts[1].keys() if n != args.net)
    inputs = [Path(__file__),*projects,*pcbs,*[p/name for p in (old,new) for name in ("review.json","drc.json","erc.json","netlist.xml")]]
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},
        replaced_net=args.net,delta=geometry_delta(*trees),per_net_opens_before=dict(sorted(counts[0].items())),
        per_net_opens_after=dict(sorted(counts[1].items())),all_other_authored_objects_exact=True,
        all_original_parts_pin_nets_values_and_footprint_IDs_exact=True,
        no_other_net_connectivity_regressions=True,native_status=reviews[1]["status"],
        physical_qualified=False,fabrication_released=False),indent=2)+"\n")
    print("Verified single-net improvement",args.net,sum(counts[0].values()),"to",sum(counts[1].values()))


if __name__ == "__main__":
    run()
