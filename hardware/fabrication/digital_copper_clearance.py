"""Check new native-captured copper against every nearby foreign-net object.

Distances use actual copper polygons, independent of the planner's grid and
centreline search margin. Hole, edge and manufacturing checks remain separate.
"""
from shapely.strtree import STRtree
from hardware.fabrication.route_nf_surface import shape


def verify_added_track_clearance(capture, track_ids, minimum_mm=.2):
    assert minimum_mm > 0
    objects = {o['uuid']: o for o in capture['objects']}
    assert len(objects) == len(capture['objects'])
    assert track_ids and set(track_ids) <= objects.keys()
    by_layer = {}
    for obj in objects.values():
        for layer, polygons in obj['layers'].items():
            if polygons:
                by_layer.setdefault(layer, []).append((obj, shape(polygons)))
    trees = {layer: STRtree([g for _, g in rows]) for layer, rows in by_layer.items()}
    radius = minimum_mm+.1
    closest = None
    checked = []
    for uid in sorted(track_ids):
        obj = objects[uid]
        assert obj['kind'] == 'PCB_TRACK' and obj['net']
        for layer, polygons in obj['layers'].items():
            if not polygons:
                continue
            copper = shape(polygons)
            for index in trees[layer].query(copper.buffer(radius)):
                other, foreign = by_layer[layer][int(index)]
                if other['net'] == obj['net']:
                    continue
                distance = copper.distance(foreign)
                assert distance >= minimum_mm-1e-6, (uid, other['uuid'], layer, distance)
                if distance <= radius and (closest is None or distance < closest['gap_mm']):
                    closest = dict(track_uuid=uid, foreign_uuid=other['uuid'], layer=layer, gap_mm=distance)
        checked.append(uid)
    return dict(checked_track_uuids=checked, minimum_required_mm=minimum_mm,
                closest_pair_within_search_radius=closest, search_radius_mm=radius,
                no_foreign_copper_gap_below_required_minimum=True,
                electrical_or_manufacturing_qualification=False)
