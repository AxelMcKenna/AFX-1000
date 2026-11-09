"""Explicitly refill the additional In4 zone after native rounding changed its fill."""
import json,shutil
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr,sexpr
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape

def run():
 source=STAGING/'two-board-power-digital-startup-01';out=STAGING/'two-board-power-digital-startup-02';assert not out.exists()
 evidence=STAGING/'two-board-power-digital-startup-filled-01/unexpected-fill-delta.json';d=json.loads(evidence.read_text())
 for n,h in d['source_sha256'].items():assert sha(REPO/n)==h,n
 changed=[z for z in d['zones'] if not z['canonical_match']];assert len(changed)==1
 z=changed[0];u=z['uuid'];assert u=='787e0385-5c4c-5b8f-9a2a-017054f7da0e'
 a,b=shape(z['before']),shape(z['after']);delta=a.symmetric_difference(b).area;distance=a.hausdorff_distance(b)
 assert delta<1e-6 and distance<2e-6,(delta,distance)
 sources=[Path(__file__),evidence,*[p for p in source.rglob('*') if p.is_file()]]
 shutil.copytree(source,out);path=out/'power_protection.kicad_pcb';board=read_sexpr(path.read_text());zone=next(z for z in children(board,'zone') if str(first(z,'uuid')[1])==u)
 assert children(zone,'filled_polygon');zone[:]=[n for n in zone if not(isinstance(n,list) and n and n[0]=='filled_polygon')]
 path.write_text(sexpr(board)+'\n');rp=out/'digital-startup-routing.json';r=json.loads(rp.read_text());assert u not in r['refilled_existing_zones'];r['refilled_existing_zones'].append(u)
 r['source_sha256'].update({str(p.relative_to(REPO)):sha(p) for p in sources})
 r['additional_refill_evidence']=dict(uuid=u,outline_unchanged=True,reason='Native refill changes a retained fill at integer-grid fracture boundaries; explicitly refill and audit it.',symmetric_difference_area_mm2=delta,hausdorff_distance_mm=distance)
 rp.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['additional_refill_evidence']))
if __name__=='__main__':run()
