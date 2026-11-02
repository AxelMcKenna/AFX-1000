"""Audit a removal-only E28 warning cleanup against the selected baseline."""
import argparse,json,copy
from pathlib import Path
from hardware.fabrication.audit_candidate import geometry_delta,native_evidence_errors,sha
from hardware.electronics.common.sexpr import children,first,read_sexpr

ROOT=Path(__file__).resolve().parent

def verify_geometry(before,after,removed):
    expected=copy.deepcopy(before)
    assert len({first(n,'uuid')[1] for n in removed})==len(removed)
    for node in removed:
        assert node[0] in ['segment','via'] and node in expected
        expected.remove(node)
    delta=geometry_delta(expected,after)
    assert delta['other_root_geometry_exact']
    for tag in ['footprint','segment','via','zone']:assert not any(delta[tag].values()),(tag,delta[tag])
    return geometry_delta(before,after)

def run():
    ap=argparse.ArgumentParser();ap.add_argument('--after',required=True);ap.add_argument('--passes',required=True);args=ap.parse_args()
    labels=args.passes.split(',');assert all(v and all(ch.isalnum() or ch in '-_' for ch in v) for v in [args.after,*labels])
    old=ROOT/'staging/e28-covered-stubs-native';new=ROOT/'staging'/args.after
    pcbs=[p/'rail_disconnect.kicad_pcb' for p in [old,new]];reviews=[p/'review.json' for p in [old,new]]
    for pcb,review in zip(pcbs,reviews):assert not native_evidence_errors(pcb.with_suffix('.kicad_pro'),json.loads(review.read_text()))
    final=json.loads(reviews[1].read_text());assert final['uncapped_open_connections']==0
    assert all(v==0 for v in final['status']['counts'].values())
    for suffix in ['.kicad_pro','.kicad_sch']:assert sha(pcbs[0].with_suffix(suffix))==sha(pcbs[1].with_suffix(suffix))
    removed=[];proofs=[]
    for label in labels:
        proof=ROOT/'staging'/label/'construction.json';data=json.loads(proof.read_text());proofs.append(proof)
        assert all(sha(Path(p))==h for p,h in data['source_sha256'].items())
        assert sha(proof.parent/pcbs[0].name)==data['candidate_PCB_sha256']
        proven={r['uuid'] for r in data['checks'] if r['safe'] and r['local_contact_components']<=1 and not r['conservative_contact_not_represented']}
        assert proven=={first(n,'uuid')[1] for n in data['removed_objects']}
        removed.extend(data['removed_objects'])
    assert final['source_sha256'][str(proofs[-1].parent/pcbs[0].name)]==sha(proofs[-1].parent/pcbs[0].name)
    trees=[read_sexpr(p.read_text()) for p in pcbs];delta=verify_geometry(*trees,removed)
    inputs=[*pcbs,*reviews,*proofs,Path(__file__),ROOT/'audit_candidate.py']+[p.with_suffix(s) for p in pcbs for s in ['.kicad_sch','.kicad_pro']]
    result=dict(source_sha256={str(p):sha(p) for p in inputs},delta=delta,
        all_original_footprints_pads_values_pin_nets_and_poses_exact=True,
        all_retained_tracks_vias_authored_zones_and_rules_exact=True,
        all_native_nets_fully_connected=True,removed_tracks=sum(n[0]=='segment' for n in removed),
        removed_vias=sum(n[0]=='via' for n in removed),local_contact_proofs_verified=True,
        native_status=final['status'],source_to_load_PDN_and_thermal_qualified=False,
        physical_qualified=False,fabrication_released=False)
    output=new/'cleanup-audit.json';assert not output.exists();output.write_text(json.dumps(result,indent=2)+'\n')
    print('Audited removals:',result['removed_tracks'],'tracks,',result['removed_vias'],'vias; all native findings zero')

if __name__=='__main__':run()
