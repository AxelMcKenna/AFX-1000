"""Bounded multilayer routing with lazily measured planar path costs.

Via regions supply a finite set of screened candidate positions. Dijkstra uses
Euclidean lower bounds until a selected planar edge has been routed through
its actual free-space polygon. This is a finite proposal search, not a proof
of a globally shortest electrical route or of global infeasibility.
"""
import heapq
import itertools
import math
import time

from shapely.geometry import Point, LineString
from shapely.ops import unary_union, nearest_points
from shapely.strtree import STRtree

from hardware.fabrication.digital_planned_region_screen import PlannedRegionScreen
from hardware.fabrication.digital_polygon_path import route as polygon_route
from hardware.fabrication.digital_region_reachability import polygon_parts


def shortest_path(nodes, members, crossings, sources, targets, measured, forbidden=()):
    """Use measured nonnegative edge costs, with Euclidean unmeasured bounds."""
    forbidden = set(forbidden)
    costs = {i: 0. for i in sources if i not in forbidden}
    queue = [(0., i) for i in costs]
    heapq.heapify(queue)
    parent = {}
    found = None
    while queue:
        cost, i = heapq.heappop(queue)
        if cost != costs.get(i):
            continue
        if i in targets:
            found = i
            break
        face, component, point = nodes[i]
        edges = [(j, measured.get(tuple(sorted((i, j))), math.dist(point, nodes[j][2])))
                 for j in members[(face, component)] if j != i]
        edges += crossings.get(i, [])
        for j, weight in edges:
            assert weight >= 0
            candidate = cost + weight
            if j in forbidden or candidate >= costs.get(j, math.inf):
                continue
            costs[j] = candidate
            parent[j] = i
            heapq.heappush(queue, (candidate, j))
    if found is None:
        return None
    path = [found]
    while found in parent:
        found = parent[found]
        path.append(found)
    return path[::-1]


def route(screen, net, starts, ends, deadline, via_penalty_mm=2., max_refinements=160):
    assert via_penalty_mm >= 0 and starts and ends
    frozen = PlannedRegionScreen(screen, net)
    faces = tuple(frozen.geometry)
    regions, trees, free = {}, {}, {}
    for face in faces:
        obstacles = [g.buffer(d+.0005, quad_segs=32) for other, g, d in frozen.geometry[face] if other != net]
        free[face] = frozen.outline.difference(unary_union(obstacles))
        regions[face] = polygon_parts(free[face])
        trees[face] = STRtree(regions[face])

    def component_at(face, xy):
        point = Point(xy)
        return next((int(i) for i in trees[face].query(point) if regions[face][int(i)].covers(point)), None)

    source_xy = starts[0][1]
    target_xy = ends[0][1]
    guides = [Point(source_xy), Point(target_xy), Point(tuple((a+b)/2 for a, b in zip(source_xy, target_xy))), LineString([source_xy, target_xy])]
    via_free = frozen.via_outline.difference(frozen.obstacles(net))
    points = set()
    area_count = 0
    for left, right in itertools.combinations(faces, 2):
        shared = via_free.intersection(free[left]).intersection(free[right])
        for area in polygon_parts(shared):
            area_count += 1
            safe = area.buffer(-.002)
            samples = [area.representative_point()]
            if not safe.is_empty:
                samples += [nearest_points(safe, guide)[0] for guide in guides]
            for point in samples:
                xy = (round(point.x, 6), round(point.y, 6))
                if frozen.via_legal(net, xy):
                    points.add(xy)
    nodes, members, point_nodes = [], {}, {}
    def node(face, xy):
        component = component_at(face, xy)
        if component is None:
            return None
        i = len(nodes)
        nodes.append((face, component, tuple(xy)))
        members.setdefault((face, component), []).append(i)
        return i
    crossings = {}
    for xy in sorted(points):
        ids = [i for face in faces if (i := node(face, xy)) is not None]
        point_nodes[xy] = ids
        for i, j in itertools.permutations(ids, 2):
            crossings.setdefault(i, []).append((j, via_penalty_mm))
    source_ids = {i for face, xy in starts if (i := node(face, xy)) is not None}
    target_ids = {i for face, xy in ends if (i := node(face, xy)) is not None}
    assert source_ids and target_ids
    print('Costed graph:', len(nodes), 'nodes;', len(points), 'via positions;', area_count, 'pair regions', flush=True)
    measured, paths, forbidden, history = {}, {}, set(), []
    result = None
    for refinement in range(max_refinements):
        if time.monotonic() >= deadline:
            break
        selected = shortest_path(nodes, members, crossings, source_ids, target_ids, measured, forbidden)
        if refinement % 10 == 0:
            print('Cost refinement', refinement, 'measured edges', len(measured), 'selected nodes', len(selected or []), flush=True)
        if selected is None:
            break
        uncertain = [(i, j) for i, j in zip(selected, selected[1:]) if nodes[i][0] == nodes[j][0] and tuple(sorted((i, j))) not in measured]
        if uncertain:
            # Validate the longest optimistic leg first; it is most likely to
            # conceal the perimeter detour that the unweighted search missed.
            i, j = max(uncertain, key=lambda e: math.dist(nodes[e[0]][2], nodes[e[1]][2]))
            face, component, start = nodes[i]
            end = nodes[j][2]
            path = polygon_route(frozen, net, face, start, end, regions[face][component], min(deadline, time.monotonic()+12))
            key = tuple(sorted((i, j)))
            if path is None:
                measured[key] = math.inf
                history.append(dict(edge=[i, j], found=False))
            else:
                length = LineString(path).length if len(path) > 1 else 0.
                assert length + 1e-7 >= math.dist(start, end)
                measured[key] = length
                paths[key] = (i, path)
                history.append(dict(edge=[i, j], found=True, planar_length_mm=length))
            continue
        vias = []
        for i, j in zip(selected, selected[1:]):
            if nodes[i][0] != nodes[j][0] and nodes[i][2] not in vias:
                assert nodes[i][2] == nodes[j][2]
                vias.append(nodes[i][2])
        collision = next(((p, q) for p, q in itertools.combinations(vias, 2) if math.dist(p, q) <= .563), None)
        if collision:
            # A conservative branch: discard one candidate position. This is
            # deliberately not advertised as exhaustive joint-via search.
            forbidden.update(point_nodes[collision[1]])
            history.append(dict(rejected_close_via_pair=collision, omitted_candidate=collision[1]))
            continue
        runs = []
        for i, j in zip(selected, selected[1:]):
            if nodes[i][0] != nodes[j][0]:
                continue
            direction, path = paths[tuple(sorted((i, j)))]
            path = path if direction == i else list(reversed(path))
            if len(path) > 1 and LineString(path).length > 1e-7:
                runs.append((nodes[i][0], path))
        assert all(screen.legal(net, face, path) for face, path in runs)
        assert all(screen.via_legal(net, xy) for xy in vias)
        result = dict(runs=runs, vias=vias)
        break
    return dict(route=result, graph_nodes=len(nodes), candidate_via_positions=len(points), pair_via_regions=area_count,
                measured_planar_edges=len(measured), refinements=history, deadline_reached=time.monotonic() >= deadline,
                via_penalty_mm=via_penalty_mm, global_optimum_proven=False, global_infeasibility_proven=False)
