"""Same-layer fills are obstacles unless a named local cutback is explicitly allowed."""
from shapely.ops import unary_union
from ..routed.plan import shape

def obstacles(zones,layer,net,width,cutback_ids=()):
 allowed=set(cutback_ids);by={z['uuid']:z for z in zones};assert allowed<=set(by)
 for uid in allowed:
  z=by[uid];assert z['layer']==layer and z['net']!=net and not z['keepout'],'Cutback permission cannot waive a keepout or different-layer rule'
 blocked=[]
 for z in zones:
  if z['layer']!=layer:continue
  if z['keepout'] and z.get('prohibit_tracks',False):blocked.append(shape(z['authored_outline']).buffer(width/2+.002))
  elif z['net']!=net and z['uuid'] not in allowed:blocked.append(shape(z['polygons']).buffer(.2+width/2+.002))
 return unary_union(blocked)
