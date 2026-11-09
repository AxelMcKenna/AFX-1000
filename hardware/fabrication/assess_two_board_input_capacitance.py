"""Record actual capacitor selections and explicit derating budgets, not guarantees."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha, read_netlist


def run():
    source = STAGING / 'two-board-power-u20-output-native-02/netlist.xml'
    parts, pins = read_netlist(source)
    out = STAGING / 'two-board-input-capacitor-review-01'
    groups = [
        ('local-input', ['P_C202','P_C203','P_C222','P_C223'], 'C2012X7R1H225K125AC', 2.2, .1, .15, 50),
        ('HF-input', ['P_C210','P_C211','P_C230','P_C231'], 'C1005X7R1H104K050BB', .1, .1, .15, 50),
        ('bulk-input', ['P_C204','P_C205','P_C224','P_C225'], 'C3225X7R1H226M250AC', 22, .2, .15, 50),
        ('output', [*[f'P_C{i}' for i in range(206,210)], *[f'P_C{i}' for i in range(226,230)]], 'C3225X7S1E476M250AC', 47, .2, .22, 25),
    ]
    rows = []
    for role, refs, mpn, nominal, tolerance, temperature, rating in groups:
        for ref in refs:
            value = parts[ref].findtext('value')
            assert mpn in value and f'{rating}V' in value
            assert ('X7S' if temperature == .22 else 'X7R') in value
            rows.append(dict(ref=ref, role=role, native_value=value,
                             footprint=parts[ref].findtext('footprint'),
                             pin_nets={pin: net for (r,pin),net in pins.items() if r == ref},
                             nominal_uF=nominal, initial_tolerance_fraction=tolerance,
                             dielectric_temperature_fraction=temperature,
                             lower_initial_and_temperature_budget_uF=nominal*(1-tolerance)*(1-temperature),
                             upper_initial_and_temperature_budget_uF=nominal*(1+tolerance)*(1+temperature)))
    local = 2.2*.9*.85
    hf = .1*.9*.85
    candidate = 4.7*.9*.85
    assert local+hf < 2 and candidate > 2
    paths = [Path(__file__), source, REPO/'hardware/electronics/power_distribution/p03/component-selections.json',
             REPO/'hardware/electronics/power_distribution/p03/components.json',
             out/'sources/download-record.json']
    result = dict(source_sha256={str(p.relative_to(REPO)):sha(p) for p in paths},
        native_capacitors=rows,
        regulator_source='https://www.ti.com/lit/ds/symlink/tps543620.pdf',
        regulator_sections=['9', '10.1'], required_effective_total_local_input_uF=4,
        recommended_effective_per_VIN_PGND_side_uF=2,
        old_local_plus_HF_initial_temperature_budget_uF=local+hf,
        old_local_plus_HF_budget_meets_2uF_without_bulk=False,
        old_source_1uF_per_local_capacitor_allocation_meets_2uF_per_side=False,
        budget_scope='Multiplicative engineering allocation for initial tolerance and dielectric envelope only; excludes DC bias, aging, AC amplitude, assembly and layout impedance. It is not a guaranteed operating capacitance.',
        candidate=dict(mpn='C2012X7R1H475K125AC', selected=False,
            source='https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C2012X7R1H475K125AC',
            manufacturer_document_mirror='https://www.farnell.com/datasheets/4464535.pdf',
            nominal_uF=4.7, rated_v=50, initial_tolerance_fraction=.1, temperature_fraction=.15,
            body_maximum_LWH_mm=[2.25,1.5,1.5], lower_initial_temperature_budget_uF=candidate,
            minimum_remaining_bias_aging_factor_for_2uF_without_HF_credit=2/candidate,
            numeric_bias_curve_or_model_retrieved=False,
            current_land_height_and_context_reconciled=False,
            guaranteed_operating_minimum_established=False),
        output_bank_per_regulator=dict(nominal_uF=188, dielectric='X7S', rated_v=25,
            initial_tolerance_fraction=.2, temperature_fraction=.22,
            lower_initial_temperature_budget_uF=4*47*.8*.78,
            upper_initial_temperature_budget_uF=4*47*1.2*1.22,
            old_80uF_effective_bank_requirement_verified=False),
        further_design_work=[
            'Evaluate each complete local input network including its 22uF50V bulk capacitor and actual low-impedance connections',
            'Obtain usable manufacturer bias/temperature data and choose documented design margins or a lower-bias alternative',
            'Reconcile replacement body/height/land dimensions before any substitution',
            'Verify input ripple current, source inrush and the effective output-bank/stability range',
            'Separate pre-fabrication design evidence from later first-article measurement acceptance'],
        capacitor_substitution_made=False, electrical_design_accepted=False, fabrication_released=False)
    with (out/'review.json').open('x') as f:
        json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(local_plus_HF_budget_uF=local+hf,
        candidate_minimum_remaining_factor=2/candidate, substitution_made=False)))


if __name__ == '__main__':
    run()
