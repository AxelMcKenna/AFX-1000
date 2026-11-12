"""Check native footprint evidence and source identity, retaining real rule conflicts."""
import hashlib,json
from pathlib import Path
from shapely.geometry import box
HERE=Path(__file__).resolve().parent

def verify(here=HERE):
    m=json.loads((here/'footprints.json').read_text());n=json.loads((here/'native/native-footprints.json').read_text())
    expected={p.name:p for p in (here/'AUX_READY.pretty').glob('*.kicad_mod')}
    assert set(expected)=={r['file'] for r in n['footprints']},'Native footprint file set changed'
    expected_pins={'TI_DQC0010A':11,'TI_DSE0006A':6,'TI_DBV0005A':5,'Coilcraft_XAL4040':2,'Vishay_CRCW2512':2,'KEMET_D_7343_LevelB':2}
    minima={}
    for r in n['footprints']:
        assert hashlib.sha256(expected[r['file']].read_bytes()).hexdigest()==r['sha256'],'Stale native footprint'
        name=Path(r['file']).stem; pads=r['pads']
        assert len(pads)==expected_pins[name] and {p['number'] for p in pads}=={str(i) for i in range(1,expected_pins[name]+1)},'Unexpected pad set'
        boxes=[]
        for p in pads:
            x,y=p['at_mm'];w,h=p['size_mm'];boxes.append(box(x-w/2,y-h/2,x+w/2,y+h/2))
        minima[name]=min(a.distance(b) for i,a in enumerate(boxes) for b in boxes[i+1:])
    for p in m['parts']:
        assert hashlib.sha256((here.parent/p['source']).read_bytes()).hexdigest()==p['source_sha256'],'Source drift'
    assert abs(minima['TI_DSE0006A']-.15)<1e-8
    assert all(v>0 for v in minima.values())
    return dict(native_load_pass=True,source_hashes_match=True,minimum_adjacent_pad_copper_gap_mm=minima,unresolved_rule_conflicts=['TI_DSE0006A 0.15 mm copper gap versus TBP72 general 0.20 mm rule'],pcb_modified=False,fabrication_qualified=False)
if __name__=='__main__':
    (HERE/'verification.json').write_text(json.dumps(verify(),indent=2)+'\n')
