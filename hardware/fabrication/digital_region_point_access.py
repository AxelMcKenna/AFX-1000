"""Classify point access by exhausting the connected polygon-region graph.

Probe membership is a planning condition, not a routed connection or proof that
multiple proposed routes can coexist. All graph edges retain exact via screens.
"""
from collections import deque
import itertools

from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.strtree import STRtree


def polygon_parts(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Polygon':
        return [geometry]
    return [p for p in geometry.geoms if p.geom_type == 'Polygon' and not p.is_empty]


def reachability(screen, net, starts, ends, faces, existing_crossings=(), probes=()):
    regions = {}
    trees = {}
    free_by_layer = {}
    for face in faces:
        obstacles = [g.buffer(d+.0005, quad_segs=32) for other, g, d in screen.geometry[face] if other != net]
        assert not screen.added and not screen.new_vias, 'Use captured geometry for this diagnostic'
        free = screen.outline.difference(unary_union(obstacles))
        free_by_layer[face] = free
        regions[face] = polygon_parts(free)
        trees[face] = STRtree(regions[face])

    def nodes_at(point, layers):
        p = Point(point)
        return [(face, int(i)) for face in layers for i in trees[face].query(p)
                if regions[face][int(i)].covers(p)]

    via_free = screen.via_outline.difference(screen.obstacles(net))
    edges = {}
    portals = []
    # Track restrictions can be wider than via restrictions, for example around
    # mounting holes. Split the admissible area for each pair of routing faces.
    for pair in itertools.combinations(faces, 2):
        shared = via_free.intersection(free_by_layer[pair[0]]).intersection(free_by_layer[pair[1]])
        for area in polygon_parts(shared):
            point = area.representative_point()
            xy = (point.x, point.y)
            assert screen.via_legal(net, xy)
            nodes = nodes_at(xy, pair)
            assert len(nodes) == 2
            assert all(area.difference(regions[face][i]).is_empty for face, i in nodes), 'Split via region has copper outside its surface component'
            portals.append(dict(point_mm=xy, area_mm2=area.area, faces=pair, component_nodes=nodes))
            for left, right in itertools.permutations(nodes, 2):
                edges.setdefault(left, []).append((right, xy, 'new_via'))
    for point, layers in existing_crossings:
        nodes = nodes_at(point, layers)
        assert len(nodes) == len(layers)
        for left, right in itertools.permutations(nodes, 2):
            edges.setdefault(left, []).append((right, point, 'existing_copper'))
    sources = {node for face, point in starts for node in nodes_at(point, [face])}
    targets = {node for face, point in ends for node in nodes_at(point, [face])}
    assert sources and targets
    queue = deque(sorted(sources))
    parents = {node: None for node in sources}
    found = None
    while queue:
        node = queue.popleft()
        if node in targets and found is None:
            found = node
        for other, point, kind in edges.get(node, []):
            if other not in parents:
                parents[other] = (node, point, kind)
                queue.append(other)
    witness = []
    node = found
    while node is not None and parents[node] is not None:
        previous, point, kind = parents[node]
        witness.append(dict(from_component=previous, to_component=node, point_mm=point, kind=kind))
        node = previous
    witness.reverse()
    probe_results = [dict(face=face, point_mm=point, connected_to_sources=any(n in parents for n in nodes_at(point,[face]))) for face,point in probes]
    return dict(probe_results=probe_results, exhausted_component_graph=True, connected=found is not None, source_components=sorted(sources), target_components=sorted(targets),
                component_counts={f: len(rows) for f, rows in regions.items()},
                visited_components=sorted(parents), conventional_via_pair_regions=portals,
                all_via_areas_proven_inside_surface_components=True, region_membership_proof="polygon_difference_is_empty", component_witness=witness,
                extra_track_region_margin_mm=.0005, routed_candidate=False, joint_new_via_spacing_checked=False,
                path_length_and_electrical_performance_qualified=False)
