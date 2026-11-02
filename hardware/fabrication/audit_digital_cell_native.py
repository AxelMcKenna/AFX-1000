"""Reverse only declared placement transforms and compare every authored object."""
import argparse,copy,json,sys
from pathlib import Path
from hardware.electronics.common.sexpr import children,first,read_sexpr
from hardware.fabrication.audit_candidate import geometry_delta,native_evidence_errors,sha
from hardware.fabrication.bypass_import import identity

ROOT=Path(__file__).resolve().parent

def normalize_annotation_half_turns(tree):
    result=copy.deepcopy(tree)
    for fp in children(result,'footprint'):
        for node in children(fp,'property')+children(fp,'fp_text'):
            at=children(node,'at')
            if at and len(at[0])>3:at[0][3]=float(at[0][3])%180
    return result

def run():
    assert sys.platform=='linux'
    import pcbnew
    ap=argparse.ArgumentParser();ap.add_argument('--after',required=True);args=ap.parse_args()
    assert args.after and all(c.isalnum() or c in '-_' for c in args.after)
    old=ROOT/'staging/digital-placement-native-05/digital_core.kicad_pcb'
    folder=ROOT/'staging'/args.after;new=folder/old.name;review=folder/'review.json'
    assert not native_evidence_errors(new.with_suffix('.kicad_pro'),json.loads(review.read_text()))
    record=json.loads(review.read_text())
    assert record['status']['counts']['violations']==record['status']['counts']['schematic_parity']==record['status']['counts']['erc']==0
    for name,h in record['captured_hierarchy_sha256'].items():assert sha(folder/name)==h
    plan=ROOT/'staging/digital-power-cell-plan-01/plan.json';data=json.loads(plan.read_text())
    assert all(sha(Path(p))==h for p,h in data['source_sha256'].items())
    before=pcbnew.LoadBoard(str(old));after=pcbnew.LoadBoard(str(new))
    a,b=identity(before),identity(after);assert set(a)==set(b)
    changes={r['ref']:r for r in data['placements']+data['IC_placements']}
    bf={f.GetReference():f for f in before.GetFootprints()};af={f.GetReference():f for f in after.GetFootprints()}
    for ref in a:
        assert a[ref][:3]==b[ref][:3] and a[ref][7:]==b[ref][7:]
        if ref not in changes:assert a[ref]==b[ref],('Unlisted component moved',ref)
        else:
            p=changes[ref];f=af[ref];o=bf[ref]
            assert f.IsFlipped()==(p['side']=='B')
            assert abs((f.GetOrientationDegrees()-p['rotation_deg']+180)%360-180)<1e-8
            assert all(abs(v/1e6-w)<.000002 for v,w in zip([f.GetPosition().x,f.GetPosition().y],p['anchor_mm']))
            if f.IsFlipped()!=o.IsFlipped():f.Flip(f.GetPosition(),False)
            f.SetOrientationDegrees(o.GetOrientationDegrees());f.SetPosition(o.GetPosition())
    restored=folder/'placement-restored-for-audit-02.kicad_pcb';assert not restored.exists()
    assert pcbnew.SaveBoard(str(restored),after)
    trees=[read_sexpr(p.read_text()) for p in [old,restored]]
    delta=geometry_delta(*[normalize_annotation_half_turns(t) for t in trees])
    assert delta['other_root_geometry_exact'],delta
    assert all(not any(delta[tag].values()) for tag in ['footprint','segment','via','zone']),delta
    inputs=[old,new,review,plan,restored,Path(__file__)]
    result=dict(source_sha256={str(p):sha(p) for p in inputs},declared_changed_components=sorted(changes),
        reverse_placement_restores_electrical_and_mechanical_geometry_exactly=True,
        property_and_Fab_text_half_turns_normalized=True,
        all_values_pin_nets_pad_geometry_courtyards_models_and_rules_retained=True,
        all_unlisted_component_poses_exact=True,native_counts=record['status']['counts'],
        physical_qualified=False,fabrication_released=False)
    (folder/'placement-change-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Independent inverse-transform audit:',len(changes),'declared placements; all authored geometry restored exactly')

if __name__=='__main__':run()
