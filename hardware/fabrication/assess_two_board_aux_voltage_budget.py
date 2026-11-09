"""Derive steady-state AUX source limits from the actual feedback network."""
import itertools
import json
from pathlib import Path
import numpy as np
from hardware.fabrication.assess_two_board_aux_load import circuit,numeric,AUX,GND
from hardware.fabrication.integrate_two_board_signal import REPO,STAGING,sha

SOURCE=STAGING/'two-board-power-startup-remaining-native-03/netlist.xml'
OUT=STAGING/'two-board-aux-monitor-loads-01/source-voltage-screen.json'


def run():
    assert not OUT.exists()
    parts,nets,pins=circuit(SOURCE)
    names=['P_R108','P_R130','P_R109']
    values=[numeric(parts[r].findtext('value')) for r in names]
    assert values==[11700.,49.9,10000.]
    fb=pins['P_U102']['2'];mid=pins['P_R108']['2']
    assert set(pins['P_R108'].values())=={AUX,mid}
    assert set(pins['P_R130'].values())=={mid,fb}
    assert set(pins['P_R109'].values())=={fb,GND}
    assert {x['ref'] for x in nets[mid]}=={'P_R108','P_R130'}
    assert {x['ref'] for x in nets[fb]}=={'P_R130','P_R109','P_U102'}
    scenarios=[];maximum_error=0.;count=0
    for name,tolerances in [('initial_labels_only',[.001,.0001,.001]),
                            ('proposed_complete_1percent',[.01,.01,.01]),
                            ('blanket_3percent_screen',[.03,.03,.03])]:
        cases=[]
        for factors,accuracy,ifb in itertools.product(
                itertools.product(*[(1-t,1+t) for t in tolerances]),[.98,1.02],[-1e-7,1e-7]):
            r1,r2,rb=[r*f for r,f in zip(values,factors)];vref=1.193*accuracy
            # Positive IFB flows out of the IC into the FB node (datasheet note).
            vout=vref*(1+(r1+r2)/rb)-ifb*(r1+r2)
            # Independent two-node KCL: unknown midpoint and output voltages.
            m=np.array([[1/r1+1/r2,-1/r1],[-1/r2,0.]])
            rhs=np.array([vref/r2,ifb-vref*(1/rb+1/r2)])
            vm,vo=np.linalg.solve(m,rhs)
            maximum_error=max(maximum_error,abs(vo-vout));assert abs(vo-vout)<1e-11
            assert abs((vo-vm)/r1-(vm-vref)/r2)<1e-12
            cases.append(dict(resistor_factors=list(factors),accuracy_factor=accuracy,
                IFB_out_of_IC_A=ifb,FB_V=vref,midpoint_V=float(vm),output_V=vout))
            count+=1
        lo=min(c['output_V'] for c in cases);hi=max(c['output_V'] for c in cases)
        scenarios.append(dict(name=name,complete_resistor_bounds=tolerances,cases=cases,
            source_voltage_range_V=[lo,hi],drop_budget_to_LTC2910_2p3V_V=lo-2.3,
            upper_margin_to_2p7V_V=2.7-hi,within_2p3_to_2p7_screen=2.3<=lo and hi<=2.7,
            total_loop_resistance_screen_at_90mA_ohm=(lo-2.3)/.09))
    assert scenarios[1]['within_2p3_to_2p7_screen']
    assert not scenarios[2]['within_2p3_to_2p7_screen']
    sources=[Path(__file__),SOURCE,REPO/'hardware/fabrication/assess_two_board_aux_load.py',
        REPO/'hardware/qualification/boards/aux_current_partition/sources/primary/TPS7A16.pdf']
    result=dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in sources},
        selected_revision='TBP50',resistors=[dict(ref=r,value=parts[r].findtext('value'),pins=pins[r]) for r in names],
        nominal_output_V=1.193*(1+sum(values[:2])/values[2]),scenarios=scenarios,
        independent_KCL_cases=count,maximum_independent_voltage_difference_V=maximum_error,
        accuracy_scope='TPS7A16 overall +/-2% under stated input/headroom, temperature and10uA..100mA load conditions; do not add typical line/load regulation a second time.',
        output_formula='VOUT = VFB*(1+(R108+R130)/R109) - IFB_out*(R108+R130)',
        IFB_sign_reversed_counterexample_rejected=True,
        complete_1percent_bounds_accepted=False,exact_MPN_drift_and_aging_verified=False,
        local_supply_return_drop_measured_or_extracted=False,
        startup_transient_and_thermal_qualified=False,fabrication_released=False)
    OUT.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(nominal=result['nominal_output_V'],cases=count,
        maximum_error_V=maximum_error,scenarios=[{k:v for k,v in s.items() if k!='cases'} for s in scenarios])))


if __name__=='__main__':run()
