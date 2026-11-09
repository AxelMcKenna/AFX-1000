exec(open('/private/tmp/finish_permission_reference_branches_v2.py').read().split('for d,xy in sorted')[0])
counts=[0,0,0,0];options=[]
for d,xy in sorted((math.dist(o['position_mm'],[x*.25,y*.25]),[x*.25,y*.25]) for x in range(548,585) for y in range(512,549)):
 if d>7 or not screen.via_legal(net,xy):continue
 counts[0]+=1;v=dict(ref='E_R107',pin='2',net=net,position_mm=xy,size_mm=.6,drill_mm=.3)
 if not any(inner_free(v,l) for l in ['In2.Cu','In3.Cu','In6.Cu']):continue
 counts[1]+=1;result=screen.simple(net,'B.Cu',o['position_mm'],xy,12)
 if not result:continue
 counts[2]+=1;area=LineString(result[1]).buffer(.1).difference(ground.buffer(.0015).union(holes).union(Point(xy).buffer(.515))).area
 if area>=1e-6:continue
 counts[3]+=1;options.append((d,xy,min(Point(xy).distance(q) for q in qfields),result[1]))
print('COUNTS',counts,flush=True)
for row in options[:20]:print('OPTION',row,flush=True)
