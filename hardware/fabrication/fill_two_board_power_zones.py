"""Fill newly authored local planes in isolated Linux, preserving other syntax."""
import argparse
import copy
import json
import shutil
import sys
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    assert sys.platform=='linux'
    import pcbnew
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
    assert all(all(c.isalnum() or c in '-_' for c in n) for n in [args.source,args.output])
    source=STAGING/args.source;out=STAGING/args.output;assert not out.exists()
    paths=[Path(__file__),*[p for p in source.rglob('*') if p.is_file()]]
    hashes={str(p.relative_to(REPO)):sha(p) for p in paths}
    shutil.copytree(source,out)
    path=out/'power_protection.kicad_pcb';authored=read_sexpr(path.read_text());board=pcbnew.LoadBoard(str(path))
    zones=list(board.Zones());assert len(zones)==2 and all(not z.GetIsRuleArea() for z in zones)
    assert pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    export=out/'native-zone-export.kicad_pcb';pcbnew.SaveBoard(str(export),board)
    native=read_sexpr(export.read_text());filled={str(first(z,'uuid')[1]):z for z in children(native,'zone')}
    copied=0
    for z in children(authored,'zone'):
        assert not children(z,'filled_polygon')
        ps=children(filled[str(first(z,'uuid')[1])],'filled_polygon');assert ps
        z.extend(copy.deepcopy(ps));copied+=len(ps)
    path.write_text(sexpr(authored)+'\n')
    assert all(sha(REPO/p)==h for p,h in hashes.items())
    result=dict(source_sha256=hashes,artifact_sha256={p.name:sha(p) for p in [path,export]},
        native_version=pcbnew.GetBuildVersion(),filled_zones=2,filled_polygons=copied,
        only_native_zone_fill_copied_back=True,native_drc_pending=True,fabrication_released=False)
    (out/'local-plane-fill.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(zones=2,filled_polygons=copied)))

if __name__=='__main__':run()
