"""Independent circuit/copper/pad-connection audit of the local SS/TMR cell."""
import json
import math
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.electronics.common.netlists import netlist
from hardware.fabrication.audit_candidate import geometry_delta,native_evidence_errors,sha
from hardware.fabrication.audit_single_net import open_counts

ROOT=Path(__file__).resolve().parent
MOVED={'C53','C54'}
ALLOWED={'/N12_SS','/N12_TMR','/N12_P03_SRC','/N12_VIN','/NF_NO_FAULT'}


def verify_geometry(before,after,removed):
    d=geometry_delta(before,after)
    refs={first(f,'uuid')[1]:next(p[2] for p in children(f,'property') if p[1]=='Reference') for f in children(before,'footprint')}
    assert d['other_root_geometry_exact'] and not any(d['zone'].values())
    assert not d['footprint']['added'] and not d['footprint']['removed']
    assert {refs[k] for k in d['footprint']['changed']}==MOVED
    assert len(removed)==20
    for tag in ['segment','via']:
        old={first(n,'uuid')[1]:n for n in children(before,tag)}
        new={first(n,'uuid')[1]:n for n in children(after,tag)}
        permit={first(n,'uuid')[1]:n for n in removed if n[0]==tag}
        assert not d[tag]['changed'] and set(d[tag]['removed'])==set(permit)
        assert all(old[k]==n and first(n,'net')[-1] in {'/N12_P03_SRC','/N12_VIN','/NF_NO_FAULT'} for k,n in permit.items())
        for k in d[tag]['added']:
            n=new[k];assert first(n,'net')[-1] in ALLOWED
            if tag=='segment':assert float(first(n,'width')[1])>=.2
            else:assert float(first(n,'size')[1])==.6 and float(first(n,'drill')[1])==.3
    return d


def verify_connections(before,after):
    pads=[{(o['ref'],o['pin']):o for o in c['objects'] if o['kind']=='PAD'} for c in [before,after]]
    assert pads[0].keys()==pads[1].keys()
    partitions={}
    for key,pad in pads[0].items():
        assert pad['net']==pads[1][key]['net']
        if key[0] not in MOVED:partitions.setdefault((pad['net'],pad['group']),[]).append(key)
    for keys in partitions.values():assert len({pads[1][k]['group'] for k in keys})==1,keys
    for cap,pin in [('C53','19'),('C54','20')]:
        x,y=pads[1][cap,'1'],pads[1]['U23',pin]
        assert x['net']==y['net'] and x['group']==y['group']
        x,y=pads[1][cap,'2'],pads[1]['U23','23']
        assert x['net']==y['net']=='/N12_P03_SRC' and x['group']==y['group']
    return pads


def run():
    folders=[ROOT/'staging'/n for n in ['nf-ct-local-native-01','nf-softstart-cell-native-02']]
    projects=[f/'negative_startup_physical.kicad_pro' for f in folders]
    for p in projects:
        r=json.loads((p.parent/'review.json').read_text());assert not native_evidence_errors(p,r)
        assert r['status']['counts']['violations']==r['status']['counts']['schematic_parity']==0
        assert r['status']['counts']['erc']==2
    assert sha(projects[0])==sha(projects[1])
    boards=[read_sexpr(p.with_suffix('.kicad_pcb').read_text()) for p in projects]
    construction=ROOT/'staging/nf-softstart-cell-routes-01/construction.json'
    plan_path=ROOT/'staging/nf-remote-timing-plan-01/plan.json'
    removed=json.loads(construction.read_text())['removed_leaf_objects']
    plan=json.loads(plan_path.read_text())
    displaced={t['uuid'] for r in plan['placements'] if r['selected']['ref'] in MOVED for t in r['selected']['displaced_logic_tracks']}
    removed += [n for n in children(boards[0],'segment') if first(n,'uuid')[1] in displaced]
    delta=verify_geometry(*boards,removed)
    parts=[netlist(f/'netlist.xml') for f in folders]
    assert parts[0][1]==parts[1][1] and parts[0][0].keys()==parts[1][0].keys()
    assert all(parts[0][0][r].findtext(k)==parts[1][0][r].findtext(k) for r in parts[0][0] for k in ['value','footprint'])
    counts=[open_counts(json.loads((f/'drc.json').read_text())) for f in folders]
    assert (sum(counts[0].values()),sum(counts[1].values()))==(166,163)
    assert all(counts[1][n]<=counts[0][n] for n in counts[0].keys()|counts[1].keys())
    paths=[ROOT/'staging'/n/'capture.json' for n in ['nf-ct-local-inputs-166','nf-softstart-cell-inputs-163']]
    captures=[json.loads(p.read_text()) for p in paths]
    for c,p in zip(captures,projects):
        assert all(sha(Path(k))==h for k,h in c['source_sha256'].items())
        assert str(p.with_suffix('.kicad_pcb')) in c['source_sha256']
    pads=verify_connections(*captures);timing=[]
    for cap,pin in [('C53','19'),('C54','20')]:
        timing.append(dict(cap=cap,owner='U23',owner_pin=pin,
                           projected_pad_distance_before_mm=math.dist(pads[0][cap,'1']['position_mm'],pads[0]['U23',pin]['position_mm']),
                           projected_pad_distance_after_mm=math.dist(pads[1][cap,'1']['position_mm'],pads[1]['U23',pin]['position_mm']),
                           timing_and_local_reference_connected=True))
    changed_counts={n:[counts[0][n],counts[1][n]] for n in counts[0].keys()|counts[1].keys() if counts[0][n]!=counts[1][n]}
    inputs=[Path(__file__),ROOT/'audit_candidate.py',ROOT/'audit_single_net.py',construction,plan_path,*paths,*projects,
            *[p.with_suffix('.kicad_pcb') for p in projects],*[f/n for f in folders for n in ['review.json','netlist.xml','drc.json','erc.json']]]
    output=folders[1]/'softstart-cell-audit.json';assert not output.exists()
    output.write_text(json.dumps(dict(source_sha256={str(p):sha(p) for p in inputs},geometry_delta=delta,
        original_circuit_values_packages_pin_nets_and_rules_exact=True,all_unmoved_pad_connections_preserved=True,
        original_outline_thickness_layers_and_authored_zones_exact=True,all_retained_original_copper_exact=True,
        local_reference_preserved=True,only_C53_C54_moved=True,opens_before=166,opens_after=163,
        no_per_net_regressions=True,changed_net_open_counts=changed_counts,timing_cells=timing,
        new_trace_width_mm=.2,new_via_dimensions_mm=[.6,.3],fault_status_detour_requires_timing_noise_review=True,
        installed_receiving_qualified=False,PDN_timing_noise_qualified=False,fabrication_released=False),indent=2)+'\n')
    print('Verified 166 -> 163:',changed_counts,'all unmoved pad connections preserved')


if __name__=='__main__':run()
