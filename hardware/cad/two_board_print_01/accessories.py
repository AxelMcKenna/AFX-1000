"""Inventory exact retained A11 prototype controls; no invented PCB carriers."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
 c=json.loads((ROOT/'capture.json').read_text());buttons=c['buttons'];knobs=c['knobs'];rows=[]
 def add(name,family,index=0,quantity=1,material='opaque PETG prototype'):
  rows.append(dict(name=name,family=family,index=index,quantity=quantity,material=material))
 for i,b in enumerate(buttons):add('button_'+b[0],'button',i)
 groups={}
 for i,b in enumerate(buttons):
  key=json.dumps(b[8]);groups.setdefault(key,[i,0]);groups[key][1]+=1
 for n,(i,q) in enumerate(groups.values()):add('holder_'+str(n+1),'holder',i,q)
 add('retaining_clip','clip',quantity=len(buttons))
 groups={}
 for i,k in enumerate(knobs):
  key=(k[3],k[4]);groups.setdefault(key,[i,0]);groups[key][1]+=1
 for (d,h),(i,q) in groups.items():add(f'knob_{d:g}x{h:g}','knob',i,q)
 add('selector_cap','selector_cap',quantity=2)
 for name,q in [('touch_lens',1),('ring_lens',1),('meter_lens',2),('bank_lens',4),('display_lens',1)]:add(name,name,quantity=q,material='translucent prototype; optical performance unqualified')
 add('shaft_coupon','shaft_coupon')
 (ROOT/'accessory-inventory.json').write_text(json.dumps(rows,indent=2)+'\n')
 out='// Exact retained A11 accessory geometry; quantities in accessory-inventory.json.\ninclude <housing.scad>\n'
 for r in rows:
  f=r['family'];i=r['index'];expr={'button':f'translate([0,0,cap_under+cap_thick])rotate([180,0,0])key(buttons[{i}]);','holder':f'translate([0,0,board_drop+1.6])switch_holder(buttons[{i}]);','clip':'retaining_clip();','knob':f'knob(knobs[{i}][3],knobs[{i}][4]);','selector_cap':'rotate([180,0,0])translate([0,0,-5.2])selector_cap();','ring_lens':'rotate([180,0,0])translate([0,0,-.8])ring_lens();','display_lens':'rotate([180,0,0])translate([0,0,-.9])display_lens();'}.get(f,f+'();')
  out+=f'if(part=="{r["name"]}"){expr}\n'
 (ROOT/'accessories.scad').write_text(out)
 print(json.dumps(dict(unique_meshes=len(rows),quantities=sum(r['quantity'] for r in rows),buttons=len(buttons),holders=len(groups))))
if __name__=='__main__':main()
