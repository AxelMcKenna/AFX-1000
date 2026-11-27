"""Conditional design window; allocations are requirements, not measured bounds."""
import json
from pathlib import Path
from .analyze import calculate, sha, HERE

def window(total_resistor_error=.003,sense_current_allocation_A=150e-9,
           shutdown_drop_slew_V=.020,startup_allowance_V=.015):
    e=total_resistor_error; ib=sense_current_allocation_A; rb=10000
    assert 0<=e<1 and ib>=0 and shutdown_drop_slew_V>=0 and startup_allowance_V>=0
    reglow=calculate()['regulator']['conditional_output_V'][0]
    required_fall=2.4+shutdown_drop_slew_V
    allowed_rise=reglow-startup_allowance_V
    fall_slope=1.15*.99*(1-e)/(rb*(1+e))-ib*(1+e)
    rise_slope=1.157*1.01*(1+e)/(rb*(1-e))+ib*(1+e)
    assert fall_slope>0
    low=(required_fall-1.15*.99)/fall_slope
    high=(allowed_rise-1.157*1.01)/rise_slope
    top=11400
    fall=1.15*.99+top*fall_slope
    rise=1.157*1.01+top*rise_slope
    return dict(assumptions=dict(total_resistor_error= e,sense_current_allocation_A=ib,
        shutdown_drop_slew_V=shutdown_drop_slew_V,startup_allowance_V=startup_allowance_V),
        allowable_top_nominal_ohm=[low,high],nonempty_window=low<=high,
        proposal=dict(E_R137='11.4k',E_R138='0ohm link',E_R139='10k',
            minimum_falling_V=fall,maximum_rising_V=rise,
            remaining_shutdown_margin_V=fall-required_fall,
            remaining_startup_margin_V=allowed_rise-rise,
            meets_allocations=low<=top<=high),
        applied_to_board=False,qualified=False,
        source_sha256={str(p.relative_to(HERE)):sha(p) for p in [Path(__file__),HERE/'analyze.py',HERE/'facts.json',HERE/'regulator-facts.json']},
        acceptance_requirements=[
            'Supplier-selected resistor and link total errors including tolerance/TCR/aging/assembly remain within0.3%; link resistance included',
            'TPS389001 SENSE current bound at actual1.15V is within allocated150nA, verified independently of5V table point',
            'Regulator conditions and component error allocation used for2.534165V minimum are met',
            'Monitor-to-comparator local supply/ground difference plus slew times entire shutdown delay is within20mV',
            'Regulator-to-monitor drop plus startup droop and required enable headroom is within15mV',
            'Trace all downstream gating and supervisor assertion/deassertion delays; this static window alone does not prove safe sequencing',
            'Complete allAUX DC,transition,fault current and thermal bounds before implementation acceptance'])

if __name__=='__main__':
    Path(__file__).with_name('threshold-window.json').write_text(json.dumps(window(),indent=2)+'\n')
