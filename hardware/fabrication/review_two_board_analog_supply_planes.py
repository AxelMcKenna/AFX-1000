"""Record supply-plane contacts and fill changes after the analog relocation."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape

def run():
    beforepath=STAGING/'two-board-power-routing-inputs-2237-permission-04/capture.json'
    afterpath=STAGING/'two-board-power-routing-inputs-2211-analog-cells-03/capture.json'
    out=STAGING/'two-board-power-analog-cells-native-03'
    paths=[beforepath,afterpath,out/'analog-connectivity-review.json',out/'analog-cell-routing.json']
    before,after,audit,r=[json.loads(p.read_text()) for p in paths]
    assert audit['all_other_native_groups_preserved']
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
    assert {x['uuid'] for x in changes}<={'2d29f18e-f863-557a-bd84-b2d1a216144c','a94125f8-f63e-5d6b-a427-21dcfd31e312'}
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*paths,REPO/'hardware/fabrication/route_nf_surface.py']},supply_planes=records,all_supply_contacts_preserved=True,all_supply_region_counts_preserved=True,supply_outlines_unchanged=True,changed_supply_plane_count=len(changes),scope='Filled-copper area, contact and region-count comparison. Current distribution, resistance, parasitics and thermal limits are not qualified.',fabrication_released=False)
    with (out/'analog-supply-plane-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(planes=len(records),changed=changes)))
if __name__=='__main__':run()
