"""Locate the eight remaining reference gaps and competing quiet fields."""
import json
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha
from hardware.fabrication.route_nf_surface import shape
CAP=STAGING/'two-board-power-routing-inputs-2210-support-references-01/capture.json'
DIAG=STAGING/'two-board-digital-return-plan-01/retained-reference-diagnosis.json'
QUIET=STAGING/'two-board-power-digital-startup-native-02/digital-startup-routing.json'
OUT=STAGING/'two-board-startup-reference-plan-01'


def run():
    assert not OUT.exists()
    cap=json.loads(CAP.read_text());diag=json.loads(DIAG.read_text());quiet=json.loads(QUIET.read_text())['quiet_ground_islands']
    for name,digest in cap['source_sha256'].items():
        path=Path(name);assert sha(path if path.is_absolute() else REPO/path)==digest
    objects={o['uuid']:o for o in cap['objects']};zones={z['uuid']:z for z in cap['zones']}
    owners={'E_U15.3':'E_U15','E_U16.3':'E_U16','E_U16.1':'E_U16','E_U17.1':'E_U17',
            'E_U33.1':'E_U33','E_R108.1':'E_U16','E_R107.1':'E_U16','E_R103.1':'E_U15'}
    results=[]
    for rec in diag['gaps'][4:]:
        route=rec['route'];layer=rec['reference_layer'];owner=owners[rec['label']]
        for uid in route['segment_uuids']:assert objects[uid]['net']==route['net']
        projection=LineString(route['path_mm']).buffer(route['width_mm']/2)
        for o in cap['objects']:
            if o['kind']=='PCB_VIA' and o['net']==route['net']:
                projection=projection.difference(Point(o['position_mm']).buffer(o['width_mm']/2+.215))
        field=unary_union([shape(z['polygons']) for z in cap['zones'] if z['net']=='PWR_AGND' and z['layer']==layer])
        missing=projection.difference(field.buffer(.0015));assert missing.area>1e-6
        extension=LineString(route['path_mm']).buffer(.4);conflicts=[]
        for q in quiet:
            if q['ref']==owner:continue
            for uid in q['zone_uuids']:
                if zones[uid]['layer']!=layer:continue
                other=shape(zones[uid]['authored_outline']).buffer(.215)
                area=extension.intersection(other).area
                if area>1e-6:conflicts.append(dict(owner=q['ref'],zone_uuid=uid,
                    proposed_0_4mm_extension_intersection_mm2=area,
                    actual_trace_projection_intersection_mm2=projection.intersection(other).area))
        results.append(dict(label=rec['label'],owner=owner,route=route,reference_layer=layer,
                            uncovered_mm2=missing.area,missing_bounds=list(missing.bounds),
                            competing_quiet_fields=conflicts))
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),CAP,DIAG,QUIET,REPO/'hardware/fabrication/route_nf_surface.py']},
                remaining_paths=results,remaining_path_count=8,
                proposed_extension_radius_mm=.4,quiet_separation_margin_mm=.215,
                scope='Diagnostic only. No fields or routes are authored. Competing-field overlap is not permission to remove that field; preserve every quiet graph, star isolation and existing signal projection.',
                fabrication_released=False)
    OUT.mkdir();(OUT/'reference-plan.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(label=r['label'],missing_mm2=r['uncovered_mm2'],conflicting_owners=[q['owner'] for q in r['competing_quiet_fields']]) for r in results]))


if __name__=='__main__':run()
