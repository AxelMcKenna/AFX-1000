"""Q02 requirements for the three PCB candidates pictured in the README."""

import hashlib
import json
from pathlib import Path

from ..spec import REPO, digest

HERE = Path(__file__).resolve().parent
FRESH_NATIVE = {
    "adc": "hardware/electronics/adc_driver/qualification/generated/native-original/verification.json",
    "psu": "hardware/electronics/power_supply/qualification/generated/native-routing/verification.json",
}
NATIVE_ANCHORS = {"adc": "", "psu": "hardware/electronics/power_supply/routing", "disconnect": ""}
BOARDS = {
    "adc": {
        "variant": "E12-characterization",
        "pcb": "hardware/electronics/adc_driver/pcb/adc_driver.kicad_pcb",
        "schematic": "hardware/electronics/adc_driver/adc_driver.kicad_sch",
        "native": "hardware/electronics/adc_driver/pcb/generated/verification.json",
        "holds": [
            "Full AGND planes cover FDA sensitive nodes; manufacturer-recommended openings need a reviewed revision.",
            "The J2 force/sense stars do not sense the converter pins through the shared harness.",
            "Stackup/parasitics, effective capacitor and contamination/servo-leakage limits remain unqualified.",
            "Actual noise, distortion, common-mode settling and stability remain unmeasured.",
            "Both bias monitors are absent; the proposed -0.16 V upper window also fails the existing output-headroom reserve.",
        ],
    },
    "psu": {
        "variant": "E14-routed-legacy",
        "pcb": "hardware/electronics/power_supply/routing/power_supply.kicad_pcb",
        "schematic": "hardware/electronics/power_supply/power_supply.kicad_sch",
        "native": "hardware/electronics/power_supply/routing/generated/verification.json",
        "holds": [
            "Digital 5 V full-temperature source bounds exceed the project window; the 0–85 C junction bound is unproved.",
            "The protected digital load budget fails even before realistic complete harness losses.",
            "Actual copper stackup, thermal paths, loop stability, startup and partial-power behavior remain unqualified.",
            "P02 is a different unimplemented source; its DC model cannot qualify this existing PCB.",
        ],
    },
    "disconnect": {
        "variant": "E26-pilot",
        "pcb": "hardware/electronics/rail_disconnect/revision26/rail_disconnect.kicad_pcb",
        "schematic": "hardware/electronics/rail_disconnect/rail_disconnect.kicad_sch",
        "native": "hardware/electronics/rail_disconnect/revision26/generated/pilot-findings.json",
        "holds": [
            "The pictured E26 pilot has actual open power paths and native DRC findings.",
            "Actual positive/return copper resistance, gate behavior, late-closure current and MOSFET SOA remain unqualified.",
            "The board is an overvoltage disconnect, not a standalone undervoltage detector or fault latch.",
            "Opening MOSFETs does not discharge protected bulk; residual energy must be measured.",
            "All fourteen generic MOSFET land patterns still need full manufacturer terminal/mask/paste and fabrication review.",
        ],
    },
}


def limit(unit, minimum=None, maximum=None, *, expected=None, source=None):
    return dict(
        unit=unit,
        minimum=minimum,
        maximum=maximum,
        expected=expected,
        status="defined_project_target" if source else "acceptance_limit_missing",
        source=source,
    )


def native_source_check(repo, native, anchor, pcb):
    hashes = native.get("source_sha256", {})
    changed, files, bound = [], [], False
    for name, expected in hashes.items():
        path = (repo / anchor / name).resolve()
        if not path.is_relative_to(repo.resolve()) or not path.is_file():
            changed.append(name)
            continue
        files.append(str(path.relative_to(repo.resolve())))
        actual = digest(path)
        if actual != expected:
            changed.append(name)
        if path == (repo / pcb).resolve() and actual == expected:
            bound = True
    return dict(
        source_hashes_checked=len(hashes),
        changed_sources=changed,
        pcb_source_bound=bound,
        current=bool(hashes) and bound and not changed,
    ), files


def build_plan(repo=REPO):
    repo = Path(repo)
    source = "hardware/electronics/power_supply/integration.json"
    power = json.loads((repo / source).read_text())
    boards, files = {}, {source}
    for name, spec in BOARDS.items():
        native_path = FRESH_NATIVE.get(name, spec["native"])
        if not (repo / native_path).exists():
            native_path = spec["native"]
        native = json.loads((repo / native_path).read_text())
        freshness, dependencies = native_source_check(repo, native, NATIVE_ANCHORS[name], spec["pcb"])
        files.update(dependencies)
        native_counts = dict(
            drc=native.get("native_drc_violations"),
            parity=native.get("schematic_parity_issues"),
            opens=native.get("native_open_connections", native.get("unconnected_items")),
        )
        assert all(type(v) is int and v >= 0 for v in native_counts.values()), (name, native_counts)
        closed = freshness["current"] and all(v == 0 for v in native_counts.values())
        boards[name] = dict(
            **{**spec, "native": native_path},
            pcb_sha256=digest(repo / spec["pcb"]),
            native_counts=native_counts,
            native_source_freshness=freshness,
            native_connectivity_closed=closed,
            physical_measurements_performed=0,
            fabrication_released=False,
        )
        files.update([spec["pcb"], spec["schematic"], native_path])
    cases = []

    def add(identifier, board, metrics, conditions, instruments, method, *, powered=True):
        for metric, criterion in metrics.items():
            unit = criterion["unit"]
            if unit == "count":
                roles = ["dmm"] if metric == "unintended_short_count" else ["inspection"]
            elif identifier.startswith(("source_", "protected_star_")) or identifier in {
                "adc_power",
                "adc_nbias",
            }:
                roles = ["dmm"]
            elif identifier == "adc_leakage" and metric in {"reference_drift", "board_leakage"}:
                roles = ["electrometer"]
            elif unit == "degC":
                roles = ["temperature"]
            elif unit == "declared_unit":
                roles = ["spectrum_analyzer"]
            elif unit == "A":
                roles = ["current_probe"]
            elif identifier == "adc_transfer":
                roles = ["audio_analyzer"]
            else:
                roles = ["oscilloscope"]
            assert set(roles) <= set(instruments), (identifier, metric, roles)
            criterion["instrument_kinds"] = roles
        cases.append(
            dict(
                id=identifier,
                board=board,
                metrics=metrics,
                conditions=conditions,
                instrument_kinds=instruments,
                powered=powered,
                method=method,
            )
        )

    for board in boards:
        add(
            board + "_unpowered",
            board,
            {
                n: limit("count", 0, 0, source="Exact schematic/BOM/PCB matching for this source snapshot")
                for n in [
                    "wrong_or_missing_part_count",
                    "unintended_short_count",
                    "land_pattern_mismatch_count",
                ]
            },
            ["as_built_inspection"],
            ["inspection", "dmm"],
            "Identify the exact fabricated PCB, layer stack, assembled BOM/part lots and independent inspection. Compare package dimensions, terminal numbers, polarity, holes, mask/paste and measured unpowered continuity. This inspection does not approve power-up.",
            powered=False,
        )
    dc_conditions = [
        f"vin_{vin}_ambient_{ambient}_load_{load}"
        for vin in ["min", "nominal", "max"]
        for ambient in ["min", "max"]
        for load in ["none", "half", "allocated_max"]
    ]
    for rail, (low, high) in power["normal_targets_v"].items():
        for board, prefix in [("psu", "source"), ("disconnect", "protected_star")]:
            add(
                f"{prefix}_{rail}",
                board,
                {"voltage": limit("V", low, high, source=source + "#normal_targets_v/" + rail)},
                dc_conditions,
                ["dmm", "load", "temperature"],
                "Only after an independent isolated-fixture review: measure signed voltage at the actual rail header against its local AGND. Bind numeric input/load/ambient settings to every condition in the fixture document. Project VIN 10.5–13.2 V and unit ambient 0–40 C are allocations, not verified junction limits. Record return topology, maximum load and uncertainty. Protected-star readings do not qualify remote loads.",
            )
    for board in ["psu", "disconnect"]:
        add(
            board + "_dynamics",
            board,
            {"peak_excursion": limit("V"), "settling": limit("s"), "peak_inrush": limit("A")},
            ["cold_start", "load_step", "shutdown", "partial_power", "restart"],
            ["oscilloscope", "current_probe", "load"],
            "Capture all sources, outputs, local returns and relevant gates under a source-bound energy-limited fixture. Derive limits and approved conditions before testing; none is inferred from a nominal RC ramp or a typical curve.",
        )
    adc_requirements = repo / "hardware/electronics/adc_driver/qualification/measurements.json"
    if adc_requirements.exists():
        for requirement in json.loads(adc_requirements.read_text()):
            if requirement["id"] not in {"ADC-POWER", "ADC-NBIAS"}:
                continue
            ranged = {m: b for m, b in requirement["limits"].items() if isinstance(b, list) and len(b) == 2}
            assert set(requirement["limits"]) - set(ranged) <= {"THS_supply_slew_stress_max_v_per_us"}, (
                "New ADC limit needs an explicit metric/unit mapping"
            )
            measurements = {
                metric: limit(
                    "V",
                    bounds[0],
                    bounds[1],
                    source=str(adc_requirements.relative_to(repo)) + "#" + requirement["id"],
                )
                for metric, bounds in ranged.items()
            }
            measurements.update(
                {metric: limit("V") for metric in requirement.get("rejected_original_health_window_v", {})}
            )
            add(
                requirement["id"].lower().replace("-", "_"),
                "adc",
                measurements,
                [
                    channel + "_" + supply + "_" + load + "_" + temperature
                    for channel in ["left", "right"]
                    for supply in ["supply_min", "supply_max"]
                    for load in ["idle", "reviewed_peak"]
                    for temperature in ["cold", "warm"]
                ],
                ["dmm", "oscilloscope", "temperature"],
                "Measure actual device supply pins and local return under reviewed steady-state corners. These are interface/recommended-operating windows, not driver noise or complete-chain regulation qualification. Missing bias-window monitors remain a design hold. Startup, missing-bias and transient envelopes require separate approved fixtures and limits.",
            )
            if (
                requirement["id"] == "ADC-NBIAS"
                and "THS_supply_slew_stress_max_v_per_us" in requirement["limits"]
            ):
                slew = limit(
                    "V/us",
                    0,
                    requirement["limits"]["THS_supply_slew_stress_max_v_per_us"],
                    source=str(adc_requirements.relative_to(repo)) + "#ADC-NBIAS",
                )
                slew["status"] = "absolute_stress_screen_only"
                add(
                    "adc_supply_slew",
                    "adc",
                    {"absolute_supply_slew": slew},
                    [
                        c + "_" + s
                        for c in ["left", "right"]
                        for s in ["start", "stop", "bias_loss", "restart"]
                    ],
                    ["oscilloscope"],
                    "Capture the magnitude of supply slew at actual FDA supply pins in a separately reviewed energy-limited fixture. The manufacturer's absolute stress limit is a necessary failure screen; meeting it alone never grants an operating/stability pass.",
                )
    add(
        "adc_transfer",
        "adc",
        {"gain": limit("V/V"), "output_offset": limit("V"), "thd": limit("percent"), "noise": limit("V_rms")},
        ["left_20Hz", "left_1kHz", "left_20kHz", "right_20Hz", "right_1kHz", "right_20kHz"],
        ["audio_analyzer", "oscilloscope"],
        "Measure the actual driver with declared source amplitude/impedance and load, bandwidth, weighting and analyzer residual. The ideal 0.4859 V/V model is not an acceptance band. Complete-unit 98/102 dB SNR and 0.005% THD targets cannot be silently assigned as a driver-only noise budget.",
    )
    add(
        "adc_stability",
        "adc",
        {"common_mode": limit("V"), "ringing": limit("V"), "settling": limit("s")},
        ["startup", "converter_equivalent_load", "maximum_reviewed_cable", "warm"],
        ["oscilloscope", "load", "temperature"],
        "Use a reviewed load/model and final force/sense architecture; measure FDA and common-mode feedback, pump/reference ripple and settling. Define allowed cable parasitics, signal amplitudes and limits before claiming stability.",
    )
    add(
        "adc_leakage",
        "adc",
        {"reference_drift": limit("V"), "board_leakage": limit("A"), "servo_recovery": limit("s")},
        ["clean_baseline", "reviewed_hot_humid", "pump_active", "production_cleaning_process"],
        ["electrometer", "temperature", "oscilloscope"],
        "Measure both reference/common-mode paths with documented loading by the measuring instrument. High-value resistors and capacitor nominal values do not establish contamination, leakage, drift or recovery acceptance limits.",
    )
    add(
        "disconnect_faults",
        "disconnect",
        {
            "trip_voltage": limit("V"),
            "fault_to_open": limit("s"),
            "residual_output": limit("V"),
            "peak_current": limit("A"),
        },
        [r + "_OV" for r in power["normal_targets_v"]]
        + [r + "_late_closure" for r in power["normal_targets_v"]]
        + ["gate_power_loss", "input_loss", "recovery"],
        ["oscilloscope", "current_probe", "load"],
        "No powered test while the selected PCB has open/DRC findings. A separately reviewed fixture must define the injected bounds/energy, each MOSFET VGS/common-source measurement and actual bulk-discharge observation. Do not assume UV protection, a fault latch, zero output after opening or a guaranteed 125 us interruption.",
    )
    for board in boards:
        add(
            board + "_thermal_emi",
            board,
            {
                "hotspot": limit("degC"),
                "junction_estimate": limit("degC"),
                "worst_spur": limit("declared_unit"),
            },
            ["idle", "rated_reviewed_load", "warm_ambient"],
            ["temperature", "spectrum_analyzer", "oscilloscope"],
            "Record actual stackup, enclosure/fixture airflow, simultaneous load, thermal model and calibrated probe/antenna setup. Component absolute maximum ratings are not operating qualification or an EMI compliance standard.",
        )
    files.update(str(p.relative_to(repo)) for p in HERE.glob("*.py"))
    files.update(["hardware/qualification/check.py", "hardware/qualification/spec.py"])
    files.add(str((HERE / "README.md").relative_to(repo)))
    # Board analyses are evidence inputs when available, never physical passes.
    for folder in ["adc_driver", "power_supply"]:
        path = repo / f"hardware/electronics/{folder}/qualification"
        if path.exists():
            files.update(
                str(p.relative_to(repo))
                for p in path.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and p.suffix in {".py", ".json", ".md"}
            )
    plan = dict(
        schema_version=2,
        revision="Q02",
        profile="isolated README PCB candidates",
        boards=boards,
        cases=cases,
        decision_rule="expanded uncertainty interval must lie wholly within the stated acceptance interval; overlap is inconclusive",
        source_sha256={n: digest(repo / n) for n in sorted(files)},
        physical_tests_performed=0,
        build_ready=False,
        fabrication_released=False,
    )
    plan["plan_sha256"] = hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return plan
