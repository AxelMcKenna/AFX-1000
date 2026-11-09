"""Read current PCB geometry and screen packaging/consolidation proposals.

This is a planar/prismatic receiving screen, not native assembly or fab approval.
Existing manufacturing and CAD packets are read only. Refuse to overwrite output.
"""
import hashlib
import itertools
import json
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from hardware.electronics.common.sexpr import children, first
from hardware.electronics.output_stage.check_placement import courtyard
from hardware.fabrication.assembly_layout import outline, component_boxes
from hardware.fabrication.digital_core_layout import pad_box

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'hardware/fabrication/staging/housing-consolidation-review-01'
AP = REPO / 'hardware/fabrication/staging/assembly-layout-04/allocation.json'
AUDIO = REPO / 'hardware/fabrication/staging/audio-main-controls-06/audio_core.kicad_pcb'
DIGITAL = REPO / 'hardware/fabrication/staging/digital-led16-closed-native-01/digital_core.kicad_pcb'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ref(fp):
    return next(p[2] for p in children(fp, 'property') if p[1] == 'Reference')


def prism(name, owner, bounds, z0, z1, kind):
    return dict(name=name, owner=owner, xy=list(bounds), z=[z0, z1], kind=kind)


def overlaps(a, b, margin=0):
    ax, ay, bx, by = a['xy']
    cx, cy, dx, dy = b['xy']
    depths = [min(bx + margin, dx) - max(ax - margin, cx),
              min(by + margin, dy) - max(ay - margin, cy),
              min(a['z'][1] + margin, b['z'][1]) - max(a['z'][0] - margin, b['z'][0])]
    return all(d > 1e-8 for d in depths)


def calculate():
    ap = json.loads(AP.read_text())
    plan_path = AUDIO.parent / 'plan.json'
    plan = json.loads(plan_path.read_text())
    paths = [Path(__file__), AP, plan_path,
             REPO/'hardware/fabrication/assembly_layout.py',
             REPO/'hardware/fabrication/digital_core_layout.py',
             REPO/'hardware/electronics/output_stage/check_placement.py',
             REPO/'hardware/electronics/common/sexpr.py']
    boards, trees, polys = [], {}, {}
    for b in ap['boards']:
        source = AUDIO if b['id'] == 'audio_main' else DIGITAL if b['id'] == 'digital_core' else REPO/b['source']
        paths.append(source)
        tree, poly = outline(source)
        trees[b['id']] = tree
        x0, y0, x1, y1 = poly.bounds
        thickness = float(first(first(tree, 'general'), 'thickness')[1])
        datum = b['datum']
        vertical = b.get('vertical', False)
        world = box(datum[0], datum[1]-thickness, datum[0]+x1-x0, datum[1]) if vertical else translate(poly, datum[0]-x0, datum[1]-y0)
        z = [datum[2], datum[2]+y1-y0] if vertical else [datum[2], datum[2]+thickness]
        polys[b['id']] = world
        boards.append(dict(id=b['id'], source=str(source.relative_to(REPO)), datum=datum,
                           vertical=vertical, thickness_mm=thickness, bounds_local_mm=list(poly.bounds),
                           area_mm2=poly.area, polygon_world_mm=list(world.exterior.coords), z_mm=z,
                           native_footprints=len(children(tree, 'footprint'))))
    slab_pairs = []
    for a, b in itertools.combinations(boards, 2):
        area = polys[a['id']].intersection(polys[b['id']]).area
        dz = min(a['z_mm'][1], b['z_mm'][1])-max(a['z_mm'][0], b['z_mm'][0])
        if area > 1e-8 and dz > 1e-8:
            slab_pairs.append(dict(boards=[a['id'], b['id']], volume_mm3=area*dz))

    bodies = []
    pose_mismatches = []
    for fp in children(trees['audio_main'], 'footprint'):
        r = ref(fp)
        if r not in plan['poses']:
            assert r.startswith('H'), r
            continue  # Mounting hardware and support geometry remain a separate missing scope.
        at = first(fp, 'at')[1:]
        side = str(first(fp, 'layer')[1])[0]
        actual = [float(at[0]), float(at[1]), float(at[2]) if len(at)>2 else 0, side]
        if actual != plan['poses'][r]:
            pose_mismatches.append(r)
        bounds = courtyard(fp, side+'.CrtYd')
        expand = plan['film_and_header_secondary_XY_clearance_mm'] if r.startswith('J') or r in {'C107','C121','C321','C322','C401','C403','C501','C502','C503','C504','C513','C514','C515','C516'} else 0
        bounds = [bounds[0]+30-expand, bounds[1]+42-expand, bounds[2]+30+expand, bounds[3]+42+expand]
        h = plan['declared_receiving_height_mm'][r]
        z0, z1 = (6.5-.2-h, 6.5+.2) if side == 'B' else (6.5-.2+1.44, 6.5+.2+1.76+h)
        bodies.append(prism(r, 'audio_main', bounds, z0, z1, 'declared_component_receiver'))
    assert not pose_mismatches, pose_mismatches
    for owner, datum, is_digital in [('digital_core', [184,44,7], True), ('rail_monitor', [36,32,24], False)]:
        for r, x,y,z,dx,dy,dz,*_ in component_boxes(trees[owner], datum, is_digital):
            bodies.append(prism(r, owner, [x,y,x+dx,y+dy], z,z+dz, 'declared_component_receiver'))

    # Explicit existing AP/AC tail requirements. Actual saved pads, transformed
    # with footprint angle; square XY covers are conservative service envelopes.
    tails = []
    for owner, datum, tail_height in [('audio_main',[30,42,6.5],3.2), ('digital_core',[184,44,7],3.2), ('rail_monitor',[36,32,24],2.0)]:
        for fp in children(trees[owner], 'footprint'):
            for p in children(fp,'pad'):
                if p[2] != 'thru_hole':
                    continue
                assert str(first(fp,'layer')[1]) == 'F.Cu', (owner, ref(fp), 'back THT needs separate transform')
                x0,y0,x1,y1 = pad_box(fp,p,.5)
                tails.append(prism(ref(fp)+'.'+str(p[1]),owner,[x0+datum[0],y0+datum[1],x1+datum[0],y1+datum[1]],
                                   datum[2]-.2-tail_height,datum[2]+.2,'THT_tail_requirement'))

    contexts = [prism(r[0], 'retained_controls_and_ports', [r[1],r[2],r[1]+r[4],r[2]+r[5]],r[3],r[3]+r[6],'AP04_context') for r in ap['retained_context_boxes']]
    # Test both the AP04 old jack poses and the documented EI02 repaired poses.
    repaired_context = json.loads(json.dumps(contexts))
    for c in repaired_context:
        if c['name'].startswith(('input_rca_', 'input_ts_', 'output_rca_', 'output_ts_')):
            c['z'] = [z+.8 for z in c['z']]

    def screen(receivers, context, shapes=polys, zs=None):
        zs = zs or {b['id']:b['z_mm'] for b in boards}
        result = dict(context_intersections=[], foreign_board_intersections=[], cross_board_receiver_intersections=[], floor_clearance_violations=[])
        for a in receivers:
            if a['z'][0] < 3.05-1e-8:
                result['floor_clearance_violations'].append([a['owner'],a['name'],a['z'][0]-2.8])
            for c in context:
                if overlaps(a,c):
                    result['context_intersections'].append([a['owner'],a['name'],c['name']])
            for name, poly in shapes.items():
                if name == a['owner']:
                    continue
                if min(a['z'][1],zs[name][1])-max(a['z'][0],zs[name][0]) > 1e-8 and box(*a['xy']).intersection(poly).area > 1e-8:
                    result['foreign_board_intersections'].append([a['owner'],a['name'],name])
        for a,b in itertools.combinations(receivers,2):
            if a['owner']!=b['owner'] and overlaps(a,b):
                result['cross_board_receiver_intersections'].append([a['owner'],a['name'],b['owner'],b['name']])
        return result

    current = screen(bodies+tails,contexts)
    repaired = screen(bodies+tails,repaired_context)
    # Proposal: maintain current XY placement and put audio/digital on common
    # underside Z6.5. This only screens the declared receivers, not merged nets.
    bridge = box(180,47,184,104)
    merged = unary_union([polys['audio_main'],polys['digital_core'],bridge])
    assert merged.geom_type == 'Polygon' and merged.is_valid and not merged.interiors
    moved = json.loads(json.dumps(bodies+tails))
    for r in moved:
        if r['owner']=='digital_core':
            r['z']=[v-.5 for v in r['z']]
    signal_screen=screen(moved,repaired_context,zs={b['id']:([6.5,8.1] if b['id']=='digital_core' else b['z_mm']) for b in boards})
    bridge_hits=[r['name'] for r in repaired_context if min(8.1,r['z'][1])-max(6.5,r['z'][0])>1e-8 and bridge.intersection(box(*r['xy'])).area>1e-8]
    power_bridge=box(164,108.5,168,143)
    power_merge=unary_union([polys['power_supply'],polys['rail_disconnect'],power_bridge])
    assert power_merge.geom_type=='Polygon' and power_merge.is_valid
    studies = dict(
        combined_signal_board=dict(bounds_world_mm=list(merged.bounds), size_mm=[268,63],
            polygon_world_mm=list(merged.exterior.coords),area_mm2=merged.area,board_underside_Z_mm=6.5,
            change='digital underside lowered 0.5 mm; audio XY and Z retained; 4 x 57 mm bridge added',
            declared_receiver_screen=signal_screen,bridge_context_intersections=bridge_hits,
            native_merged_PCB_created=False,full_hardware_harness_and_support_fit_verified=False),
        combined_power_and_disconnect=dict(bounds_world_mm=list(power_merge.bounds),size_mm=[320,60.5],
            polygon_world_mm=list(power_merge.exterior.coords),area_mm2=power_merge.area,
            plane_conflict='current underside Z is 6.5 mm for power and 5 mm for disconnect; cannot join unchanged',
            thermal_links_terminals_harness_and_component_fit_verified=False),
        all_in_one=dict(existing_flat_board_area_sum_mm2=sum(b['area_mm2'] for b in boards),
            enclosure_outer_XY_area_mm2=334*188.4,
            area_ratio_is_not_a_fit_test=True,
            obstacles=['monitor overlaps audio in XY at a different height','NF and fan boards are vertical',
                       'power/disconnect are at different Z and use external thermal/current hardware',
                       'panel controls and sensor have fixed mounting heights',
                       'full harness, boss, service, airflow and actual package heights remain incomplete'],
            one_board_ruled_out=False,requires_new_component_placement_and_routing=True))
    histories=[REPO/'hardware/cad/a12/enclosure_growth/integration_repaired/README.md',
               REPO/'hardware/cad/a12/enclosure_growth/unified_airpath/README.md',
               REPO/'hardware/cad/a12/enclosure_growth/nf265_fpc91/README.md',
               REPO/'hardware/cad/a12/trill_front_bay/README.md']
    paths += histories
    return dict(review='HC01 current geometry and consolidation feasibility screen',
        source_sha256={str(p.relative_to(REPO)):digest(p) for p in paths},
        case_outer_mm=ap['case_outer_mm'],boards=boards,nominal_board_slab_intersections=slab_pairs,
        declared_receivers=bodies,declared_THT_tail_receivers=tails,
        current_AP04_context_screen=current,EI02_raised_jack_context_screen=repaired,
        consolidation_studies=studies,
        covered_component_boards=['audio_main','digital_core','rail_monitor'],
        missing_current_component_envelope_boards=[b['id'] for b in boards if b['id'] not in ['audio_main','digital_core','rail_monitor']],
        limits=['All component heights and connector reserves are project receiving requirements, not supplier-approved maxima.',
                'Board slab intersections use nominal thickness; no whole-case tolerance clearance is claimed.',
                'Audio U201 has no footprint or height. Mounting posts/heads, holes and keepouts need a coherent current model.',
                'Other five boards are checked as board slabs only; their current bodies, mates and tails are not screened here.',
                'Floor check is against Z2.8 plus 0.25 mm only; no bosses, ducts, copper bus hardware or real shell solids.',
                'Receiver overlap is conservative; it is not a confirmed collision of exact component bodies.',
                'No complete panel emitter/sensor PCB count, full harness, removal path, thermal or airflow validation.',
                'EI02 repairs are tested as a separate scenario; they are not silently adopted into AP04.'],
        source_audio_poses_match_plan=not pose_mismatches,
        native_full_assembly_rebuilt=False,complete_fit_verified=False,fabrication_released=False)


def render(d):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch
    fig,axes=plt.subplots(2,1,figsize=(12,9),layout='constrained')
    colours=['#d79a52','#46a99c','#c46a72','#8f8ac0','#a879b6','#5a93c9','#cbb34b','#cbb34b']
    for ax in axes:
        ax.set_xlim(0,334);ax.set_ylim(188.4,0);ax.set_aspect('equal')
        ax.set_xlabel('Enclosure X (mm)');ax.set_ylabel('Y (mm)');ax.grid(alpha=.15)
    ax=axes[0]
    for b,col in zip(d['boards'],colours):
        ax.add_patch(Patch(b['polygon_world_mm'],facecolor=col,edgecolor='#333',alpha=.65))
        p=Polygon(b['polygon_world_mm']).representative_point()
        label=b['id'].replace('_',' ')
        ax.text(p.x,p.y,label,ha='center',va='center',fontsize=8)
    ax.set_title('Current eight-board allocation: monitor stacked; NF and fan cards vertical')
    ax=axes[1]
    for key,col in [('combined_signal_board','#46a99c'),('combined_power_and_disconnect','#c46a72')]:
        s=d['consolidation_studies'][key]
        ax.add_patch(Patch(s['polygon_world_mm'],facecolor=col,edgecolor='#333',alpha=.65))
        x0,y0,x1,y1=s['bounds_world_mm']
        ax.text((x0+x1)/2,(y0+y1)/2,('Signal candidate: 268 × 63 mm\npartial receiver screen only' if key=='combined_signal_board' else 'Power/disconnect outline study: 320 × 60.5 mm\ncomponent and thermal redesign required'),ha='center',va='center',fontsize=9)
    ax.set_title('Consolidation study — remaining boards are NOT incorporated into these outlines')
    fig.suptitle('AFX-1000 housing review · 334 × 188.4 × 45.6 mm outer shell\nConcept allocation only — complete fit and fabrication release remain unverified',fontsize=13)
    fig.savefig(OUT/'comparison.png',dpi=160)
    fig.savefig(OUT/'comparison.svg')
    plt.close(fig)


if __name__=='__main__':
    result=calculate()
    OUT.mkdir(exist_ok=False)
    (OUT/'review.json').write_text(json.dumps(result,indent=2)+'\n')
    render(result)
    print(json.dumps({k:result[k] for k in ['nominal_board_slab_intersections','current_AP04_context_screen','EI02_raised_jack_context_screen']}))
    print('Signal proposal:',json.dumps(result['consolidation_studies']['combined_signal_board']['declared_receiver_screen']))
