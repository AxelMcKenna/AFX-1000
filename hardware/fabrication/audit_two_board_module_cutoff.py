"""Independent native TBP10 pin, package, preserved-circuit and corner audit."""
import copy
import itertools
import json
import math
from pathlib import Path

from hardware.electronics.common.sexpr import children, first, read_sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.native_two_board_power import partition
from hardware.fabrication.audit_two_board_power_delta import geometry
from hardware.fabrication.audit_two_board_enable_recovery import check_uv
from hardware.fabrication.audit_two_board_fault_mask import evaluate
from hardware.fabrication.audit_two_board_source_sense import verify_sense

BASE = STAGING/'two-board-power-native-06'
OUT = STAGING/'two-board-power-native-10'


def branch(parts, p):
    assert parts['G_U1'].findtext('value') == 'TPS26601RHFR'
    assert parts['G_U1'].findtext('footprint') == 'TBP09_Module:TI_RHF0024A'
    assert parts['G_R5'].findtext('value') == '22.1k 0.1% 25ppm'
    for r in ['G_C3', 'G_C4']:
        assert parts[r].findtext('value') == '100nF25V C0G C1206C104J3GACTU'
        assert parts[r].findtext('footprint') == 'TB05_N_NF06P:PROPOSED_KEMET1206_LevelB'
    def same(*nodes):
        nets = {p[(r, str(n))] for r, n in nodes}
        assert len(nets) == 1, (nodes, nets)
    same(('G_U1',8),('G_U1',9),('P_U101',17),('P_U101',18),('P_C103',1),
         ('G_C1',1),('G_D1',1),('G_R1',1),('G_R3',1))
    same(('G_U1',23),('G_U1',24),('N_U17',2),('N_U22',2),('N_C4',1),
         ('N_C31',1),('N_J6',1),('G_C2',1),('G_D2',1))
    same(('G_U1',17),('G_NT1',2),('N_U17',1),('N_U22',1),('N_C4',2),
         ('N_C31',2),('N_J6',2),('G_C1',2),('G_C2',2),('G_D1',2),('G_D2',2))
    same(('G_U1',15),('G_U1',25),('G_R2',2),('G_R4',2),('G_R5',2),('G_C3',2),('G_C4',2))
    same(('G_NT1',1),('P_C103',2),('P_U101',8))
    same(('G_U1',10),('G_R1',2),('G_R2',1))
    same(('G_U1',12),('G_R3',2),('G_R4',1))
    same(('G_U1',19),('G_R5',1))
    same(('G_U1',20),('G_C3',1),('G_C4',1))
    representatives = [('G_U1',n) for n in [8,23,17,15,10,12,19,20]] + [('G_NT1',1)]
    nc = list(range(1,8)) + [11,13,14,16,18,21,22]
    for pin in nc:
        net = p[('G_U1',str(pin))]
        assert net.startswith('unconnected-')
        assert [node for node, value in p.items() if value == net] == [('G_U1',str(pin))]
    distinct = [p[(r,str(n))] for r,n in representatives] + [p[('G_U1',str(n))] for n in nc]
    assert len(set(distinct)) == len(distinct)
    assert p[('G_U1','8')] not in [p[('P_U101','1')],p[('N_J1','6')],p[('E_U29','7')]]
    assert {n for n,v in p.items() if n[0].startswith('G_') and v == p[('P_C103','2')]} == {('G_NT1','1')}
    for ref in ['N_U17','N_U22']:
        assert parts[ref].findtext('value') == 'TMR 1-1215'


def package(f):
    # TI RHF0024A 4219064/A: top-view terminal numbering, land and stencil.
    expected = {}
    for pin,y in enumerate([-1.5,-1,-.5,0,.5,1,1.5],1): expected[str(pin)] = (-1.9,y,.6,.24)
    for pin,x in enumerate([-1,-.5,0,.5,1],8): expected[str(pin)] = (x,2.4,.24,.6)
    for pin,y in enumerate([1.5,1,.5,0,-.5,-1,-1.5],13): expected[str(pin)] = (1.9,y,.6,.24)
    for pin,x in enumerate([1,.5,0,-.5,-1],20): expected[str(pin)] = (x,-2.4,.24,.6)
    expected['25'] = (0,0,2.65,3.65)
    numbered = [p for p in children(f,'pad') if p[1]]
    assert len(numbered) == 25
    for p in numbered:
        actual = tuple(map(float,first(p,'at')[1:3]+first(p,'size')[1:3]))
        assert actual == expected[str(p[1])], (p[1],actual)
        assert first(p,'layers')[1:] == (['F.Cu','F.Mask'] if p[1]=='25' else ['F.Cu','F.Mask','F.Paste'])
        assert abs(float(first(p,'roundrect_rratio')[1])*min(actual[2:])-.05)<1e-8
    paste = [p for p in children(f,'pad') if not p[1]]
    wanted = [(x,y,1.17,1.04) for x in [-.685,.685] for y in [-1.24,0,1.24]]
    actual = [tuple(map(float,first(p,'at')[1:3]+first(p,'size')[1:3])) for p in paste]
    assert sorted(actual) == sorted(wanted)
    assert all(first(p,'layers')[1:]==['F.Paste'] for p in paste)
    assert float(first(f,'solder_mask_margin')[1]) == .05
    return dict(numbered_copper_pads=25,exposed_pad_paste_windows=6,land_and_stencil_dimensions_match=True,
        drawing='TI RHF0024A 4219064/A',thermal_RTN_vias_implemented=False,board_process_accepted=False)


def numerical(parts):
    def ohms(r):
        v=parts[r].findtext('value').split()[0]
        return float(v.rstrip('k'))*(1000 if v.endswith('k') else 1)
    corners={}
    for name,bottom,limits in [('UV_on','G_R2',[1.175,1.225]),('UV_off','G_R2',[1.08,1.125]),
        ('OV_off','G_R4',[1.17,1.225]),('OV_reenable','G_R4',[1.085,1.125])]:
        top='G_R1' if bottom=='G_R2' else 'G_R3'
        vs=[]
        for threshold,ts,bs,leak in itertools.product(limits,[.995,1.005],[.995,1.005],[-1e-7,1e-7]):
            rt,rb=ohms(top)*ts,ohms(bottom)*bs
            vin=threshold+rt*(threshold/rb+leak)
            assert abs((vin-threshold)/rt-threshold/rb-leak)<1e-15
            vs.append(vin)
        corners[name]=[min(vs),max(vs)]
    c=sum(float(parts[r].findtext('value').split('nF')[0])*1e-9 for r in ['G_C3','G_C4'])
    slew=[23.75*4e-6/(c*1.06),25.5*5.5e-6/(c*.94)]
    current=12000/ohms('G_R5')
    modeled_low=current*.85/1.005-.055
    startup=.35+60e-6*slew[1]
    assert startup<modeled_low
    assert corners['UV_on'][1]<11.4 and corners['OV_reenable'][0]>12.6
    steady_floor=corners['UV_off'][0]-.1-.01-.35*.25
    assert steady_floor>9 and corners['OV_off'][1]<18
    authored=json.loads((OUT/'module-cutoff-design.json').read_text())
    for key,value in corners.items():
        assert all(math.isclose(a,b,rel_tol=1e-12) for a,b in zip(value,authored['input_divider_limits_v'][key]))
    assert all(math.isclose(a,b,rel_tol=1e-12) for a,b in zip(slew,authored['output_slew_v_per_s']))
    assert math.isclose(startup,authored['projected_combined_current_a'])
    assert authored['guaranteed_maximum_fault_timer_s'] is None
    assert authored['current_envelope_is_engineering_assumption'] is True
    return dict(input_corners_v=corners,slew_v_per_s=slew,nominal_current_limit_a=current,
        nominal_circuit_breaker_a=current-.03,modeled_startup_a=startup,
        modeled_minimum_CB_a=modeled_low,modeled_startup_margin_a=modeled_low-startup,
        steady_input_floor_with_allocated_losses_v=steady_floor,
        startup_current_envelope_and_load_not_guaranteed=True,
        nominal_fault_timer_s=.004,guaranteed_max_fault_time_s=None)


def run():
    parts,p=read_netlist(OUT/'netlist.xml'); oldparts,oldp=read_netlist(BASE/'netlist.xml')
    added={'G_'+r for r in ['U1','NT1','D1','D2','R1','R2','R3','R4','R5','C1','C2','C3','C4']}
    assert set(parts)==set(oldparts)|added
    for ref in oldparts:
        for field in ['value','footprint']:assert parts[ref].findtext(field)==oldparts[ref].findtext(field),(ref,field)
    assert partition({n:v for n,v in p.items() if n[0] in oldparts})==partition(oldp)
    branch(parts,p)
    mutations={}
    for name,node,wrong in [
        ('MODE_grounded',('G_U1','13'),('G_U1','15')),
        ('RTN_shorted_to_GND',('G_U1','15'),('G_U1','17')),
        ('exposed_pad_on_force_ground',('G_U1','25'),('G_U1','17')),
        ('missing_second_IN',('G_U1','9'),('G_U1','1')),
        ('missing_second_OUT',('G_U1','24'),('G_U1','2')),
        ('slew_cap_return_grounded',('G_C4','2'),('G_U1','17')),
        ('divider_return_grounded',('G_R2','2'),('G_U1','17')),
        ('unprotected_source',('G_U1','8'),('P_U101','1')),
        ('module_protector_bypassed',('N_U17','2'),('G_U1','8')),
        ('primary_to_quiet_ground',('N_U17','1'),('N_J1','2')),
        ('return_star_bypassed',('G_NT1','1'),('G_NT1','2')),
        ('output_clamp_reversed',('G_D2','1'),('G_U1','17'))]:
        trial=dict(p);trial[node]=p[wrong]
        try:branch(parts,trial)
        except AssertionError:mutations[name]=True
        else:raise AssertionError(name)
    for name,ref,value in [('auto_retry_variant','G_U1','TPS26600RHFR'),('old_current_setting','G_R5','6.49k 0.1% 25ppm')]:
        trial=copy.deepcopy(parts);trial[ref].find('value').text=value
        try:branch(trial,p)
        except AssertionError:mutations[name]=True
        else:raise AssertionError(name)
    trees=[read_sexpr((d/'power_protection.kicad_pcb').read_text()) for d in [BASE,OUT]]
    fps0,fps=[{prop(f,'Reference')[2]:f for f in children(t,'footprint')} for t in trees]
    assert set(fps)==set(fps0)|added
    for ref in fps0:assert geometry(fps[ref],ref not in oldparts)==geometry(fps0[ref],ref not in oldparts),ref
    def root_geometry(tree):return [n for n in tree if not(isinstance(n,list) and n and n[0] in ['net','footprint'])]
    assert root_geometry(trees[0])==root_geometry(trees[1])
    for tag in ['segment','via','zone']:assert not children(trees[1],tag)
    count=0
    for ref,f in fps.items():
        for pad in children(f,'pad'):
            if ref not in parts or not pad[1]:continue
            assert str(first(pad,'net')[2]).lstrip('/')==p[(ref,str(pad[1]))]
            count+=1
    assert first(fps['G_NT1'],'net_tie_pad_groups')[1:]==['1,2']
    land=package(fps['G_U1'])
    # PCB geometry mutations exercise physical pin assignment and land size.
    for name in ['swapped_IN_OUT_lands','changed_exposed_pad_size']:
        trial=copy.deepcopy(fps['G_U1'])
        pads={str(p[1]):p for p in children(trial,'pad') if p[1]}
        if name=='swapped_IN_OUT_lands':pads['8'][1],pads['23'][1]='23','8'
        else:first(pads['25'],'size')[1]=2.5
        try:package(trial)
        except AssertionError:mutations[name]=True
        else:raise AssertionError(name)
    numbers=numerical(parts)
    assert len(evaluate(p))==32 and len(verify_sense(parts,p))==2
    uv,trace,deep=check_uv(p);assert len(uv)==64
    review=json.loads((OUT/'review.json').read_text())
    assert review['geometry_findings']==review['schematic_parity_findings']==0
    erc=json.loads((OUT/'erc.json').read_text())
    findings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(findings)==2 and all(v['type']=='ground_pin_not_ground' and v['severity']=='warning' for v in findings)
    priorparts,priorpins=read_netlist(STAGING/'two-board-power-native-09/netlist.xml')
    assert partition(priorpins)==partition(p) and set(priorparts)==set(parts)
    paths=[Path(__file__),BASE/'netlist.xml',BASE/'power_protection.kicad_pcb',OUT/'netlist.xml',
        OUT/'power_protection.kicad_pcb',OUT/'review.json',OUT/'erc.json',OUT/'drc.json',OUT/'module-cutoff-design.json',
        STAGING/'two-board-power-native-09/netlist.xml',STAGING/'two-board-module-cutoff-review-01/sources/tps2660.pdf',
        *[REPO/'hardware/fabrication'/f for f in ['audit_two_board_enable_recovery.py','audit_two_board_fault_mask.py',
            'audit_two_board_source_sense.py','audit_two_board_power_delta.py','native_two_board_power.py']]]
    report=dict(source_sha256={str(f.relative_to(REPO)):sha(f) for f in paths},electrical_parts=len(parts),
        unchanged_original_components=len(oldparts),unchanged_original_footprints=len(fps0),
        unchanged_outline_setup_and_mounts=True,mapped_pad_instances=count,land=land,numerical=numbers,
        mutation_controls_rejected=mutations,prior_fault_cases=32,prior_source_sense_channels=2,prior_UV_cases=len(uv),
        parallel_OUT_symbol_correction_did_not_change_connectivity=True,
        timer_latch_topology_and_RTN_separation_verified=True,return_star_routed=False,
        installed_module_fault_behavior_qualified=False,complete_power_circuit=False,fabrication_released=False)
    target=OUT/'module-cutoff-audit.json';assert not target.exists()
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))


if __name__=='__main__':run()
