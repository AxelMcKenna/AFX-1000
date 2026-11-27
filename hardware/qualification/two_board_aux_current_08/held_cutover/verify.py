from pathlib import Path
import hashlib,json
from ..schematic_candidate.verify import verify,netlist
from .build import CAPS,MPN,URL
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
 manifest=json.loads((HERE/'authored/candidate.json').read_text())
 assert hashlib.sha256((HERE/'primary/c0805c104k5ractu.pdf').read_bytes()).hexdigest()==manifest['capacitor_primary_sha256']
 verify(HERE.parent/'held_rail/authored',here=HERE)
 old,_=netlist(HERE/'native-03/baseline-netlist.xml');new,_=netlist(HERE/'native-03/candidate-netlist.xml')
 for ref,c in new.items():
  fields={x.attrib['name']:x.text or '' for x in c.findall('./fields/field')};prior={x.attrib['name']:x.text or '' for x in old[ref].findall('./fields/field')}
  assert c.findtext('footprint')==old[ref].findtext('footprint')
  if ref in CAPS:assert fields.get('MPN')==MPN and c.findtext('datasheet')==URL
  else:assert fields.get('MPN')==prior.get('MPN') and c.findtext('datasheet')==old[ref].findtext('datasheet')
 print('Exact capacitor MPNs and all inherited footprint assignments verified')
