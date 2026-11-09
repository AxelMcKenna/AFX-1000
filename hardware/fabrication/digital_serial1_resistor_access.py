"""Exhaustive region probes for saved resistor poses; no PCB is emitted."""
import copy,json
from pathlib import Path
from hardware.fabrication.audit_candidate import sha
from hardware.fabrication.digital_region_point_access import reachability
from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_via_spacing_close_margin import CloseMarginViaScreen
from hardware.fabrication.digital_xlat_escape_repair import add
from hardware.fabrication.digital_serial1_packed_repair_v3 import contacts
from hardware.fabrication.digital_serial1_joint_repair import ROOT,FACES
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_minimum_logic as layers

def run():
    cp=ROOT/'staging/digital-bypass-ground-signal-inputs-31/capture.json'
    rp=ROOT/'staging/digital-serial1-data-cutset-01/diagnosis.json'
    pp=ROOT/'staging/digital-serial1-data-resistor-repack-02/diagnosis.json'
    cap,recipe,placement=[json.loads(p.read_text()) for p in (cp,rp,pp)]
    for r in (cap,recipe,placement):
        assert all(sha(Path(p))==h for p,h in r['source_sha256'].items())
    removed=set(placement['removed_uuids'])
    work=copy.deepcopy(cap)
    work['objects']=[o for o in cap['objects'] if o['uuid'] not in removed and o.get('ref')!='R3015']
    surface.WIDTH=layers.WIDTH=.2;surface.MARGIN=.001;surface.SIGNAL_LAYERS=FACES
    fixed=recipe['fixed_routes']+[recipe['serial_continuation']]
    screen=CloseMarginViaScreen(work,signal_layers=FACES)
    for r in fixed:add(screen,r['net'],dict(runs=r['runs'],vias=r['new_vias_mm']))
    rows=[]
    for net,ref,pin,posepin in [('/LED/DATA_5V_SRC','U3005','21','1'),('/LED/DATA_5V','U3001','4','2')]:
        ends=sorted(contacts(work,net,ref,pin))
        crossings=[(o['position_mm'],[f for f in FACES if o['layers'].get(f)]) for o in work['objects'] if o['net']==net and (o['kind']=='PCB_VIA' or o['kind']=='PAD' and any(o.get('drill_mm',[0,0])))]
        crossings += [(p,list(FACES)) for n,p in screen.new_vias if n==net]
        poses=[('B.Cu',next(p for p in pose['pads'] if p['pin']==posepin)['position_mm']) for pose in placement['legal_poses']]
        lattice=[(f,[58+x*.5,8+y*.5]) for f in ['B.Cu','F.Cu'] for x in range(53) for y in range(53)]
        report=reachability(PlannedRegionScreen(screen,net),net,ends,ends,FACES,existing_crossings=crossings,probes=poses+lattice)
        accepted=[i for i,p in enumerate(report['probe_results'][:len(poses)]) if p['connected_to_sources']]
        rows.append(dict(net=net,pose_indices_with_access=accepted,pose_probe_count=len(poses),region_report=report))
        print(net,'reachable poses',len(accepted),'of',len(poses),'lattice access',sum(p['connected_to_sources'] for p in report['probe_results'][len(poses):]),flush=True)
    jointly=sorted(set(rows[0]['pose_indices_with_access'])&set(rows[1]['pose_indices_with_access']))
    paths=[cp,rp,pp,Path(__file__)]+[ROOT/n for n in ('audit_candidate.py','digital_serial1_joint_repair.py','digital_serial1_packed_repair_v3.py','digital_latch_supply_repack.py','digital_region_point_access.py','digital_planned_region_screen.py','digital_via_spacing_close_margin.py','digital_via_spacing_v2.py','digital_xlat_escape_repair.py','route_nf_surface.py','nf_minimum_logic.py','nf_softstart_joint_screen.py','nf_softstart_cell_routes.py')]
    out=ROOT/'staging/digital-serial1-resistor-access-01';out.mkdir(exist_ok=False)
    (out/'diagnosis.json').write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in paths},results=rows,pose_indices_with_both_access=jointly,proposed_pads_not_yet_added=True,access_is_necessary_not_sufficient=True,candidate_emitted=False,fabrication_released=False),indent=2)+'\n')
    print('Both terminal regions accessible:',jointly,flush=True)

if __name__=='__main__':run()
