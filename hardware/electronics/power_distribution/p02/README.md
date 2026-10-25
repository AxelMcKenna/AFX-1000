# P02 precision source and complete 5 V distribution candidate

P02 is a **conditional electrical design**, with a native KiCad schematic and independent DC endpoint enclosure. It preserves `5V_DIG_SRC`/`V5_REG_SRC`, the protected rail names and original endpoint targets. It does not replace P01, the certified PSU sources, E25 placement/routing, A11, or the existing system wiring. **Fabrication, physical fit, thermal, startup, stability and build readiness remain false.** The requirements below are new construction requirements, not claims that the present assemblies meet them.

## Source circuit

`power_p02.kicad_sch` contains 48 components. Native all-severity ERC is zero; `check.py` separately checks every connected manufacturer pin and every passive value/net against an independent contract. `generated/verification.json` hashes its checked sources. U1, the three film capacitor packages and the two source strap lands intentionally have no assigned fabrication footprint; a generic land pattern would conceal an unfinished implementation.

P02 is a new source-module block, not a plug-compatible replacement for the old PSU headers. Its J1.1/J1.2/J1.3 bind to VIN_PROTECTED/quiet AGND/POWER_READY (legacy PSU J1.1/AGND/J5.2). P02 J2.1 feeds the replacement `5V_DIG_SRC` at legacy PSU J3.1; P02 J3.1 feeds replacement `V5_REG_SRC` at legacy PSU J2.6. The other four analog source rails remain from the existing raw/LDO circuits. Removing the old 5 V regulators and implementing these bindings in a new native PSU layout is required; no connector-number equivalence or existing physical wiring implementation is claimed.

A TPSM63606RDLR 6 A integrated buck supplies a local nominal 6.0 V preregulator. It replaces the two existing 5 V source regulators in this proposed variant; it is not connected in parallel with them. The unchanged raw boost/Cuk generators remain supplied by `VIN_PROTECTED` according to their **native VIN and inductor pins**, not by the digital 5 V source. The existing source-side SHDN resistors, REF5025 and LT3090 shutdown loads are explicitly assigned an additional 18 mA digital-source budget.

An LT3083IQ DD-PAK postregulator supplies nominal 5.040 V digital. IN receives the 6 V preregulator, while VCONTROL receives `VIN_PROTECTED`; the metal tab is **5V_DIG_SRC**, never grounded. A 909 Ω source-side resistor maintains more than 5 mA steady load even with E26 off. The separate-control arrangement and minimum input/output capacitance follow [ADI LT3083 Rev. B](https://www.analog.com/media/en/technical-documentation/data-sheets/LT3083.pdf). The model uses DD-PAK full-temperature ±6 mV offset, an additional 4 mV load term, 600 mV IN headroom and 1.6 V control headroom. It charges the full 80 mA control-current limit to input power and includes its heat. Neither the regulator's 3 A rating nor its unspecified maximum current limit qualifies late closure or fault SOA.

An LT3045IDD supplies nominal 5.006 V analog, with local OUTS feedback before E26. A shared ADR4550BRZ reference and OPA2192ID provide two separate local SET loops. The 6.8 kΩ SET resistors, 100 nF SET capacitors and 47 nF local feedback capacitors are explicit native connections. The analog divider is 120 Ω/100 kΩ; the digital divider is 800 Ω/100 kΩ. No feedback crosses the disconnect. The analog output offset/load/line allowance is 2.854 mV. Component behavior and pin roles derive from [ADI LT3045 Rev. D](https://www.analog.com/media/en/technical-documentation/data-sheets/3045fa.pdf).

The reference calculation sums initial error, the complete −40…125 °C B-grade box-TC envelope, a conservative full-input-span line term, load regulation and amplifier errors. It adds a **2 mV unqualified assembly/aging/humidity reserve** and ±0.1% total resistor-error allocations. Those allocations are not lifetime guarantees. A 10 kΩ/three 4.7 µF film filter requires at least 12.69 µF effective capacitance and at most 30 nA aggregate hot/aged leakage. Its leakage loss and both amplifier input bias currents are retained explicitly. See [ADR4550 Rev. G](https://www.analog.com/media/en/technical-documentation/data-sheets/adr4520_4525_4530_4533_4540_4550.pdf), [OPA2192](https://www.ti.com/lit/ds/symlink/opa2192.pdf), and the candidate [WIMA MKS2 family](https://www.wima.de/wp-content/uploads/media/d_WIMA_MKS_2.pdf). Film capacitor MPN, package, leakage and aging remain selection/qualification work.

The buck's ±2.5% regulation and ±50 mV ripple envelope, 85% minimum efficiency and effective capacitor bounds are **design allocations**, not guaranteed 6 V performance inferred from a different datasheet test point. Its local output comprises preregulator capacitors and postregulator inputs; E26's millifarads are downstream of the linear regulators. This removes P01's TPS62903 direct-capacitance mismatch but does not prove loop stability. U1 uses 13 kΩ RT and 18 pF feedforward with 50 kΩ/10 kΩ feedback. Actual effective capacitance, compensation, transient behavior and thermal derating must be checked against [TI TPSM63606 Rev. B](https://www.ti.com/lit/ds/symlink/tpsm63606.pdf).

## Physical distribution requirements

All conductor resistances use copper at 100 °C, rho20 = 1.724e−8 Ωm and alpha = 0.00393/K. These material/process values are design assumptions. Each ordinary conductor adds **two 2 mΩ hot/EOL mated contact allocations plus 1 mΩ combined board access copper**. No unknown contact is set to zero. Required maximum single-conductor lengths/minimum areas are:

| Path | Length | Copper area |
| --- | ---: | ---: |
| PSU→E26 analog/digital positive and existing ground wires | 180 mm | 2.08 mm² |
| E26→processor | 150 mm | 2.08 mm² |
| Processor→LED board | 120 mm | 1.31 mm² |
| Other 5 V load branches and new converter return | 150 mm | 0.823 mm² |
| Signal grounds | 200 mm | 0.326 mm² |
| Gain coils and LED emitter tails | 150 mm | 0.326 mm² |

E26 positive copper is allocated 3 mΩ per 5 V path; analog hot switch resistance is 6 mΩ and digital is also conservatively 6 mΩ, allowing one conducting device on each side rather than assuming equal sharing. Each ground wire includes finite board access. An additional ±0.5 mV analog/±2 mV digital load-pad ground-spread requirement remains beyond those port resistances. The A↔D star bridge is at most 1 mΩ; its multiport transfer behavior requires extraction and measurement.

**Two additional ground straps are necessary.** Ordinary harness returns alone fail the full analog distribution enclosure. The new source quiet-star attachments J5/J6 require separate top-side analog/digital E26 land interfaces. Each full strap is bounded by 2 mΩ including joints and both board accesses:

| Strap | Maximum length including bends | Minimum copper section | 100 °C copper | Two hot/EOL joints | Combined board access | Total candidate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Analog | 180 mm | 20 mm² (e.g. 10×2 mm) | 0.204 mΩ | 0.700 mΩ | 1.000 mΩ | 1.904 mΩ |
| Digital | 90 mm | 20 mm² | 0.102 mΩ | 0.700 mΩ | 1.000 mΩ | 1.802 mΩ |

These lengths follow the current PSU/E26 separation rather than a fictional 40 mm analog link. Joint limits are requirements without a selected qualified terminal/finish/torque system. The 1.000 mΩ combined board-access allowance must be demonstrated from real filled copper, attachment geometry and the path to the original E26 header-return stars. Existing A11 has **no demonstrated bar/stud support, clearance, insulation or fastener stack**. Its 0.3 mm underside tail gap cannot silently accommodate nuts. Proposed E26 top attachment areas are analog centre (111, 39.5) mm and digital centre (128, 27) mm, each 10×8 mm, relative to board origin; the board enclosure datum is (8, 108.5, 4.6) mm. These are interface reservations with implemented_in_pcb=false, pending land/stud, plating, underside keepout and mechanical/interface review. A new ≤1 mΩ input-guard-to-source quiet-star return is also required; this is not the old E23 wire.

A supplementary E26 J3.2→converter J4.2 analog return is part of P02. The current baseline powers that converter through analog 5 V while its available return traverses processor/signal ground links. Every new multi-load connection requires a real fanout assembly; no single unspecified header terminal is assumed to accept several wires.

## Actual endpoint proof and loads

`loads.py` checks all nine interboard 5 V positive wires against the current system manifest and actual native load-board header nets. It also checks all four LED anode groups, GAIN_LOW coil returns, and Seed VIN behind R1. `distribution.py` uses every interboard AGND wire from the manifest, including parallel signal-ground returns. Panel returns are not silently merged into an imaginary panel ground plane.

The proof bounds every independent ground resistance from **zero to its nonzero maximum**, using Rayleigh effective-resistance bounds, reciprocity and the grounded-network maximum principle. The polarization identity explains transfer impedance; mixed resistance corners are covered, not mistaken for the all-hot network. Load currents independently range from zero to their allocation. Positive and negative analog return currents do not cancel by assumption. Input-guard current can pull ground negative and is included up to 3.6 A. Positive paths include full source/header/E26/FET/outgoing cable loss.

Digital protected allocation is 2.4 A: Seed/local 1.0 A; LED logic 0.380 A plus four 0.096 A emitter groups; bypass 0.080 A; two gain coils 0.030 A each; monitor 0.080 A; and **0.416 A reserve at E26**, not routed through the Seed filter. Analog protected allocation is 0.251 A: ADC 0.100 A, converter 0.140 A, monitor 0.003 A, reserve 0.008 A. Separate ±12/±19 and extra 3V3 return allocations are present. These are requirements, not measured board consumption or SD/card-regulator capability.

The independent enclosure, including ±3 mV analog and ±20 mV digital ripple/load-step reserves, gives:

| Endpoint group | Minimum | Maximum | Unchanged target |
| --- | ---: | ---: | --- |
| ADC analog 5 V | 4.976798 V | 5.022630 V | 4.975…5.025 V |
| Converter analog 5 V | 4.977920 V | 5.022420 V | 4.975…5.025 V |
| Monitor analog 5 V | 4.978832 V | 5.022452 V | 4.975…5.025 V |
| Worst digital emitter endpoint | 4.929711 V | 5.083822 V | 4.900…5.100 V |

All thirteen endpoint groups pass this **conditional DC enclosure**. The tightest analog margin is about 1.8 mV. Source/fanout/contact/thermal requirements cannot be relaxed independently without rerunning it. Seed R1 is 0.47 Ω/1%/1 W in the actual native circuit: the 1 A allocation causes up to 0.4747 V drop and 0.4747 W heat; the resulting module VIN remains above the project's 4.0 V bring-up screen. Manufacturer module limits and R1 temperature derating remain unverified.

## Input, heat and startup gates

The full digital regulator allocation is about 2.424 A after local source loads and bleed; the shared preregulator is about 2.703 A including analog ground current/reference consumption. Guaranteed headroom and minimum-load screens pass under the stated preregulator envelope. The analog source consumes its bleed **in addition to** the protected 0.251 A load.

Total input allocation is about **34.4 W / 3.28 A at 10.5 V**, including the raw converters, reference/SHDN/local loads, control current and auxiliary supply. **The old E23 minimum limit and 3 A adapter are incompatible.** A new ≥4 A normal input profile requires actual guard, jack, fuse, wire, contact and thermal engineering; no change to E23 is claimed here.

LT3083 pass/control heat is about **3.52 W**. At 60 °C ambient and a 110 °C junction design limit its complete junction-to-ambient path must be about **14.2 °C/W or better**. The DD-PAK junction-to-case figure alone proves no PCB/chassis thermal result. Module loss at the allocated efficiency is about 2.96 W. None of these thermal paths has been implemented or measured.

The ≥126.8 ms reference RC permits a reference-acquired, preconnected-bulk charging-current screen below regulator ratings. That narrow screen excludes initial SET-current floor acquisition: with an allocated 80 nF minimum SET capacitance, the initial current-source slew can demand approximately 4.53 A digital/1.40 A analog capacitor charging current before load current, so regulator current limiting and startup SOA cannot be bypassed by this RC calculation. It does **not** limit E26 closure after the source is already charged. Digital/analog regulator SET-current floors are approximately 0.347/0.694 V before reference acquisition. The existing E26 Si8751/gate circuit has no established guaranteed slew/current bound into the modeled 7.1 mF/1.1 mF. Late closure, SOA, source current-limit interaction, shutdown, partial power and real SET-loop phase margin remain hard release holds. No transient or physical test is claimed.

## Reproduce

```sh
python3 -m hardware.electronics.power_distribution.p02.generate
python3 -m hardware.electronics.power_distribution.p02.check --kicad-cli /path/to/kicad-cli
python3 -m hardware.electronics.power_distribution.p02.analysis
python3 -m hardware.electronics.power_distribution.p02.analysis --check
python3 -m unittest discover -s tests/tooling -p 'test_power_p02.py' -v
```

Tests reject pin/divider errors, prove actual endpoint coverage and native source domains, expose failure when straps are absent or contacts degrade, and compare independent mixed/random ground networks against the interval enclosure. They retain all physical release flags false.
