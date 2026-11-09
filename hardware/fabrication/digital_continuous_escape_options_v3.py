"""Find conventional-via escape options inside actual polygon free space."""
import math,time
from shapely.geometry import Point,box,LineString
from shapely.ops import unary_union,nearest_points
from hardware.fabrication.digital_visibility_escape import route as visibility_route
import hardware.fabrication.route_nf_surface as surface
import hardware.fabrication.nf_pin_escape_routes as raster
import hardware.fabrication.digital_native_spacing_search_v2 as search


def escape_options(screen,net,contacts,key,deadline,target_layer='In5.Cu'):
    assert target_layer in ('In3.Cu','In5.Cu')
    existing=[dict(point=p,layers=[target_layer],runs=[],vias=[],cost=0.,group=key)
              for face,p in sorted(contacts) if face==target_layer]
    if existing:return existing
    via_free=screen.via_outline.difference(screen.obstacles(net));options=[];seen=set();free_cache={}
    for face,xy in sorted(contacts):
        if time.monotonic()>deadline:break
        start=Point(xy)
        if face not in free_cache:
            obstacles=[g.buffer(d+.0005,quad_segs=32) for n,g,d in screen.geometry[face] if n!=net]
            obstacles += [g.buffer(.4105,quad_segs=32) for n,l,g in screen.added if n!=net and l==face]
            obstacles += [Point(p).buffer(.5105,quad_segs=32) for n,p in screen.new_vias if n!=net]
            free_cache[face]=screen.outline.difference(unary_union(obstacles))
        free=free_cache[face];regions=[free] if free.geom_type=='Polygon' else list(free.geoms)
        regions=[g for g in regions if g.covers(start)]
        targets=[]
        for region in regions:
            available=region.intersection(via_free).intersection(start.buffer(8)).buffer(-.005)
            geoms=[available] if available.geom_type=='Polygon' else list(getattr(available,'geoms',[]))
            for g in geoms:
                if g.is_empty or g.area<1e-8:continue
                for point in [nearest_points(start,g)[1],g.representative_point(),g.centroid]:
                    p=(round(point.x,6),round(point.y,6))
                    if (face,p) in seen or not screen.via_legal(net,p):continue
                    seen.add((face,p));targets.append(p)
        for target in sorted(targets,key=lambda p:math.dist(xy,p)):
            if time.monotonic()>deadline:break
            if math.dist(xy,target)<1e-7:
                options.append(dict(point=target,layers=[target_layer],runs=[],vias=[target],cost=2.5,group=key))
                continue
            paths=[p for p in surface.candidate_paths(xy,target) if screen.legal(net,face,p)]
            path=min(paths,key=lambda p:LineString(p).length) if paths else None
            if path is None:
                old=(screen.outline,search.LAYERS,search.STEP,raster.STEP,raster.RASTER_MARGIN)
                try:
                    screen.outline=screen.outline.intersection(box(min(xy[0],target[0])-3,min(xy[1],target[1])-3,max(xy[0],target[0])+3,max(xy[1],target[1])+3))
                    search.LAYERS=(face,);search.STEP=raster.STEP=.05;raster.RASTER_MARGIN=math.sqrt(2)*.05/2+.002
                    def portal(p):return dict(point=p,layers=[face],runs=[],vias=[],cost=0.,group=key)
                    result=search.route_multi(screen,net,[portal(xy)],{face:[portal(target)]},min(deadline,time.monotonic()+3),max_visits=400000)
                    if result is not None:
                        assert len(result['runs'])==1 and not result['vias']
                        path=result['runs'][0][1]
                finally:screen.outline,search.LAYERS,search.STEP,raster.STEP,raster.RASTER_MARGIN=old
            if path is None and time.monotonic()<deadline:
                path=visibility_route(screen,net,face,xy,target,free_cache[face],min(deadline,time.monotonic()+5))
            if path is None:continue
            assert screen.legal(net,face,path) and screen.via_legal(net,target)
            options.append(dict(point=target,layers=[target_layer],runs=[(face,path)],vias=[target],cost=LineString(path).length+2.5,group=key))
            if len(options)>=48:break
        if len(options)>=48:break
    return sorted(options,key=lambda r:r['cost'])
