"""Audit electrical branch connectivity and nonduplicated LED load ownership."""
from pathlib import Path
import csv,copy,hashlib,json,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
REF=HERE/'reference'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def sources():
    rows=[]
    for name,h in json.loads((REF/'source-manifest.json').read_text()).items():
        assert digest(REF/name)==h,name
        for r in csv.DictReader((REF/name).open()):
            if 'display' in r: receiver=r['display'];terminal=r['manufacturer_pin'];channel=r['logical_channel']
            elif 'board' in r:receiver=r['board'];terminal=r['pad']+'.'+r['pin'];channel=r['channel']
            elif 'ring_pad' in r:receiver='touch_ring';terminal=r['ring_pad']+'.'+r['pin'];channel=r['logical_channel']
            else:receiver='button_'+r['button'];terminal=r['pad']+'.'+r['pin'];channel=r['channel']
            rows.append(dict(receiver=receiver,terminal=terminal,channel=int(channel) if channel else None,header=r.get('main_connector') or r['connector'],pin=r['main_pin'],net=r['net']))
    return rows

def audit(graph,rows):
    nodes={n['id']:n for n in graph['nodes']};assert len(nodes)==34
    expected={r['receiver']+':'+r['terminal']:r['header'] for r in rows if r['net']=='D__5V_DIG'}
    assert len(expected)==38
    sinks={}
    for r in rows:
        if r['channel'] is not None:sinks.setdefault(r['receiver'],set()).add(r['channel'])
    assert sorted(c for v in sinks.values() for c in v)==list(range(96))
    receivers={r['receiver']+':'+r['terminal']:r['receiver'] for r in rows if r['net']=='D__5V_DIG'}
    out={};ind={};port_counts={}
    for e in graph['edges']:
        a,b=e['from'],e['to'];port_counts[a]=port_counts.get(a,0)+1;port_counts[b]=port_counts.get(b,0)+1
        assert port_counts[a]==port_counts[b]==1,'Multiple wires in a port/contact'
        x=a.rsplit(':',1)[0] if a.rsplit(':',1)[0] in nodes else a
        y=b.rsplit(':',1)[0] if b.rsplit(':',1)[0] in nodes else b
        out.setdefault(x,[]).append(y);ind[y]=ind.get(y,0)+1
        if x in nodes:assert a.rsplit(':',1)[1] in ['OUT_A','OUT_B']
        if y in nodes:assert b.rsplit(':',1)[1]=='IN'
    assert len(graph['edges'])==72
    for n in nodes:assert ind.get(n)==1 and len(out.get(n,[]))==2
    assert set(k for k in ind if k not in nodes)==set(expected)
    for leaf in expected:assert ind[leaf]==1 and not out.get(leaf)
    memo={}
    def below(n,path=()):
        assert n not in path,'Cycle'
        if n in expected:return {n}
        assert out.get(n),'Missing branch'
        a=set()
        for child in out[n]:a |= below(child,path+(n,))
        memo[n]=a;return a
    headers={}
    for header in sorted(set(expected.values())):
        root=header+':25';assert root not in ind and len(out[root])==1
        leaves=below(root);assert leaves=={k for k,v in expected.items() if v==header},'Wrong feed ownership'
        channels=set().union(*(sinks[receivers[l]] for l in leaves))
        headers[header]=dict(unique_channels=sorted(channels),count=len(channels))
    assert set(memo)==set(nodes)|{h+':25' for h in headers}
    edges=[]
    for e in graph['edges']:
        n=e['to'].rsplit(':',1)[0];n=n if n in nodes else e['to']
        leaves=memo[n] if n in memo else {n}
        channels=set().union(*(sinks[receivers[l]] for l in leaves))
        edges.append(dict(e,downstream_unique_channels=sorted(channels),count=len(channels)))
    return headers,edges

def main():
    graph=json.loads((HERE/'anode-topology.json').read_text());rows=sources();headers,edges=audit(graph,rows)
    native=ET.parse(REF/'signal-netlist.xml');nets={}
    for net in native.findall('./nets/net'):
        for n in net.findall('node'):nets[n.get('ref'),n.get('pin')]=net.get('name')
    for r in rows:assert nets[r['header'],r['pin']]==r['net']
    values={c.get('ref'):c.findtext('value') for c in native.findall('./components/comp')}
    irefs={f'D_R300{i}':values[f'D_R300{i}'] for i in range(1,5)}
    assert set(irefs.values())=={'16.5k 1%'}
    nominal=41*1.20/16500
    for row in [*headers.values(),*edges]:
        row['nominal_current_A']=row['count']*nominal
        row['resistor_tolerance_only_high_A']=row['count']*nominal/.99
        row['nominal_drop_V_per_m_at_20C']=row['nominal_current_A']*38/304.8
    faults={}
    bad=copy.deepcopy(graph);bad['edges'][1]['from']=bad['edges'][0]['from'];faults['two_wires_one_contact']=bad
    bad=copy.deepcopy(graph);bad['edges'].pop();faults['missing_receiver_wire']=bad
    bad=copy.deepcopy(graph); roots=[e for e in bad['edges'] if e['from'].startswith('D_J')]; roots[0]['from'],roots[-1]['from']=roots[-1]['from'],roots[0]['from'];faults['swapped_feed_ownership']=bad
    bad=copy.deepcopy(graph);bad['edges'][1]['to']=bad['nodes'][0]['id']+':IN';faults['cycle_or_duplicate_input']=bad
    results={}
    for name,bad in faults.items():
        try:audit(bad,rows)
        except AssertionError:results[name]='rejected'
        else:raise AssertionError('Mutation accepted:'+name)
    assert {h:v['count'] for h,v in headers.items()}=={'D_J3002':12,'D_J3003':33,'D_J3004':35,'D_J3005':16}
    result=dict(source_sha256={str(p.relative_to(HERE)):digest(p) for p in [Path(__file__),HERE/'build.py',HERE/'anode-topology.json',*sorted(REF.rglob('*'))] if p.is_file()},headers=headers,edges=edges,IREF=irefs,nominal_channel_current_A=nominal,nominal_total_A=96*nominal,mutation_checks=results,branch_count=34,wire_count=72,receiver_terminal_count=38,
        current_scope='Typical constant-current equation at41gain/1.20V reference and16.5kohm. Resistor-only high is NOT a guaranteed driver-current bound. Simultaneous PWM peaks considered by assuming every channel on. Paired display anodes share current: each edge allocates its downstream unique channels, so sibling edge bounds may not be summed. No contact/splice/ambient/bundle ampacity or fault qualification asserted.',
        remaining=['Exact driver-current error across real operating voltage/temperature at~3mA','Wire and crimp/contact temperature/current acceptance under final bundle conditions','Native layout, insulated splice receiving envelope, routes/lengths and support','Whole unit digital5V capacity/thermal allocation'],fabrication_released=False)
    (HERE/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Verified34junctions72wires38endpoints96channels; 4mutations rejected; nominal total',96*nominal)
if __name__=='__main__':main()
