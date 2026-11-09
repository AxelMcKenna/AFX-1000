"""Independently check the TBP51 BOM/land revision against selected TBP50."""
import copy
import itertools
import json
from decimal import Decimal as D
from pathlib import Path
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from hardware.electronics.common.sexpr import children, first, read_sexpr, sexpr
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, prop, read_netlist, sha
from hardware.fabrication.route_nf_surface import shape
from hardware.fabrication.verify_native_zone_unfracture import verify_capture

BASE = STAGING/'two-board-power-startup-remaining-native-03'
OUT = STAGING/'two-board-power-aux-feedback-native-01'
BEFORE = STAGING/'two-board-power-routing-inputs-2172-startup-remaining-03/capture.json'
AFTER = STAGING/'two-board-power-routing-inputs-2172-aux-feedback-01/capture.json'
SELECTION = REPO/'hardware/fabrication/parts/aux-feedback-01/selection.json'
FILL = STAGING/'two-board-power-aux-feedback-filled-01/local-plane-fill.json'
WANTED = {
    'P_R108': ('11.7k 0.1% 25ppm', 'TNPW080511K7BEEA', 'TBP51_AUX:R_0805_Vishay_TNPW_28950'),
    'P_R109': ('10k 0.1% 10ppm', 'TNPW080510K0BYEA', 'TBP51_AUX:R_0805_Vishay_TNPW_28950'),
    'P_R130': ('49.9 0.01% 5ppm', 'RNCF0805TKY49R9', 'TB05_P_Resistor_SMD:R_0805_2012Metric'),
}


def strip(node, tags):
    return [n for n in node if not (isinstance(n, list) and n and n[0] in tags)]


def run():
    target=OUT/'aux-feedback-review.json'
    assert not target.exists()
    paths=[Path(__file__), SELECTION, BEFORE, AFTER, FILL, OUT/'review.json',
           BASE/'startup-cell-reference-review.json']
    selection,before,after,fill,native,prior=[json.loads(p.read_text()) for p in paths[1:]]
    fidelity=verify_capture(after)
    for path,data in zip(paths[1:], [selection,before,after,fill,native,prior]):
        for key in ['source_sha256','artifact_sha256']:
            for name,digest in data.get(key,{}).items():
                p=Path(name)
                if not p.is_absolute(): p=(REPO if name.startswith(('hardware/','tests/')) else path.parent)/p
                assert sha(p)==digest,(path,name)
    b0,b1=[read_sexpr((p/'power_protection.kicad_pcb').read_text()) for p in [BASE,OUT]]
    assert strip(b0,['footprint','zone'])==strip(b1,['footprint','zone'])
    f0,f1=[{prop(f,'Reference')[2]:f for f in children(b,'footprint')} for b in [b0,b1]]
    assert f0.keys()==f1.keys() and len(f1)==1101
    for r in f0:
        if r not in WANTED:
            assert f0[r]==f1[r],r
            continue
        old,new=copy.deepcopy(f0[r]),copy.deepcopy(f1[r])
        value,mpn,fp=WANTED[r]
        assert new[1]==fp and prop(new,'Value')[2]==value and prop(new,'MPN')[2]==mpn
        assert prop(new,'Manufacturer')[2] in ['Vishay','Stackpole Electronics']
        assert prop(new,'Datasheet')[2].startswith('https://')
        allowed={'Value','MPN','Manufacturer','Datasheet'}
        for f in [old,new]:
            f[:]=[n for n in f if not (isinstance(n,list) and n and n[0]=='property' and n[1] in allowed)]
        if r!='P_R130':
            new[1]=old[1]
            for po,pn in zip(children(old,'pad'),children(new,'pad')):
                assert pn[1]==po[1] and pn[3]=='rect'
                assert list(map(float,first(pn,'size')[1:]))==[.9,1.45]
                assert list(map(float,first(pn,'at')[1:3]))==[-.95 if pn[1]=='1' else .95,0.]
                assert first(po,'at')[3:]==first(pn,'at')[3:]
                assert strip(po,['at','size','roundrect_rratio'])[4:]==strip(pn,['at','size','roundrect_rratio'])[4:]
            old[:]=[n for n in old if not (isinstance(n,list) and n and n[0]=='pad')]
            new[:]=[n for n in new if not (isinstance(n,list) and n and n[0]=='pad')]
            for ro,rn in zip(children(old,'fp_rect'),children(new,'fp_rect')):
                if str(first(ro,'layer')[1]).endswith('.CrtYd'):
                    assert list(map(float,first(rn,'start')[1:]))==[-1.68,-1.]
                    assert list(map(float,first(rn,'end')[1:]))==[1.68,1.]
                    first(rn,'start')[:]=first(ro,'start')
                    first(rn,'end')[:]=first(ro,'end')
        assert old==new,(r,'undeclared footprint change')
    oldparts,oldpins=read_netlist(BASE/'netlist.xml')
    newparts,newpins=read_netlist(OUT/'netlist.xml')
    assert oldpins==newpins and oldparts.keys()==newparts.keys()
    for r in oldparts:
        for field in ['value','footprint','datasheet']:
            if r not in WANTED:
                assert oldparts[r].findtext(field)==newparts[r].findtext(field),(r,field)
        if r in WANTED:
            value,mpn,fp=WANTED[r]
            assert newparts[r].findtext('value')==value and newparts[r].findtext('footprint')==fp
            fields={p.attrib['name']:p.text for p in newparts[r].findall('./fields/field')}
            assert fields['MPN']==mpn
    # Exact schematic delta, including every untouched sheet and wire.
    for path in BASE.glob('*.kicad_sch'):
        old=read_sexpr(path.read_text());new=read_sexpr((OUT/path.name).read_text())
        if path.name=='power_protection.kicad_sch':
            assert first(first(new,'title_block'),'rev')[1]=='TBP51-CANDIDATE'
            first(first(new,'title_block'),'rev')[:]=first(first(old,'title_block'),'rev')
        if path.name=='P_power_p03.kicad_sch':
            for tree in [old,new]:
                for s in children(tree,'symbol'):
                    if prop(s,'Reference')[2] in WANTED:
                        s[:]=[n for n in s if not (isinstance(n,list) and n and n[0]=='property' and n[1] in ['Value','Footprint','Datasheet','MPN','Manufacturer'])]
        assert old==new,path.name
    o0,o1=[{o['uuid']:o for o in c['objects']} for c in [before,after]]
    aliases={}
    physical=lambda o:{k:v for k,v in o.items() if k not in ['uuid','group']}
    for u in o0.keys()-o1.keys():
        assert o0[u]['kind']=='PAD'
        matches=[v for v in o1.keys()-o0.keys() if physical(o0[u])==physical(o1[v])]
        assert len(matches)==1
        aliases[matches[0]]=u
    assert set(aliases)==o1.keys()-o0.keys()
    for obj in after['objects']:
        obj['uuid']=aliases.get(obj['uuid'],obj['uuid']);obj['group']=aliases.get(obj['group'],obj['group'])
    after['all_groups']={aliases.get(k,k):[aliases.get(u,u) for u in v] for k,v in after['all_groups'].items()}
    o1={o['uuid']:o for o in after['objects']}
    assert o0.keys()==o1.keys()
    assert {frozenset(v) for v in before['all_groups'].values()}=={frozenset(v) for v in after['all_groups'].values()}
    for u,o in o0.items():
        if o.get('ref') not in ['P_R108','P_R109']: assert physical(o)==physical(o1[u]),u
    z0,z1=[{z['uuid']:z for z in c['zones']} for c in [before,after]]
    assert z0.keys()==z1.keys() and len(z1)==47
    areas=[]
    for u,z in z0.items():
        assert z['authored_outline']==z1[u]['authored_outline']
        if u not in selection['refilled_zone_uuids']:
            assert z==z1[u],u
        else:
            delta=shape(z['polygons']).symmetric_difference(shape(z1[u]['polygons']))
            vicinity=unary_union([shape(o['layers'][z['layer']]).buffer(.8) for o in o0.values()
                if o.get('ref') in ['P_R108','P_R109'] and z['layer'] in o['layers']])
            assert delta.difference(vicinity).area<1e-6,(u,'remote fill change')
            areas.append(dict(zone_uuid=u,changed_area_mm2=delta.area))
    # Direct contact assigns each return island to a native connectivity group.
    def fields(c):
        result={};excluded=[]
        contacts={l:[(o['group'],shape(o['layers'][l])) for o in c['objects']
            if o['net']=='PWR_AGND' and o['layers'].get(l)] for l in c['copper_layers']}
        for z in c['zones']:
            if z['net']!='PWR_AGND':continue
            for p in z['polygons']:
                g=Polygon(p['outer'],p['holes'])
                groups={gid for gid,s in contacts[z['layer']] if g.buffer(.0015).intersection(s).area>1e-9}
                if not groups: excluded.append((z['uuid'],p));continue
                assert len(groups)==1
                result.setdefault((z['layer'],next(iter(groups))),[]).append(g)
        return {k:unary_union(v) for k,v in result.items()},excluded
    fields0,excluded0=fields(before);fields1,excluded1=fields(after)
    assert excluded0==excluded1
    holes={}
    for o in o0.values():
        if o['kind']=='PCB_VIA': holes.setdefault(o['net'],[]).append(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
    holes={n:unary_union(p) for n,p in holes.items()}
    references=[];layers=before['copper_layers']
    for u,o in o0.items():
        if o['kind']!='PCB_TRACK' or o['net']=='PWR_AGND':continue
        layer,=o['layers'];i=layers.index(layer)
        adj={layers[j] for j in [i-1,i+1] if 0<=j<len(layers)}
        track=LineString([o['position_mm'],o['end_mm']]).buffer(o['width_mm']/2).difference(holes.get(o['net'],Polygon()))
        if track.is_empty:continue
        for (l,gid),field in fields0.items():
            if l not in adj or track.difference(field.buffer(.0015)).area>=1e-6:continue
            anchor=next(iter(before['all_groups'][gid]))
            missing=track.difference(fields1[(l,o1[anchor]['group'])].buffer(.0015)).area
            assert missing<1e-6,(u,l,missing)
            references.append(dict(track_uuid=u,reference_layer=l,uncovered_mm2=missing))
    # Decimal corner check, separate from the builder's floating nodal solver.
    checked=0
    for scenario in selection['voltage_scenarios']:
        for c in scenario['cases']:
            r1,r2,rb=[D(str(n))*D(str(f)) for n,f in zip([11700,49.9,10000],c['factors'])]
            vf=D(str(c['feedback_V']));ifb=D(str(c['IFB_out_A']))
            vo=vf*(1+(r1+r2)/rb)-ifb*(r1+r2)
            assert abs(float(vo)-c['output_V'])<1e-12
            assert abs((c['output_V']-c['midpoint_V'])/float(r1)-(c['midpoint_V']-float(vf))/float(r2))<1e-12
            checked+=1
    assert checked==64
    drc=json.loads((OUT/'drc.json').read_text());erc=json.loads((OUT/'erc.json').read_text())
    findings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert not drc['violations'] and not drc['schematic_parity'] and not drc['ignored_checks']
    assert not erc['ignored_checks'] and all(v['severity']=='warning' for v in findings) and len(findings)==2
    assert before['native_uncapped_opens']==after['native_uncapped_opens']==native['opens']==2172
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        candidate_revision='TBP51-CANDIDATE', verified_parts=WANTED,
        changed_copper_pads=4, changed_nominal_resistances=0,
        all_tracks_vias_zone_outlines_and_other_footprints_unchanged=True,
        all_native_connectivity_groups_preserved=True, generated_pad_identity_aliases=aliases,
        local_fill_changes=areas, retained_reference_checks=references,
        unanchored_fragments_preserved=True, independent_voltage_corners=checked,
        power_opens=2172, native_geometry_errors=0, parity_errors=0, ERC_errors=0,
        ERC_warnings=2, installed_resistor_limits_qualified=False, fabrication_released=False)
    result['zone_unfracture_fidelity']=fidelity
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['source_sha256','retained_reference_checks','verified_parts','zone_unfracture_fidelity']}))
    print('Retained reference checks:',len(references))


if __name__=='__main__':run()
