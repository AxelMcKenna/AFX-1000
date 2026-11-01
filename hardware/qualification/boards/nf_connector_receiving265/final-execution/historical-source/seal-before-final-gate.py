"""Create/check the NC265 scoped interface seal; never alter parent packets."""

import argparse
import hashlib
import json
from pathlib import Path

from hardware.qualification.boards.nf_connector_receiving265 import audit

ROOT = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def contract_errors(d):
    errors = []
    for flag in [
        "physical_qualified",
        "electrical_qualified",
        "fabrication_released",
        "full265_PCB_completed",
        "fullunit_harness_fit_qualified",
        "parent_packets_edited",
    ]:
        if d.get(flag) is not False:
            errors.append("Unsupported promotion:" + flag)
    if (
        d.get("source_port_pads") != 40
        or d.get("actual_local_model_strict_cases") != 18
        or d.get("retained_raw_strict_contact_failures") != 4
        or d.get("new_contact_guard_cases") != 9
    ):
        errors.append("Wrong scoped evidence coverage")
    return errors


def run(create=False):
    target = ROOT / "handoff.json"
    if create and target.exists():
        raise RuntimeError("Refusing to replace a frozen interface packet")
    errors = audit.checks()
    if target.exists():
        d = json.loads(target.read_text())
        errors += contract_errors(d)
        for name, expected in d["files_sha256"].items():
            p = ROOT / name
            if not p.is_file() or sha(p) != expected:
                errors.append("Changed sealed NC265 file:" + name)
    elif create:
        if errors:
            raise ValueError(errors)
        files = sorted(
            p
            for p in ROOT.rglob("*")
            if p.is_file()
            and "__pycache__" not in p.parts
            and p.name != ".DS_Store"
            and not p.name.endswith(".pyc")
        )
        d = dict(
            revision="NC265-interface-and-strain-prototype-handoff",
            files_sha256={str(p.relative_to(ROOT)): sha(p) for p in files},
            exact_NF265_source_seal="f53cdb06d5f8c717ddc7b0b077bedf5ff1b855561d742b6e0197465467738cad",
            adopted_interface_proposal="ports-v2.json",
            ports_v2_sha256=sha(ROOT / "ports-v2.json"),
            source_port_pads=40,
            actual_local_model_strict_cases=18,
            strict_local_passes_before_correlated_contact_checks=14,
            retained_raw_strict_contact_failures=4,
            new_contact_guard_cases=9,
            finite1000nm_intrusion_controls=5,
            actual_new_native_KO_copper_rejection_controls=2,
            actual_source_component_count=265,
            final_connector_only_fixture="prototype-v3/NC265_ports_strain_v3.kicad_pcb",
            final_fixture_electrical_FPs=6,
            final_fixture_mechanical_FPs=2,
            fixture_Cu_layers=4,
            fullboard_future_layers_not_inherited=6,
            actual_native_fixture_DRC_count=0,
            actual_native_fixture_opens=0,
            continuous29wire_pair_proofs=406,
            source_entry_actual_mate_and_remote_destinations_qualified=False,
            complete_other259parts_and_wholeunit_checks_required=True,
            physical_qualified=False,
            electrical_qualified=False,
            fabrication_released=False,
            full265_PCB_completed=False,
            fullunit_harness_fit_qualified=False,
            parent_packets_edited=False,
        )
        target.write_text(json.dumps(d, indent=2) + "\n")
    else:
        errors.append("No NC265 handoff")
    print(json.dumps(dict(errors=errors, handoff_sha256=sha(target) if target.exists() else None)))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true")
    run(parser.parse_args().create)
