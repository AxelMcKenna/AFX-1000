"""Explicit 34-instance assembly hierarchy and source-bound main-board boundary."""
import csv,copy,json,re,sys,uuid,os
from collections import defaultdict
from contracts import *
sys.path.insert(0,str(REPO/'hardware/electronics'))
from common.flat_schematic import generate
from common.sexpr import *
P=R/'assembly';PROJECT='panel';ROOT=str(uuid.uuid5(uuid.NAMESPACE_URL,'tbh-panel-root'))
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'tbh-panel-'+s))
def normalized(n):return n.strip('/').replace('/','__')
def rows(path):return list(csv.DictReader((CONTROLS/path).open()))
def build():
 P.mkdir(exist_ok=True);instances=[];connections=[];channels={};boundary={};sheets=[];allcomponents=[]
 main=read_sexpr((REPO/'hardware/fabrication/staging/two-board-signal-routed-native-03/signal_main.kicad_pcb').read_text());mainpads={}
 for f in children(main,'footprint'):
  props={p[1]:p[2] for p in children(f,'property')}
  for pad in children(f,'pad'):
   ns=children(pad,'net')
   if ns:mainpads[(props['Reference'],pad[1])]=ns[0][-1]
 def endpoint(ref,pin,net):
  assert mainpads[(ref,str(pin))]==net,(ref,pin,net)
  boundary[(ref,str(pin))]=net;return normalized(net)
 def wiremap(rs,key,padkey='pad',refkey='main_connector',channelkey='channel'):
  maps=defaultdict(dict)
  for r in rs:
   name=r[key];net=endpoint(r[refkey],r['main_pin'],r['net']);maps[name][r[padkey]]=net
   connections.append(dict(instance=name,pad=r[padkey]+'.1',main_reference=r[refkey],main_pin=r['main_pin'],main_net=r['net']))
   if r[channelkey]!='':
    ch=int(r[channelkey]);assert ch not in channels;channels[ch]=dict(instance=name,pad=r[padkey]+'.1',net=net)
  return maps
 leds=wiremap(rows('led_follow_on/wiring.csv'),'board');buttons=wiremap(rows('button_follow_on/wiring.csv'),'button')
 rr=rows('ring_follow_on/wiring.csv')
 for r in rr:r['instance']='ring'
 ring=wiremap(rr,'instance','ring_pad','connector','logical_channel')
 interfaces=json.loads((R/'reference/panel-contract.json').read_text())
 def sheet(name,cs,description):
  index=len(sheets)+2;folder=P/name;folder.mkdir(exist_ok=True)
  for i,c in enumerate(cs):c.update(x=63.5+(i%3)*127,y=63.5+(i//3)*101.6)
  revision='ASSY_'+name
  generate(folder,revision,PROJECT,cs,[(15,12,description)],(420,max(150,95+((len(cs)+2)//3)*101.6)),[])
  file=folder/'panel.kicad_sch';sch=read_sexpr(file.read_text());sheetid=uid(name)
  for symbol in children(sch,'symbol'):
   proj=first(first(symbol,'instances'),'project');proj[1]=PROJECT;first(proj,'path')[1]='/'+ROOT+'/'+sheetid
  for label in children(sch,'label'):
   justify=first(first(label,'effects'),'justify');left=justify[1]=='right';justify[:]=[a('justify'),a('right' if left else 'left')]
   first(label,'at')[3]=a(180 if left else 0);label[0]=a('global_label');label.insert(2,[a('shape'),a('passive')]);label.insert(3,[a('fields_autoplaced')])
  # Local libraries stay independently editable; root library table collects all children.
  file.write_text(sexpr(sch)+'\n');sheets.append(dict(name=name,uuid=sheetid,page=index,revision=revision));allcomponents.extend(cs)
 def board(name,design,ports):
  idx=len(instances)+1;spec=contract(design);cs=copy.deepcopy(spec['components']);mapping={c['ref']:re.sub(r'\d+$','',c['ref'])+str(idx).zfill(2)+str(j+1).zfill(3) for j,c in enumerate(cs)}
  nets={n:ports.get(w,normalized(name)+'__'+n) for w,n in spec['ports'].items()}
  for c in cs:
   c['ref']=mapping[c['ref']]
   for p in c['pins']:p['net']=nets.get(p['net'],normalized(name)+'__'+p['net'])
  instances.append(dict(instance=name,design=design,pcb=spec['pcb'],ref_map=mapping,external_ports=ports,net_map={n:nets.get(n,normalized(name)+'__'+n) for n in groups(spec['components'])}))
  sheet(name,cs,f'{name}: {design} passive PCB; instance {idx}/34; local references in manifest')
 for selector in interfaces['selectors']:
  ports={}
  for w in selector['wires']:
   m=w['main'];ports[w['pad'].split('.')[0]]=endpoint(m['reference'],m['pin'],m['net'])
   connections.append(dict(instance=selector['id'],pad=w['pad'],main_reference=m['reference'],main_pin=m['pin'],main_net=m['net']))
  board(selector['id'],selector['id'],ports)
 for name,ports in leds.items():board(name,'bank' if name.startswith('bank_') else name,ports)
 board('ring','ring',ring['ring'])
 button_design={r['button']:r['design'] for r in rows('button_follow_on/wiring.csv')}
 for name,ports in buttons.items():board(name,button_design[name],ports)
 assert len(instances)==34
 def component(ref,part,pins,source='',note=''):
  return dict(ref=ref,part=part,footprint='',source=source,note=note,pins=[dict(number=str(n),name=label,kind='passive',side='L' if i%2==0 else 'R',net=net) for i,(n,label,net) in enumerate(pins)])
 ds=defaultdict(list)
 for r in rows('display-wiring.csv'):
  net=endpoint(r['main_connector'],r['main_pin'],r['net']);ds[r['display']].append((r['manufacturer_pin'],r['function'],net))
  connections.append(dict(instance=r['display'],pad=r['manufacturer_pin'],main_reference=r['main_connector'],main_pin=r['main_pin'],main_net=r['net']))
  if r['logical_channel']!='':
   ch=int(r['logical_channel']);assert ch not in channels;channels[ch]=dict(instance=r['display'],pad=r['manufacturer_pin'],net=net)
 sheet('displays',[component('DS'+str(i+1),'SA36-11YWA',pins,'https://www.kingbrightusa.com/images/catalog/SPEC/SA36-11YWA.pdf',name) for i,(name,pins) in enumerate(ds.items())],'Three directly wired common-anode display digits; manufacturer pin numbers')
 pots=[]
 for i,pot in enumerate(interfaces['pots']):
  pins=[(m['pin'],('WIPER' if m['pin']=='2' else 'END'),endpoint(m['reference'],m['pin'],m['net'])) for m in pot['main']]
  pots.append(component('RV'+str(i+1),'10k linear - detent TBD',pins,'https://www.bourns.com/docs/product-datasheets/PTV09.pdf',pot['id']+'; 6025F no-detent vs 6225F center-detent allocation unresolved'))
 sheet('pots',pots,'10k pots; terminal2 wiper; detent allocation and exact procurement suffix unresolved')
 controls=[]
 for i,front in enumerate(interfaces['front_inputs']):
  if front['receiver_kind']!='B3F-1000 momentary':continue
  m=front['signal'];net=endpoint(m['reference'],m['pin'],m['net'])
  controls.append(component('SW'+str(900+i),'B3F-1000',[(1,'CONTACT_A',net),(2,'A_DUPLICATE',net),(3,'CONTACT_B','LINK_AGND'),(4,'B_DUPLICATE','LINK_AGND')],'https://components.omron.com/sites/default/files/datasheet_pdf/A036-E1.pdf',front['id']+'; wires on1/3 only,2/4 internal short terminals'))
 sheet('switches',controls,'Momentary contacts:1-2 and3-4 internally common; press bridges pairs; wire1 and3 only')
 boundarycs=[]
 for i,ref in enumerate(sorted({r for r,p in boundary})):
  pins=[(pin,ref+'_'+pin,normalized(net)) for (r,pin),net in sorted(boundary.items(),key=lambda x:(x[0][0],int(x[0][1]))) if r==ref]
  boundarycs.append(component('J'+str(800+i),ref+' MAIN_BOUNDARY',pins,note='Electrical boundary only, exact mating geometry in harness package'))
 sheet('main_boundary',boundarycs,'Source-bound main-board header pins; boundary symbols are not additional physical connectors')
 assert set(channels)==set(range(96))
 root=[a('kicad_sch'),[a('version'),a(20250114)],[a('generator'),a('eeschema')],[a('uuid'),a(ROOT)],[a('paper'),'User',a(500),a(600)],[a('lib_symbols')],[a('sheet_instances'),[a('path'),'/',[a('page'),'1']]]]
 for i,s in enumerate(sheets):
  x=25+(i%4)*120;y=30+(i//4)*50
  root.append(read_sexpr(f'(sheet (at {x} {y}) (size 100 25) (stroke (width 0) (type default)) (fill (color 0 0 0 0)) (uuid {s["uuid"]}) (property "Sheetname" "{s["name"]}" (at {x} {y-1.27} 0) (effects (font (size 1.27 1.27)) (justify left bottom))) (property "Sheetfile" "{s["name"]}/panel.kicad_sch" (at {x} {y+26.27} 0) (effects (font (size 1.27 1.27)) (justify left top))) (instances (project "panel" (path "/{ROOT}" (page "{s["page"]}")))))'))
 root.append([a('embedded_fonts'),a('no')]);(P/'panel.kicad_sch').write_text(sexpr(root)+'\n');(P/'panel.kicad_pro').write_text(json.dumps({'meta':{'filename':'panel.kicad_pro','version':1}})+'\n')
 (P/'sym-lib-table').write_text('(sym_lib_table (version 7) '+''.join(f'(lib (name "RMX_{s["revision"]}") (type "KiCad") (uri "${{KIPRJMOD}}/{s["name"]}/RMX_{s["revision"]}.kicad_sym") (options "") (descr "Assembly circuit"))' for s in sheets)+')\n')
 (P/'fp-lib-table').write_text('(fp_lib_table (version 7) '+''.join(f'(lib (name "{lib}") (type "KiCad") (uri "${{KIPRJMOD}}/{os.path.relpath((CONTROLS/path).parent/(lib+".pretty"),P)}") (options "") (descr "Frozen layout"))' for lib,path in {lib:path for path,lib in DESIGNS.values()}.items())+')\n')
 manifest=dict(passive_board_instances=instances,channels=channels,connections=connections,main_boundary=[dict(reference=r,pin=p,net=n) for (r,p),n in boundary.items()],sheets=sheets,components=allcomponents,fabrication_released=False)
 (R/'assembly-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':build()
