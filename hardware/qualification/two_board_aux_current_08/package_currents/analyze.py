"""Source-bound AUX package census and regulator margin; never a full load bound."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def calculate(facts=None):
    facts = facts or json.loads((HERE/'facts.json').read_text())
    tree = ET.parse(PARENT/'sources/TBP71-netlist.xml')
    components = {c.attrib['ref']:c.findtext('value') for c in tree.findall('./components/comp')}
    inventory = json.loads((PARENT/'sources/monitor-loads.json').read_text())['IC_supply_inventory']
    expected = {r['ref']:r['part'] for r in inventory}
    actual = {}; rows = []
    for f in facts['families']:
        if 'pdf' in f:
            assert sha(HERE/f['pdf']) == f['sha256']
            assert sha(HERE/f['text']) == f['text_sha256']
        else:
            assert f['web_table_review']['max_uA']==f['table_max_uA_per_unit']
        assert f['application_current_bound'] is False
        for ref in f['references']:
            assert ref not in actual
            actual[ref] = f['part']
            assert components[ref] == f['part']
        multiplier = 4 if f['part'].startswith('TLV1824') else 2 if f['part'] in ['TLV1822DR','OPA2333AID'] else 1
        assert f['units_per_package'] == multiplier
        rows.append(dict(part=f['part'],references=f['references'],table_max_per_package_uA=f['table_max_uA_per_unit']*multiplier,table_max_family_uA=f['table_max_uA_per_unit']*multiplier*len(f['references']),condition=f['table_condition'],application_bound=False))
    assert actual == expected and len(actual)==81 and len(rows)==29
    translators={r['ref']:r['AUX_supply_pin'] for r in inventory if r['part']=='SN74LVC2T45DCUR'}
    assert translators == {'N_U16':'1','N_U27':'8'}
    assert components['P_R108']=='11.7k 0.1% 25ppm'
    assert components['P_R130']=='49.9 0.01% 5ppm'
    assert components['P_R109']=='10k 0.1% 10ppm'
    pins={}
    for net in tree.findall('./nets/net'):
        for node in net.findall('node'):pins[(node.attrib['ref'],node.attrib['pin'])]=net.attrib['name']
    assert pins['P_R108','1']==pins['P_U102','1']=='PWR_V2V5_AUX'
    assert pins['P_R108','2']==pins['P_R130','1']
    assert pins['P_R130','2']==pins['P_R109','1']==pins['P_U102','2']
    assert pins['P_R109','2']=='PWR_AGND'
    regulator=json.loads((HERE/'regulator-facts.json').read_text())
    for name,h in regulator['source_sha256'].items():assert sha(HERE/name)==h
    nom=1.193*(1+(11700+49.9)/10000)
    # Allocation, not a purchased-component total error guarantee: stated tolerance
    # plus linear TCR over maximum 100C deviation from25C (-40..125C).
    rtoplo=11700*(1-.001-25e-6*100)+49.9*(1-.0001-5e-6*100)
    rtophi=11700*(1+.001+25e-6*100)+49.9*(1+.0001+5e-6*100)
    rblo=10000*(1-.001-10e-6*100); rbhi=10000*(1+.001+10e-6*100)
    lo=1.193*.98*(1+rtoplo/rbhi)-.1e-6*rtophi
    hi=1.193*1.02*(1+rtophi/rblo)+.1e-6*rtophi
    demand=sum(r['table_max_family_uA'] for r in rows)/1e6
    ledger=json.loads((PARENT/'ledger.json').read_text())
    # Recompute source-port terms, not rounded README total.
    ports=ledger['owned_source_ports']
    portsum=sum(r['conditional_max_A'] for r in ports)
    assert [components[r] for r in ['E_R137','E_R138','E_R139']]==['11.1k 0.1%','39.2 0.1%','10k 0.1%']
    assert pins['E_R137','1']=='PWR_V2V5_AUX' and pins['E_R139','2']=='PWR_AGND'
    assert pins['E_R137','2']==pins['E_R138','1']
    assert pins['E_R138','2']==pins['E_R139','1']==pins['E_U19','1']
    st=11100+39.2; sb=10000
    sup_lo=1.15*.99*(1+st*.999/(sb*1.001))-100e-9*st*1.001
    sup_rise_lo=1.157*.99*(1+st*.999/(sb*1.001))-100e-9*st*1.001
    return dict(schema=1,packages=81,families=29,rows=rows,translator_aux_ports=translators,
        table_max_sum_A=demand,other_77_package_table_sum_A=demand-.038,
        conditional_resistor_source_port_sum_A=portsum,
        mixed_condition_sensitivity_A=demand+portsum,
        common_temperature_screen_C=[-40,85],
        regulator=dict(nominal_output_V=nom,tolerance_plus_TCR_screen_C=[-40,125],conditional_output_V=[lo,hi],
            tightest_fixed_minimum_V=2.4,affected_packages=sorted(ref for f in facts['families'] if f['part'].startswith('TLV182') for ref in f['references']),
            conditional_distribution_and_transient_drop_budget_V=lo-2.4,
            accuracy_input_headroom_requirement_V=nom+.5,
            pg_nominal_rising_threshold_range_V=[nom*.85,nom*.95],
            pg_alone_proves_comparator_valid=False),
        aux_supervisor=dict(ref='E_U19',nominal_falling_threshold_V=1.15*(1+st/sb),
            nominal_rising_threshold_V=1.157*(1+st/sb),
            tolerance_only_with_100nA_signed_sensitivity_falling_min_V=sup_lo,
            tolerance_only_with_100nA_signed_sensitivity_rising_min_V=sup_rise_lo,
            falling_margin_to_2V4_V=sup_lo-2.4,
            conditions='0.1% initial resistor tolerance only;1% threshold;100nA ISENSE table at5V used as signed sensitivity, not accepted leakage bound; noTCR/aging/drop/delay allocation',
            proof_of_safe_enable_or_shutdown=False),
        unresolved=['Table maxima at different supplies/input states do not make an application bound',
            'Si8751 actual gate load and OFF maximum; input clamp and transition currents',
            'Logic nonrail inputs, switch frequencies, Cpd and capacitive output loads',
            'Supplier total resistor errors beyond stated tolerance plus TCR allocation',
            'Actual VIN/load/transient/startup ramp, distribution drop and installed thermal resistance'],
        full_current_bound_A=None,startup_current_bound_A=None,thermal_feasible=None,fabrication_released=False,
        source_sha256={str(p.relative_to(PARENT)):sha(p) for p in [HERE/'facts.json',HERE/'regulator-facts.json',PARENT/'sources/TBP71-netlist.xml',PARENT/'sources/monitor-loads.json',PARENT/'ledger.json',Path(__file__)]})

if __name__=='__main__':
    result=calculate()
    (HERE/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['rows','source_sha256']},indent=2))
