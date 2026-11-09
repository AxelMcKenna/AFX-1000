import sys,itertools,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
s=Path('/private/tmp/pack_analog_cells_v2.py').read_text();exec(s[:s.index('def place(')])
started=time.monotonic();pools={};roles={};owners={};anchors={}
for chip,ilm,dvdt,capref,pull in cells:
 pp={o['pin']:o['position_mm'] for o in objects if o.get('ref')==chip}
 for ref,role,pin,limit in [(ilm,'ILM','9',3.8),(dvdt,'DVDT','7',4.5),(capref,'CAP','7',5.0),(pull,'EN','1',3.8)]:
  roles[ref]=role;owners[ref]=chip;anchors[ref]=pp;target=pp[pin];pool=[]
  sites=sorted((math.hypot(ix*.5,iy*.5),[round(target[0]+ix*.5,4),round(target[1]+iy*.5,4)],rot,flip) for ix in range(-12,13) for iy in range(-12,13) if math.hypot(ix*.5,iy*.5)<=6 for rot in [0,90,180,270] for flip in [False,True])
  for radius,xy,rot,flip in sites:
   t=trial(ref,xy,rot,flip)
   if not t:continue
   f,g,os=t;by={o['pin']:o for o in os};p1=by['1']['position_mm'];p2=by['2']['position_mm'];d=math.dist(p1,target)
   if d>limit:continue
   ground=math.dist(p2,pp['8']) if role!='DVDT' else 0
   if ground>7:continue
   score=d+.35*ground+(.3 if first(f,'layer')[1]=='F.Cu' else 0)
   pool.append(dict(ref=ref,xy=xy,rot=rot,flip=flip,side=first(f,'layer')[1][0],g=g,q=g.buffer(.3,join_style=2),os=os,score=score))
   if len(pool)>=240:break
  # Keep geometrically diverse candidates, then a bounded beam can place all cells together.
  pool.sort(key=lambda p:p['score']);selected=[]
  for row in pool:
   if any(row['side']==p['side'] and row['g'].symmetric_difference(p['g']).area<.05 for p in selected):continue
   selected.append(row)
   if len(selected)>=100:break
  assert selected,ref;pools[ref]=selected;print('POOL',ref,len(selected),'best',round(selected[0]['score'],3),flush=True)
  assert time.monotonic()-started<240,'bounded placement search expired'
# Pairwise courtyard and local DVDT link constraints, solved jointly by MRV.
refs=list(pools);pairs={cap:dvdt for chip,ilm,dvdt,cap,pull in cells};pairs.update({v:k for k,v in pairs.items()})
conflicts={};paircost={}
for a,b in itertools.combinations(refs,2):
 masks=[0]*len(pools[a]);reverse=[0]*len(pools[b]);costs={}
 for i,p in enumerate(pools[a]):
  x0,y0,x1,y1=p['q'].bounds
  for j,q in enumerate(pools[b]):
   u0,v0,u1,v1=q['g'].bounds
   bad=p['side']==q['side'] and min(x1,u1)-max(x0,u0)>1e-8 and min(y1,v1)-max(y0,v0)>1e-8
   extra=0.
   if pairs.get(a)==b:
    dr=p if roles[a]=='DVDT' else q;cr=q if roles[a]=='DVDT' else p
    p2=next(o['position_mm'] for o in dr['os'] if o['pin']=='2');p1=next(o['position_mm'] for o in cr['os'] if o['pin']=='1');dist=math.dist(p2,p1)
    bad=bad or dist>5.5;extra=.8*dist+(.8 if dr['side']!=cr['side'] else 0)
   if bad:masks[i]|=1<<j;reverse[j]|=1<<i
   costs[i,j]=extra
 conflicts[a,b]=masks;conflicts[b,a]=reverse;paircost[a,b]=costs;paircost[b,a]={(j,i):v for (i,j),v in costs.items()}
best=[float('inf'),None];nodes=0;solutions=0;search_start=time.monotonic()
def indices(mask):
 while mask:
  bit=mask&-mask;yield bit.bit_length()-1;mask-=bit
def dfs(chosen,domains,cost):
 global nodes,solutions
 nodes+=1
 if nodes>300000 or time.monotonic()-search_start>120:return
 if not domains:
  solutions+=1
  if cost<best[0]:best[:]=[cost,dict(chosen)];print('SOLUTION',solutions,'cost',round(cost,3),'nodes',nodes,flush=True)
  return
 lower=cost+sum(min(pools[r][i]['score'] for i in indices(mask)) for r,mask in domains.items())
 if lower>=best[0]:return
 ref=min(domains,key=lambda r:domains[r].bit_count())
 choices=[]
 for i in indices(domains[ref]):
  inc=pools[ref][i]['score']+sum(paircost[ref,r][i,j] for r,j in chosen.items());choices.append((inc,i))
 for inc,i in sorted(choices):
  if cost+inc>=best[0]:continue
  remain={r:mask&~conflicts[ref,r][i] for r,mask in domains.items() if r!=ref}
  if any(not mask for mask in remain.values()):continue
  dfs(dict(chosen,**{ref:i}),remain,cost+inc)
dfs({}, {r:(1<<len(p))-1 for r,p in pools.items()},0.)
print('SEARCH',nodes,'solutions',solutions,'seconds',round(time.monotonic()-search_start,2),flush=True)
assert best[1], 'No complete packing within bounded candidate domains'
beam=[(best[0],{r:pools[r][i] for r,i in best[1].items()})]
score,chosen=beam[0];moves={r:[p['xy'],p['rot'],p['flip']] for r,p in chosen.items()};updated=dict(fps)
for ref,(xy,rot,flip) in moves.items():
 updated[ref]=rotate_footprint(fps[ref],xy,rot)
 if flip:updated[ref]=flip_layers(updated[ref])
mechanical_check(updated,set(moves),placement)
result=dict(moves=moves,retired_objects=sorted(retire),reconciled_existing_passive_sides=side_reconciliations,search_score=score,search_nodes=nodes,search_solutions=solutions,candidate_counts={r:len(p) for r,p in pools.items()},scope='Joint local packing; native poses, routing and reference validation remain mandatory')
Path('/private/tmp/analog-cell-placement-joint-01.json').write_text(json.dumps(result,indent=2)+'\n')
for r,p in chosen.items():print('PLACED',r,p['xy'],p['rot'],p['flip'],p['side'],flush=True)
print('DONE',round(time.monotonic()-started,2),flush=True)
