"""Remove only external-power assertions superseded by real integrated sources."""
import json
import shutil
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, sha

SOURCE = STAGING / "two-board-power-integration-01"
OUT = STAGING / "two-board-power-integration-02"
REMOVED = {
    "E": {"#E_FLAG0":"P_U7.1", "#E_FLAG2":"P_U8.3", "#E_FLAG4":"P_U22.10",
          "#E_FLAG5":"#P_FLAG3", "#E_FLAG6":"P_U102.1", "#E_FLAG7":"#P_FLAG1"},
    "M": {"#M_FLAG2":"#P_FLAG1"},
    "N": {"#N_FLAG0":"#P_FLAG1", "#N_FLAG2":"F_U401.6", "#N_FLAG4":"P_U10.1", "#N_FLAG5":"P_U11.1"},
    "F": {"#F_FLAG0":"#P_FLAG3", "#F_FLAG1":"#P_FLAG1"},
}


def build():
    assert not OUT.exists()
    erc_path = STAGING / "two-board-power-native-01/erc.json"
    erc = json.loads(erc_path.read_text())
    conflicts = [v for s in erc["sheets"] for v in s.get("violations",[]) if v["type"] == "pin_to_pin"]
    assert len(conflicts) == 13
    paths = [Path(__file__),erc_path,*[p for p in SOURCE.rglob("*") if p.is_file()]]
    shutil.copytree(SOURCE,OUT)
    changes = []
    for role, flags in REMOVED.items():
        path = next(OUT.glob(role+"_*.kicad_sch"))
        tree = read_sexpr(path.read_text())
        for ref, driver in flags.items():
            symbol = next(s for s in children(tree,"symbol") if prop(s,"Reference")[2] == ref)
            at = first(symbol,"at")[1:3]
            own_labels = [l for l in children(tree,"label")+children(tree,"global_label") if first(l,"at")[1:3] == at]
            assert len(own_labels) == 1 and own_labels[0][0] == "global_label",ref
            # All retained source power flags have a direct label, no wire stub.
            assert not [w for w in children(tree,"wire") if any(x[1:3] == at for x in children(first(w,"pts"),"xy"))],ref
            assert any(any(i["description"].startswith("Symbol "+ref+" Pin ") for i in v["items"]) for v in conflicts),ref
            tree.remove(symbol)
            tree.remove(own_labels[0])
            changes.append(dict(nonphysical_flag=ref,net=own_labels[0][1],retained_driver=driver))
        path.write_text(sexpr(tree)+"\n")
    assert len(changes) == 13
    record = json.loads((SOURCE/"construction.json").read_text())
    record["source_sha256"] = {str(p.relative_to(REPO)):sha(p) for p in paths}
    record["superseded_nonphysical_power_flags"] = changes
    record["source_isolated_reference_warnings_not_suppressed"] = True
    (OUT/"construction.json").write_text(json.dumps(record,indent=2)+"\n")
    print("Removed 13 superseded external-power flags and their own direct labels; all physical components retained")


if __name__ == "__main__":
    build()
