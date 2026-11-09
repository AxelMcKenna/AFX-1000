"""Capture TBP10 and the retained signal board without claiming fab readiness."""
import json
from pathlib import Path
from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, sha


def run():
    power=STAGING/'two-board-power-native-10'
    signal=STAGING/'two-board-signal-routed-native-03'
    reports=[power/'review.json',power/'circuit-audit.json',power/'module-cutoff-audit.json',
        power/'construction.json',power/'plots-module/native-plot.json',power/'plots-module/visual-review.json',
        signal/'review.json',signal/'copper-retention-v2.json']
    bindings=0
    for report in reports:
        data=json.loads(report.read_text())
        for field in ['source_sha256','artifact_sha256']:
            for name,digest in data.get(field,{}).items():
                path=Path(name)
                if not path.is_absolute():
                    path=(REPO if name.startswith(('hardware/','tests/')) else report.parent)/path
                assert path.is_file() and sha(path)==digest,(str(report),name)
                bindings+=1
    native=json.loads((power/'review.json').read_text())
    independent=json.loads((power/'module-cutoff-audit.json').read_text())
    assert native['opens']==2709 and native['geometry_findings']==native['schematic_parity_findings']==0
    assert independent['timer_latch_topology_and_RTN_separation_verified']
    erc=json.loads((power/'erc.json').read_text())
    findings=[v for s in erc['sheets'] for v in s.get('violations',[])]
    assert len(findings)==2 and all(v['severity']=='warning' for v in findings)
    old=json.loads((STAGING/'two-board-fabrication-status-05/status.json').read_text())
    old.update(
        source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__),*reports,
            power/'README.md',power/'MODULE-FIRST-ARTICLE.md',
            STAGING/'two-board-power-native-09/erc.json',
            REPO/'hardware/fabrication/integrate_two_board_power_v9.py',
            REPO/'hardware/fabrication/integrate_two_board_power_v10.py']},
        verified_direct_source_and_artifact_bindings=bindings,
        power_project=str((power/'power_protection.kicad_pro').relative_to(REPO)),
        power_opens=native['opens'],power_schematic_pin_entries=3428,power_mapped_pad_instances=3489,
        module_branch_requires_cutoff_revision=False,
        module_cutoff_implemented='TPS26601RHFR, MODE open; timer-operated latch-off',
        module_cutoff_maximum_duration_guaranteed=False,
        module_control_RTN_separate_from_force_GND=True,
        module_first_article_plan=str((power/'MODULE-FIRST-ARTICLE.md').relative_to(REPO)),
        module_first_article_tests_executed=False,
        next_required_design_work=[
            'Resolve module normal/startup current and effective capacitance; 9.5mA margin is only an engineering screen',
            'Finalize individual module fault containment and its voltage-drop/time-current coordination',
            'Complete passive MPN receiving, critical module/source placement, RTN thermal vias and return-star routing',
            'AUX_VALID high-temperature fan-out; full-range thresholds, noise/default/partial-power and loaded timing',
            'Loaded reference, sense, clamp and shared AUX current/return review',
            'Minimum recognized UV pulse, loaded cutoff and actual GLOBAL-OFF interval; deep AUX loss resets E28 latch'],
        fabrication_released=False,goal_complete=False)
    old.pop('next_module_cutoff_candidate',None)
    # Distinguish a first-prototype release plan from physical qualification of
    # that future prototype; do not require an unbuilt board to be measured.
    old['other_open_release_requirements']=[
        'ESS approved package/land/stencil and interface inputs',
        'Final cross-board power/control interface and all routing',
        'Critical placement, current/return/timing/noise/thermal design verification',
        'Accepted manufacturing stack/BOM/process and complete fabrication outputs',
        'Revised supports, airflow/cooling, real mates/harnesses and full installed fit',
        'Complete whole-unit prototype inspection and bring-up plan; module procedure is drafted']
    out=STAGING/'two-board-fabrication-status-06';assert not out.exists();out.mkdir()
    (out/'status.json').write_text(json.dumps(old,indent=2)+'\n')
    print(json.dumps(dict(verified_bindings=bindings,power_opens=native['opens'],fabrication_released=False)))


if __name__=='__main__':run()
