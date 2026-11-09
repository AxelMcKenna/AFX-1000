"""Design the independent 12 V input branch for the two TMR 1-1215 modules.

Numerical screens explicitly distinguish specified limits, model extrapolations
and receiving requirements. None substitutes for the installed transient test.
"""
import itertools
import json
from pathlib import Path

from hardware.fabrication.integrate_two_board_signal import REPO, STAGING, read_netlist, sha

OUT = STAGING / "two-board-module-feed-01"
BASE = STAGING / "two-board-power-native-06"
TI = "https://www.ti.com/lit/ds/symlink/tps25947.pdf"
TRACO = "https://www.tracopower.com/tmr1-datasheet"
RFP = "TB05_A_Resistor_SMD:R_0603_1608Metric"
CFP = "TB05_P_Capacitor_SMD:C_0805_2012Metric"
DFP = "TB05_P_Diode_SMD:D_SMA"
VIN, VOUT, GND = "PWR_MODULE_FEED_IN", "PWR_MODULE_12V", "PWR_MODULE_INPUT_GND"


def components():
    rows = []

    def add(ref, part, footprint, pins, source, note, xy):
        rows.append(dict(ref=ref, part=part, footprint=footprint, source=source,
            note=note, x=xy[0], y=xy[1], pins=[dict(number=str(n), name=name,
            net=net, kind=kind, side=side) for n, name, net, kind, side in pins]))

    add("U1", "TPS259474LRPWR", "TBP07_Module:TI_RPW0010A", [
        (1,"EN_UVLO","MODULE_UV","input","L"), (2,"OVLO","MODULE_OV","input","L"),
        (3,"PG",None,"open_collector","R"), (4,"PGTH",GND,"input","L"),
        (5,"IN",VIN,"power_in","L"), (6,"OUT",VOUT,"power_out","R"),
        (7,"DVDT","MODULE_DVDT","passive","R"), (8,"GND",GND,"power_in","L"),
        (9,"ILM","MODULE_ILM","passive","R"), (10,"ITIMER","MODULE_ITIMER","passive","R")],
        TI, "Independent of GLOBAL_MASTER; PG unused, PGTH grounded. Latch reset needs VIN=0 or EN<0.45V.", (65,70))
    for ref,value,left,right,xy in [
        ("R1","470k",VIN,"MODULE_UV",(180,35)), ("R2","59.0k","MODULE_UV",GND,(260,35)),
        ("R3","470k",VIN,"MODULE_OV",(180,70)), ("R4","43.2k","MODULE_OV",GND,(260,70)),
        ("R5","6.49k","MODULE_ILM",GND,(180,105))]:
        add(ref,value+" 0.1% 25ppm/K; complete resistance budget 0.5%",RFP,
            [(1,"A",left,"passive","L"),(2,"B",right,"passive","R")],
            "", "0603 precision resistor; exact order code and full drift budget require BOM receiving.",xy)
    for ref,value,fp,left,right,xy,note in [
        ("C1","1uF 50V X7R 10%",CFP,VIN,GND,(65,135),"At least 0.5uF effective at maximum DC bias; local IN bypass."),
        ("C2","2.2uF 50V X7R 10%","TB05_P_Capacitor_SMD:C_1206_3216Metric",VOUT,GND,(65,170),"At least 1uF effective; local OUT bypass, in addition to N_C4 and N_C31."),
        ("C3","4.7nF 50V C0G 5%; complete 6%",CFP,"MODULE_DVDT",GND,(260,105),"Typical ramp 0.426V/ms. 50V rating exceeds maximum input plus 5V."),
        ("C4","2.2nF 50V C0G 5%; complete 6%",CFP,"MODULE_ITIMER",GND,(260,140),"Blanking duration calculated from specified current and voltage limits.")]:
        add(ref,value,fp,[(1,"A",left,"passive","L"),(2,"B",right,"passive","R")],"",note,xy)
    for ref,part,net,url,xy in [
        ("D1","SMAJ15A-E3/61",VIN,"https://www.vishay.com/docs/88390/smaj50a.pdf",(180,175)),
        ("D2","SS14-E3/61T",VOUT,"https://www.vishay.com/docs/88746/ss12.pdf",(260,175))]:
        add(ref,part,DFP,[(1,"K",net,"passive","L"),(2,"A",GND,"passive","R")],url,
            "Local transient clamp; actual temperature, inductance and pulse stresses require review.",xy)
    add("NT1","MODULE_RETURN_STAR","TBP07_Module:Return_Star",[
        (1,"P03_BULK_RETURN","PWR_AGND","passive","L"),(2,"MODULE_FORCE_RETURN",GND,"passive","R")],
        "", "Copper net tie at P_C103.2; sole connection of module primary return to system ground.", (65,215))
    return rows


def divider(top, bottom, thresholds):
    # I>0 is current flowing into the IC. KCL gives Vs=Vpin*(1+Rt/Rb)+I*Rt.
    samples = [v*(1+rt/rb)+i*rt for v,rt,rb,i in itertools.product(
        thresholds, [top*.995,top*1.005], [bottom*.995,bottom*1.005], [-.1e-6,.1e-6])]
    return [min(samples), max(samples)]


def calculations():
    uv_on = divider(470e3,59e3,[1.183,1.223])
    uv_off = divider(470e3,59e3,[1.076,1.116])
    ov_off = divider(470e3,43.2e3,[1.183,1.223])
    ov_on = divider(470e3,43.2e3,[1.076,1.116])
    # The 0.425/0.575 A row is specified at 6.65k. Scaling to 6.49k uses
    # the datasheet's inverse-resistance model; it is NOT a new tested row.
    ilim = [.425*6650/(6490*1.005), .575*6650/(6490*.995)]
    blank = [1.286*2.2e-9*.94/2.5e-6, 1.741*2.2e-9*1.06/1.2e-6]
    nominal_slew = 2000/4700  # V/ms, datasheet equation 4 (typical)
    # Charging-current screen assumes unity DVDT-to-output slope; only
    # typical output slew is specified, so label this conditional.
    conditional_slew = 3.82e-6/(4.7e-9*.94)
    load_budget, total_cap_budget = .35, 60e-6
    conditional_inrush = conditional_slew*total_cap_budget
    assert uv_on[1] < 11.4 and ov_off[0] > 12.6
    assert uv_off[0] - .10 > 9.0 and ov_off[1] < 18
    assert load_budget+conditional_inrush < ilim[0]
    assert 549 < 6490*.995 < 6490*1.005 < 6650
    return dict(
        assumptions=dict(resistance_total_fraction=.005, timing_cap_total_fraction=.06,
            pin_leakage_a=[-.1e-6,.1e-6], nominal_12V_receiving_window_v=[11.4,12.6],
            maximum_branch_distribution_drop_v=.10, accepted_source_window=False),
        UV_turn_on_v=uv_on, UV_turn_off_v=uv_off, OV_turn_off_v=ov_off, OV_reenable_v=ov_on,
        nominal_current_limit_a=3334/6490,
        model_scaled_current_limit_a=ilim, current_limit_model_is_not_new_datasheet_test_row=True,
        overcurrent_blanking_s=blank, typical_slew_v_per_ms=nominal_slew,
        typical_12V_ramp_s=12/(1000*nominal_slew),
        conditional_max_slew_v_per_s=conditional_slew,
        receiving_operating_current_a=load_budget, receiving_total_output_capacitance_f=total_cap_budget,
        conditional_capacitive_inrush_a=conditional_inrush,
        conditional_combined_current_a=load_budget+conditional_inrush,
        source_contract_normal_current_screen_a=.17412935323383083,
        two_full_1W_modules_typ_efficiency_input_current_at_9V_a=2/(9*.77),
        normal_loss_45mohm_model_w=load_budget**2*.045,
        normal_drop_45mohm_model_v=load_budget*.045,
        fault_input_power_at_14_8V_and_scaled_limit_w=14.8*ilim[1],
        receiving_limits_verified=False,
        limits=["TMR efficiency is typical, not a minimum; startup/internal capacitance/current are not bounded by the datasheet table.",
                "0.35A load and 60uF total capacitance are receiving requirements, not measured or manufacturer-guaranteed values.",
                "Output slew specifications are typical; charging-current projection is a conditional design screen.",
                "Moderate persistent overload latches after ITIMER. Fast short trips, then retries in current limit; thermal shutdown latches L variant.",
                "Neither 500ns fast-trip nor 2us circuit-breaker delay is specified as a maximum.",
                "A common approximately 0.51A electronic branch limit is not equivalent to two 250mA slow fuses; per-module fault containment still needs acceptance.",
                "UV/OV faults recover automatically. RUN-off is not proven to discharge VIN enough to reset; DC power removal is the specified reset until discharged timing is proven."])


def run():
    assert OUT.exists() and not (OUT/"design.json").exists()
    parts,pins=read_netlist(BASE/"netlist.xml")
    for r in ["N_U17","N_U22"]:
        assert parts[r].findtext("value")=="TMR 1-1215"
        assert pins[(r,"2")]==pins[("N_J6","1")]
        assert pins[(r,"1")]==pins[("N_J6","2")]
    assert pins[("N_J6","2")]!=pins[("P_C103","2")]
    assert pins[("P_C103","1")]==pins[("P_U101","17")]
    data=dict(revision="TBP07 module branch design", components=components(), calculations=calculations(),
        source_endpoint=["P_C103","1"], return_star_endpoint=["P_C103","2"],
        module_positive_endpoint=["N_J6","1"], module_return_endpoint=["N_J6","2"],
        source_sha256={str(p.relative_to(REPO)):sha(p) for p in [Path(__file__), BASE/"netlist.xml",
            REPO/"hardware/qualification/boards/startup_negative_circuit/uv_recovery/integration-contract.json",
            *sorted((OUT/"sources").glob("*.pdf"))]},
        manufacturer_sources=dict(TPS25947=TI,TMR1=TRACO),
        TMR1_local_bytes_available=False, TMR1_review="Official search-indexed Aug 7 2024 model/input tables; direct retrieval 403; complete original review remains open",
        electrical_transients_qualified=False, complete_unit_fabrication_released=False)
    (OUT/"design.json").write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps(data["calculations"],indent=2))


if __name__=="__main__":
    run()
