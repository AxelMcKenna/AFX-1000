import numpy as np,json
segments=[([234,55,32],[246,62,32],4.5),([246,62,32],[265,69.1891892,28],4.5),([265,69.1891892,28],[283,76,28],4.5),([283,76,28],[293,82,25.1],4.5)]
for x in [230,232.54,235.08,237.62]:segments.append(([x,55,24.89],[234,55,32],.7))
def clearance(points):
 best=1e6
 for a,b,r in segments:
  a=np.array(a);d=np.array(b)-a;t=np.clip(((points-a)@d)/(d@d),0,1);dist=np.linalg.norm(points-(a+t[:,None]*d),axis=1)
  best=min(best,float(dist.min())-r-.65)
 return best
out=[]
for x in [230,232.54,235.08,237.62]:
 best=(-1e9,None)
 for deg in np.arange(0,360,.5):
  a=np.deg2rad(deg);t=np.linspace(0,np.pi/2,181);p=np.array([x,59,25.65])+13*(np.outer(1-np.cos(t),[np.cos(a),np.sin(a),0])+np.outer(np.sin(t),[0,0,1]));gap=clearance(p)
  if gap>best[0]:best=(gap,float(deg))
 out.append(dict(x=x,best_gap=best[0],azimuth=best[1]))
print(json.dumps(out,indent=2))
