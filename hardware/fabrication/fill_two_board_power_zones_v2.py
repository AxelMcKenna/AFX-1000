"""Fill added local planes while verifying and retaining existing native fills."""
import argparse
import copy
import json
import shutil
import sys
from pathlib import Path
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha
from hardware.fabrication.capture_partial_board import polygons

def canonical(polys):
    def ring(points):
        p=[tuple(v) for v in points]
        if p[0]==p[-1]:p.pop()
        versions=[]
        for q in [p,list(reversed(p))]:
            i=min(range(len(q)),key=lambda i:q[i:]+q[:i])
            versions.append(tuple(q[i:]+q[:i]))
        return min(versions)
    return sorted((ring(p['outer']),tuple(sorted(ring(h) for h in p['holes']))) for p in polys)



def run():
    assert sys.platform=='linux'
    import pcbnew
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--output',required=True);ap.add_argument('--expected-zones',type=int,required=True);args=ap.parse_args()
    assert all(all(c.isalnum() or c in '-_' for c in n) for n in [args.source,args.output])
    source=STAGING/args.source;out=STAGING/args.output;assert not out.exists()
    paths=[Path(__file__),*[p for p in source.rglob('*') if p.is_file()]]
    hashes={str(p.relative_to(REPO)):sha(p) for p in paths}
    shutil.copytree(source,out)
    path=out/'power_protection.kicad_pcb';authored=read_sexpr(path.read_text());board=pcbnew.LoadBoard(str(path))
    zones=list(board.Zones());assert len(zones)==args.expected_zones and all(not z.GetIsRuleArea() for z in zones)
    existing={}
    for z in zones:
        native_poly=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(z.GetLayer()))
        if native_poly.OutlineCount():
            native_poly.Unfracture()
            existing[z.m_Uuid.AsString()]=canonical(polygons(native_poly))
    assert pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    export=out/'native-zone-export.kicad_pcb';pcbnew.SaveBoard(str(export),board)
    native=read_sexpr(export.read_text());filled={str(first(z,'uuid')[1]):z for z in children(native,'zone')}
    existing_deltas={}
    for z in zones:
        ident=z.m_Uuid.AsString()
        if ident not in existing:continue
        poly=pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(z.GetLayer()));poly.Unfracture()
        actual=canonical(polygons(poly))
        assert existing[ident]==actual,ident
        existing_deltas[ident]=True
    copied=0
    for z in children(authored,'zone'):
        if children(z,'filled_polygon'):
            assert str(first(z,'uuid')[1]) in existing_deltas
            continue
        ps=children(filled[str(first(z,'uuid')[1])],'filled_polygon');assert ps
        z.extend(copy.deepcopy(ps));copied+=len(ps)
    path.write_text(sexpr(authored)+'\n')
    assert all(sha(REPO/p)==h for p,h in hashes.items())
    result=dict(source_sha256=hashes,artifact_sha256={p.name:sha(p) for p in [path,export]},
        native_version=pcbnew.GetBuildVersion(),filled_zones=len(zones),new_filled_polygons=copied,
        unchanged_existing_zone_canonical_polygon_match=existing_deltas,
        only_native_zone_fill_copied_back=True,native_drc_pending=True,fabrication_released=False)
    (out/'local-plane-fill.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(zones=len(zones),new_filled_polygons=copied,existing_zones_verified=len(existing_deltas))))

if __name__=='__main__':run()
