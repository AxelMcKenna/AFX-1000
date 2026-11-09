"""Record supply-plane contacts and fill changes after the startup reference repairs."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape

def run():
    beforepath=STAGING/'two-board-power-routing-inputs-2210-support-references-01/capture.json'
    afterpath=STAGING/'two-board-power-routing-inputs-2210-startup-references-04/capture.json'
    out=STAGING/'two-board-power-startup-references-native-04'
    paths=[beforepath,afterpath,out/'startup-reference-review.json',out/'startup-reference-routing.json']
    before,after,audit,r=[json.loads(p.read_text()) for p in paths]
    assert audit['all_native_groups_preserved']
    aliases=audit['generated_pad_identity_aliases']
    for o in after['objects']:o['uuid']=aliases.get(o['uuid'],o['uuid'])
    retired=set(r['retired_objects']);z1={z['uuid']:z for z in after['zones']};records=[]
    for z in before['zones']:
        if z['net']=='PWR_AGND':continue
        n=z1[z['uuid']];g,h=shape(z['polygons']),shape(n['polygons'])
        assert z['net']==n['net'] and z['layer']==n['layer']
        assert shape(z['authored_outline']).equals(shape(n['authored_outline']))
        contacts=[]
        for cap,field in [(before,g),(after,h)]:
            contacts.append({o['uuid'] for o in cap['objects'] if o['uuid'] not in retired and o['net']==z['net'] and o['layers'].get(z['layer']) and field.buffer(.0015).intersection(shape(o['layers'][z['layer']])).area>1e-9})
        assert contacts[0]==contacts[1],(z['uuid'],'supply contact change')
        assert len(z['polygons'])==len(n['polygons']),(z['uuid'],'supply region count changed')
        records.append(dict(uuid=z['uuid'],net=z['net'],layer=z['layer'],contacts_preserved=sorted(contacts[0]),filled_regions=len(n['polygons']),before_area_mm2=g.area,after_area_mm2=h.area,symmetric_change_mm2=g.symmetric_difference(h).area))
    changes=[x for x in records if x['symmetric_change_mm2']>1e-6]
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*paths,REPO/'hardware/fabrication/route_nf_surface.py']},supply_planes=records,all_supply_contacts_preserved=True,all_supply_region_counts_preserved=True,supply_outlines_unchanged=True,changed_supply_plane_count=len(changes),scope='Filled-copper area, contact and region-count comparison. Current distribution, resistance, parasitics and thermal limits are not qualified.',fabrication_released=False)
    with (out/'startup-supply-plane-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(planes=len(records),changed=changes)))
if __name__=='__main__':run()
