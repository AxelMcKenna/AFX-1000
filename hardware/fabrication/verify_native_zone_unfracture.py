"""Verify raw/fractured native copper against unfractured capture geometry."""
import math
from shapely.geometry import Polygon
from shapely.ops import unary_union
from hardware.fabrication.route_nf_surface import shape


def verify(raw, captured, displacement=2e-6):
    # Fractured polygons can have zero-width slit boundaries, invalid in GEOS.
    # Resolve only those slits using buffer(0), then check area preservation
    # against the raw signed polygon area before comparing both copper sets.
    source = [Polygon(p['outer'], p['holes']) for p in raw]
    source_area = sum(p.area for p in source)
    a = unary_union([p.buffer(0) for p in source])
    b = shape(captured)
    assert a.is_valid and b.is_valid and not a.is_empty and not b.is_empty
    assert abs(a.area-source_area) < 1e-7
    bound = max(1e-6, sum(p.length for p in source)*displacement)
    distance = a.hausdorff_distance(b)
    difference = a.symmetric_difference(b).area
    assert distance <= displacement, ('boundary displacement', distance)
    assert difference <= bound, ('symmetric area difference', difference, bound)
    assert (a.geom_type, len(a.geoms) if hasattr(a, 'geoms') else 1) == (b.geom_type, len(b.geoms) if hasattr(b, 'geoms') else 1)
    return dict(boundary_displacement_mm=distance, symmetric_difference_area_mm2=difference,
                maximum_boundary_displacement_mm=displacement, maximum_symmetric_difference_area_mm2=bound,
                raw_area_mm2=source_area, captured_area_mm2=b.area)


def verify_capture(capture):
    records = capture['zone_unfracture_fidelity']
    assert {(z['uuid'],z['layer']) for z in capture['zones']} == {(r['uuid'],r['layer']) for r in records}
    results = []
    for r in records:
        z = next(z for z in capture['zones'] if (z['uuid'],z['layer']) == (r['uuid'],r['layer']))
        assert r['maximum_boundary_displacement_mm'] == 2e-6
        result = verify(r['raw_filled_polygons'], z['polygons'])
        assert math.isclose(result['maximum_symmetric_difference_area_mm2'],r['maximum_symmetric_difference_area_mm2'],abs_tol=1e-10)
        assert math.isclose(result['raw_area_mm2'],z['native_area_before_unfracture_mm2'],abs_tol=1e-7)
        assert math.isclose(result['captured_area_mm2'],z['native_area_after_unfracture_mm2'],abs_tol=1e-7)
        results.append(dict(uuid=z['uuid'],layer=z['layer'],**result))
    return results
