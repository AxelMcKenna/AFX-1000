"""Classify each captured interface individually; never turn test pads into cables."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parent;source=R.parent/'installation-audit.json'
out=[]
for c in json.loads(source.read_text())['connectors']:
 ref,value=c['ref'],c['value'];n=len(c['pads']);mate=None
 if 'probe' in value.lower() or ref=='P_J22':state='Test access; no operating harness selected'
 elif ref.startswith('N_J'):
  state='NF module physical interface unresolved; requires current electrical contract and current rating before mate adoption'
  if ref=='N_J6':mate='XHP-2 / SXH-001T-P0.6, candidate only; source explicitly unaccepted'
 elif 'B' + str(n) + 'B-XH' in value:
  state='Source identifies JST XH board family; compatible mating family candidate'
  mate=f'JST XHP-{n} / SXH-001T-P0.6; verify insulation OD 0.9–1.9 mm, current and tooling per circuit'
 elif 'PHR-2' in value:
  state='Source-selected board and cable mate';mate='JST PHR-2 / SPH-002T-P0.5S'
 elif 'DIRECT_SOLDER' in value or 'Alpha3079' in value:state='Direct solder source proposal; physical retention and current qualification remain'
 elif '7466003' in value:state='M3 power terminal; exact ring lug, wire gauge and torque remain unselected'
 elif 'Header' in value or 'Conn_' in value:state='Generic header; exact male manufacturer, mating housing/contact and cable remain unselected'
 else:state='Individual interface review required; do not infer mating harness from pad count'
 out.append(dict(board=c['board'],reference=ref,value=value,status=state,mating_candidate=mate,pads=c['pads'],footprint=c['footprint'],installed_box=c['body_box']))
result=dict(scope='Per-interface electrical pad inventory and mate selection status. Not a released cut list, cable topology or declaration that all 78 entries require operating harnesses.',source_sha256={source.name:hashlib.sha256(source.read_bytes()).hexdigest()},interfaces=out,source_links=['https://www.jst-mfg.com/product/index.php?lang=2&series=277','https://www.jst-mfg.com/product/pdf/eng/eXH.pdf'])
(R/'interface-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print('Classified',len(out),'interfaces')
