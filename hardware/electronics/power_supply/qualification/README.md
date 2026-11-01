# Qualification audit of the pictured main-supply PCB

This audits the actual **157-part, 90 × 44 mm E14 routing candidate** shown in the README. It does not substitute the unimplemented P02 source module, edit the original PCB or refresh an old certificate to hide changes. A fresh isolated native check closes all 322 declared paths, with zero ERC, all-severity DRC, parity or open-connection findings. **The board nevertheless fails analytical acceptance for the unrestricted temperature and complete load boundaries below. It is not qualified for fabrication, power-up or the final unit.** No physical measurement has been performed.

## Demonstrated failures

The native TPS62933F divider is R10 + R51 = 10,510 Ω over R11 = 2,000 Ω. Using its actual ±150 nA feedback leakage and the project's ±0.1% total resistor allocations, the 0…85 °C junction reference limits yield **4.919091–5.089181 V** before the project's ±10 mV excursion allowance. This is a conditional source-feedback result; the physical output-return offset is not proved. The manufacturer's full −40…150 °C limits yield **4.894113–5.114243 V**, or **4.884113–5.124243 V** with that excursion. The 4.9–5.1 V source target therefore does not hold over that component range. The unit's 0…40 °C ambient objective does not prove its regulator junction stays below 85 °C.

A trim cannot solve the full-temperature problem: the nominal upper resistance would have to be **at least 10,550.624 Ω and at most 10,450.722 Ω simultaneously**. Even at conditional 0…85 °C, the complete load target becomes infeasible when adding only the older 3.5 mΩ switch/star allocation and four 1 mΩ contact allocations, with **zero wire resistance**. Its upper resistance would need to be at least 10,521.235 Ω and at most 10,512.013 Ω. These contact values are requirements used for the calculation, not measured or guaranteed connector properties. Failed allocated corners are retained as `failed`, separately from missing physical evidence.

Analog 5 V has only **15.144 mΩ** available for the entire 0.251 A positive/return drop at the source's worst corner, even before extra ripple or shared-return effects. Its old 6.5 mΩ switch/star allocation consumes part of that allowance. This is a resistance ceiling, not proof that the actual path meets it. P01/P02's separate conditional redesigns cannot certify the native E14 source.

At the original 1.8 A digital budget, the existing conditional preconnected-capacitor startup screen fits its old input-guard allocation. Repeating the same narrow screen for the newer 2.4 A digital reserve fails: the extra input current exceeds the remaining guard margin. It still omits other rail charging and late disconnect closure. `generated/analysis.json` records the complete calculation using the native E14 power values and the actual earlier E23 guard allocation; neither the limit-programming tolerance nor the resulting startup envelope is physically guaranteed.

## Construction and unresolved performance

Independent pin checks confirm that both LT3471 exposed pads are AGND, positive regulator tabs are their outputs, and both LT3090 exposed pads and ILIM are their **negative inputs**. The enhanced REF5025E pin 1 is enable, not the older grade's DNC. Package identity/pitch and these critical nets are consistent with manufacturer drawings. This does not approve every land, paste aperture, fabrication tolerance or solder process.

The board declares six copper layers but **no actual stackup**. The new trace estimates evaluate both hypothetical 35 µm and 70 µm finished copper at an explicitly assumed 85 °C conductor temperature. They use the actual measured route lengths/minimum widths. They exclude via barrels, pad spreading, contacts and return-current distribution, so they are not whole-board resistance or ampacity results. Digital positive-header drop is locally sensed by its feedback connection; it must not be blindly subtracted again as an uncompensated output loss. The real feedback-ground-to-output-return displacement remains unqualified.

Both boost positive outputs retain passive `VIN_PROTECTED → inductor → diode → raw output` paths while the switchers are disabled. SHDN is not galvanic input isolation. Partial-power tests must capture those precharged rails and all affected reference/SET/control nodes. The audit establishes the path, not its loaded precharge voltage or timing.

The digital buck has local 44 µF nominal ceramic output capacitance but the selected disconnect alone adds 4,700 µF nominal when connected. The LT3080 analog output sees a separate 1,500 µF protected bulk. Distributed loads add more capacitors and wire/contact impedances. The existing slow soft-start is conditional on preconnection and cannot limit a later gate closure. Actual capacitor MPNs, effective capacitance, ESR, cable impedances and switch slew/SOA must enter the models and tests.

The TPS62933F's 0.9 W loss assumption at 55 °C local ambient requires a **33.33 °C/W or better actual junction-to-ambient path** to retain the 85 °C accuracy screen. The manufacturer's JEDEC/EVM thermal figures do not establish the thermal behavior of this compact six-layer board and enclosure. The positive/negative LDO dissipations and raw-pair efficiencies also remain conditional allocations. Shared heating, current limits and foldback recovery require analysis and real measurements.

Raw-rail switch stress currently includes an unproved 3 V ringing allowance. The high pair has only 1.92 V left below the LT3471's 42 V absolute maximum under that allocation. Actual edge ringing, commutation loop inductance, reference ground movement, compensation, EMI, LDO SET-loop stability and fault/recovery behavior are unqualified. A routing-length threshold or clean DRC is not a bandwidth, noise or phase-margin specification.

## Reproduce

```sh
uv run --locked python -m hardware.electronics.power_supply.qualification.analysis \
  --kicad-cli /path/to/kicad-cli
uv run --locked python -m hardware.electronics.power_supply.qualification.analysis --check
uv run --locked python -m unittest discover -s tests/tooling \
  -p test_power_supply_qualification.py -v
```

The wrapper redirects the existing native routing checker into this new audit folder, exports a fresh schematic netlist/ERC and confirms the original source/evidence files are byte-unchanged. `source-contract.json` records the primary manufacturer references. `measurement-requirements.json` separates sourced/project limits from still-undefined dynamic criteria. Root qualification tooling may bind those tests to actual fixture and instrument evidence; no firmware binary is required for this isolated power board.

The source inlet is `VIN_PROTECTED`, whose reviewed normal boundary is 10.5…13.2 V. Applying a raw misplug test directly to this board would bypass the separate input protection; LT3471's 16 V absolute input rating is not a normal operating or test target. Whole-unit, destructive fault and production acceptance procedures require a completed compatible assembly and reviewed fixtures. There is no physical test release in this packet.
