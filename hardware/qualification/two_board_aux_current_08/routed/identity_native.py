"""Reconcile source pads without UUIDs using complete native physical identities."""
import json,sys,hashlib
from pathlib import Path
import pcbnew
from hardware.electronics.common.sexpr import read_sexpr,children,first
source=Path(sys.argv[1]);candidate=Path(sys.argv[2]);out=Path(sys.argv[3])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tree=read_sexpr(source.read_text());pads=[p for f in children(tree,'footprint') for p in children(f,'pad')];explicit=[str(first(p,'uuid')[1]) for p in pads if children(p,'uuid')];assert len(explicit)==len(set(explicit));anonymous_count=len(pads)-len(explicit)
def polygons(p):
 def pts(c):return [[c.CPoint(i).x,c.CPoint(i).y] for i in range(c.PointCount())]
 return [{'outer':pts(p.COutline(i)),'holes':[pts(p.CHole(i,j)) for j in range(p.HoleCount(i))]} for i in range(p.OutlineCount())]
def identity(p,b):
 f=p.GetParentFootprint();copper={}
 for l in b.GetEnabledLayers().CuStack():
  if p.IsOnLayer(l):
   q=pcbnew.SHAPE_POLY_SET();p.TransformShapeToPolygon(q,l,0,pcbnew.FromMM(.001),pcbnew.ERROR_OUTSIDE);q.Simplify();copper[b.GetLayerName(l)]=polygons(q)
 return {'ref':f.GetReference(),'pin':p.GetNumber(),'position_nm':[p.GetPosition().x,p.GetPosition().y],'orientation_degrees':p.GetOrientation().AsDegrees()%360,'footprint_position_nm':[f.GetPosition().x,f.GetPosition().y],'footprint_orientation_degrees':f.GetOrientationDegrees()%360,'side':f.GetLayerName(),'shape':int(p.GetShape()),'size_nm':[p.GetSize().x,p.GetSize().y],'drill_nm':[p.GetDrillSize().x,p.GetDrillSize().y],'drill_shape':int(p.GetDrillShape()),'attribute':int(p.GetAttribute()),'layers_hex':p.GetLayerSet().FmtHex(),'offset_nm':[p.GetOffset().x,p.GetOffset().y],'roundrect_radius_ratio':p.GetRoundRectRadiusRatio(),'chamfer_ratio':p.GetChamferRectRatio(),'net':p.GetNetname(),'copper_polygons_nm':copper}
b=pcbnew.LoadBoard(str(source));after=pcbnew.LoadBoard(str(candidate));before={p.m_Uuid.AsString():identity(p,b) for f in b.GetFootprints() for p in f.Pads()};now={p.m_Uuid.AsString():identity(p,after) for f in after.GetFootprints() for p in f.Pads()};assert set(explicit)<=set(before)
for u in explicit:assert u in now and before[u]==now[u],('Explicit pad changed',u)
anonymous=[{'uuid':u,'identity':i} for u,i in before.items() if u not in set(explicit)];assert len(anonymous)==anonymous_count;refs={r['identity']['ref'] for r in anonymous}
result={'native_version':pcbnew.Version(),'source_sha256':sha(source),'candidate_sha256':sha(candidate),'explicit_source_pads_checked':len(explicit),'explicit_pad_identities_unchanged':True,'source_anonymous_pad_count':anonymous_count,'baseline_anonymous':anonymous,'candidate_relevant_pads':[{'uuid':u,'identity':i} for u,i in now.items() if i['ref'] in refs]}
(out/'pad-identities.json').write_text(json.dumps(result,indent=2)+'\n');print({'anonymous':anonymous_count,'explicit':len(explicit)})
