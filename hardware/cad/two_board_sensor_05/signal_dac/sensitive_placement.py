"""Validate a transported sensitive-pad opening independently of the proposed routes."""
from shapely.affinity import translate
from hardware.fabrication.route_nf_surface import shape


def validated_exclusions(before, after, contracts):
    old = {o['uuid']: o for o in before['objects']}
    new = {o['uuid']: o for o in after['objects']}
    sensitive = {o['net'] for o in before['objects']
                 if o.get('ref') in ['A_U301','A_U302','A_U303','A_U304'] and o.get('pin') in ['2','6']}
    rows = []
    for item in contracts:
        assert item['reference'] == 'A_R308' and item['pin'] == '2'
        assert item['buffer_mm'] == .5 and item['pad_layer'] == 'F.Cu'
        assert item['excluded_layers'] == ['In1.Cu','In2.Cu']
        p0,p1 = old[item['pad_uuid']],new[item['pad_uuid']]
        assert p0['net'] == p1['net'] == item['net'] and item['net'] in sensitive
        assert p0['ref'] == p1['ref'] == item['reference'] and p0['pin'] == p1['pin'] == item['pin']
        assert p0['position_mm'] == item['before_pad_mm'] and p1['position_mm'] == item['after_pad_mm']
        dx,dy = item['translation_mm']
        assert [p0['position_mm'][0]+dx,p0['position_mm'][1]+dy] == p1['position_mm']
        moved = translate(shape(p0['layers']['F.Cu']),dx,dy)
        actual = shape(p1['layers']['F.Cu'])
        assert moved.difference(actual.buffer(2e-6)).area < 1e-9
        assert actual.difference(moved.buffer(2e-6)).area < 1e-9
        expected = moved.buffer(.5)
        zones = [z for z in after['zones'] if z['uuid'] == item['zone_uuid']]
        assert {z['layer'] for z in zones} == set(item['excluded_layers']) and len(zones) == 2
        for z in zones:
            assert z['keepout'] and not z['prohibit_tracks'] and not z['prohibit_vias']
            native = shape(z['polygons'])
            assert native.difference(expected.buffer(2e-6)).area < 1e-9
            assert expected.difference(native.buffer(2e-6)).area < 1e-9
        native = shape(next(z for z in zones if z['layer']=='In1.Cu')['polygons'])
        rows.append({'net':item['net'],'source_pad_uuid':item['pad_uuid'],'zone_uuid':item['zone_uuid'],
                     'buffer_mm':.5,'before_pad_mm':item['before_pad_mm'],'after_pad_mm':item['after_pad_mm'],
                     'expected_area_mm2':expected.area,'native_area_mm2':native.area,
                     'geometry':native.intersection(expected)})
    return rows
