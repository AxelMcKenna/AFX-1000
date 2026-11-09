exec(open('/private/tmp/diagnose_startup_follow3.py').read().split('for t in anchors:')[0].replace("exec(s[:s.index('# Restore every')])", "exec(s[:s.index('# Restore every')].replace('from startup_layer_hop import', 'from startup_layer_hop_v2 import'))"))
label='FOLLOW3 to digital eFuse enable';candidates=[]
anchor=next(t for t in anchors if t['kind']=='PCB_VIA');net=o['net']
for xy in [[x,y] for y in [136.,138.,140.,142.,144.] for x in [144.,145.,146.,147.,148.,142.,140.,138.]]:
 if not screen.via_legal(net,xy) or any(Point(xy).distance(q)<.6 for q in qfields):continue
 v=dict(ref='E_R120',pin='1',net=net,position_mm=xy,size_mm=.6,drill_mm=.3)
 if not any(inner_free(v,l) for l in ['In2.Cu','In3.Cu','In6.Cu']):continue
 for layer in ['F.Cu','B.Cu']:
  result=screen.simple(net,layer,anchor['position_mm'],xy,30)
  path=result[1] if result else None
  if path:candidates.append((LineString(path).length+math.dist(xy,source['position_mm']),v,layer,path))
print('CANDIDATES',len(candidates),[(v['position_mm'],l) for d,v,l,path in sorted(candidates,key=lambda row:row[0])[:12]],flush=True)
for _,v,layer,path in sorted(candidates,key=lambda row:row[0])[:12]:
 r=connect(source,[v],label)
 if not r:continue
 viaadd(v);add(net,layer,path,label+' surface transition');r['target_uuid']=o['uuid'];r['target']=['E_R120','1'];r['surface_anchor_uuid']=anchor['uuid'];joins.append(r);deferred=[d for d in deferred if d['label']!=label];break
if not deferred:
 p['retired_objects']=sorted(set(p['retired_objects'])|{'b1874fb2-be39-5995-b7e2-8da9b4f3b8df'})
 Path('/private/tmp/startup-completion-routes-v10.json').write_text(json.dumps(dict(moves=p['moves'],retired_objects=p['retired_objects'],side_reconciliations=p['side_reconciliations'],cells=p['cells'],routes=new,extra_vias=extra,joins=joins,deferred=deferred,native_validation_pending=True),indent=2)+'\n')
print('RESULT',len(joins),len(new),len(extra),len(deferred),flush=True)
