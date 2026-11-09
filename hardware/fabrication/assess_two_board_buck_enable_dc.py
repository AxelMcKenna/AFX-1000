"""Source-bound DC screen of both shared POWER_READY enable branches.

The AUX voltage band and 25 uA EN-current allocation are engineering scenarios,
not established full-temperature guaranteed device limits. No release gate is
closed by this calculation.
"""
import itertools,json
from pathlib import Path
import numpy as np
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha,read_netlist
OUT=STAGING/'two-board-power-buck-enable-native-01'

def solve(res,aux,i_d,i_a,i_ready,sink=None,aux_floating=False):
    pull,sd,gd,sa,ga=res;gp=0 if aux_floating else 1/pull
    matrix=np.array([[gp+1/sd+1/sa+(0 if sink is None else 1/sink),-1/sd,-1/sa],[-1/sd,1/sd+1/gd,0],[-1/sa,0,1/sa+1/ga]])
    rhs=np.array([gp*aux+i_ready,i_d,i_a]);v=np.linalg.solve(matrix,rhs)
    assert max(abs(matrix@v-rhs))<1e-12
    return v.tolist()

def run():
    netlist=OUT/'netlist.xml';parts,pins=read_netlist(netlist)
    refs=['P_R110','P_R204','P_R205','P_R224','P_R225'];nom=[1000,10000,22000,10000,22000]
    assert [parts[r].findtext('value') for r in refs]==['1k 1%','10k 1%','22k 1%','10k 1%','22k 1%']
    ready='P_power_supply/POWER_READY';en_d='P_power_supply/P03_D_ENABLE';en_a='P_power_supply/P03_A_ENABLE'
    assert {p for p,n in pins.items() if n==ready}=={('P_J103','2'),('P_J22','3'),('P_R110','2'),('P_R204','1'),('P_R224','1'),('P_U101','16'),('P_U26','6')}
    assert {p for p,n in pins.items() if n==en_a}=={('P_R224','2'),('P_R225','1'),('P_U23','7')}
    assert {p for p,n in pins.items() if n==en_d}=={('P_R204','2'),('P_R205','1'),('P_U20','7')}
    assert pins['P_R110','1']=='PWR_V2V5_AUX' and all(pins[r,'2']=='PWR_AGND' for r in ['P_R205','P_R225'])
    data={k:[] for k in ['ready_released','ready_asserted','aux_floating_ready_released']}
    cases=0
    for tol in itertools.product([.99,1.01],repeat=5):
        res=[a*b for a,b in zip(nom,tol)]
        for aux,di,ai,leak in itertools.product([2.3,2.7],[0,25e-6],[0,25e-6],[-10.15e-6,10.15e-6]):
            data['ready_released'].append(solve(res,aux,di,ai,leak))
            for ron in [36,130]:data['ready_asserted'].append(solve(res,aux,di,ai,leak,sink=ron))
            data['aux_floating_ready_released'].append(solve(res,aux,di,ai,leak,aux_floating=True))
            cases+=1
    ranges={k:{name:[min(r[i] for r in rows),max(r[i] for r in rows)] for i,name in enumerate(['POWER_READY_V','D_ENABLE_V','A_ENABLE_V'])} for k,rows in data.items()}
    assert all(ranges['ready_released'][n][0]>1.25 for n in ['D_ENABLE_V','A_ENABLE_V'])
    assert all(ranges[k][n][1]<1.05 for k in ['ready_asserted','aux_floating_ready_released'] for n in ['D_ENABLE_V','A_ENABLE_V'])
    # Independent symmetric zero-source closed form cross-check.
    v=solve(nom,2.5,0,0,0);expected=2.5*16000/17000
    assert abs(v[0]-expected)<1e-12 and abs(v[1]-expected*22/32)<1e-12 and abs(v[1]-v[2])<1e-12
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),netlist,OUT/'buck-enable-audit.json']},
        references={'TPS543620_SLUSDR5C_sections_6_5_and_7_3_2':'https://www.ti.com/lit/ds/symlink/tps543620.pdf',
                    'TPS2663_SLVSE94G_section_6_5':'https://www.ti.com/lit/ds/symlink/tps2663.pdf',
                    'SN74LVC1G97_SCES416N_section_6_5':'https://www.ti.com/lit/ds/symlink/sn74lvc1g97.pdf'},
        cases=cases,total_linear_solutions=sum(map(len,data.values())),nominal_no_EN_source_V=v,
        scenario_parameters=dict(AUX_band_V=[2.3,2.7],resistor_initial_tolerance=.01,EN_source_allocation_A=[0,25e-6],ready_node_current_allocation_A=[-10.15e-6,10.15e-6],PGOOD_sink_ohm=[36,130]),
        voltage_ranges=ranges,scenario_enable_rising_screen_V=1.25,scenario_enable_falling_screen_V=1.05,
        all_selected_DC_scenarios_pass_enable_threshold_screen=True,
        assumptions=['AUX band is a proposed screen, not verified loaded rail tolerance.','25 uA is an engineering allocation, not a TPS543620 guaranteed maximum. Published 11.6 uA sourcing value above threshold is typical.','Ready-node 10.15 uA allocation combines an assumed 10 uA logic allowance with 0.15 uA eFuse leakage. Its continuous input-voltage envelope remains to be verified.','J103/J22 add no fitted external load or drive in these scenarios; final interface retirement/receiving is pending.','Only initial resistor tolerances are included; exact MPN drift and temperature are pending.','Floating-AUX model disconnects its pull-up source and applies the allocated currents. Negative linear voltages from sink-current corners are not clamp-device predictions.'],
        outstanding=['Guaranteed full-range EN sourcing/current envelope','Loaded AUX voltage/current and ground offsets','Logic thresholds over actual supply range','Partial-power clamps and startup/shutdown timing','Final interfaces and fitted external loads'],
        full_enable_electrical_qualification=False,fabrication_released=False)
    with (OUT/'enable-dc-screen.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(solutions=result['total_linear_solutions'],nominal=v,ranges=ranges,qualified=False),indent=2))

if __name__=='__main__':run()
