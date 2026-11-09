"""Capture native front/back orientations of the existing R3015 footprint."""
import json,sys
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.capture_board import polygons
ROOT=Path(__file__).resolve().parent

def run():
    assert sys.platform=='linux','Mac CAD remains disabled'
    import pcbnew
    source=ROOT/'staging/digital-eight-serial-native-01/digital_core.kicad_pcb'
    out=ROOT/'staging/digital-data-series-templates-01';out.mkdir(exist_ok=False)
    records=[]
    for side in ['F','B']:
        for angle in [0,90,180,270]:
            board=pcbnew.LoadBoard(str(source));fp=next(f for f in board.GetFootprints() if f.GetReference()=='R3015')
            if fp.IsFlipped()!=(side=='B'):fp.Flip(fp.GetPosition(),False)
            fp.SetOrientationDegrees(angle);fp.SetPosition(pcbnew.VECTOR2I(0,0))
            temp=out/'template-work.kicad_pcb';assert pcbnew.SaveBoard(str(temp),board)
            tree=read_sexpr(temp.read_text());node=next(f for f in children(tree,'footprint') if any(p[1:3]==['Reference','R3015'] for p in children(f,'property')))
            name=f'R3015-{side}-{angle}.kicad_mod';(out/name).write_text(sexpr(node)+'\n')
            pads=[]
            for pad in fp.Pads():
                poly=pcbnew.SHAPE_POLY_SET();pad.TransformShapeToPolygon(poly,pad.GetLayer(),0,1000,pcbnew.ERROR_OUTSIDE)
                pads.append(dict(uuid=pad.m_Uuid.AsString(),pin=pad.GetNumber(),net=pad.GetNetname(),position_mm=[pad.GetPosition().x/1e6,pad.GetPosition().y/1e6],polygons=polygons(poly)))
            records.append(dict(side=side,angle=angle,file=name,sha256=sha(out/name),pads=pads))
    (out/'templates.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in [source,Path(__file__),ROOT/'capture_board.py']},templates=records,physical_qualified=False),indent=2)+'\n')
    print('Captured eight native R3015 orientation templates')
if __name__=='__main__':run()
