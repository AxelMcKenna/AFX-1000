# SF01 — higher-pressure fan candidate

The preferred prototype candidate is **two Sunon MF40100V1-1000U-G99 fans**, with a new guard having at least **800 mm² net opening per fan**. This addresses AP01's restrictive low-pressure baseline while retaining a 40 mm fan footprint. No fan, clamp, harness or enclosure geometry is changed by this study.

| Source comparison | V1 preferred | V2 comparison |
|---|---:|---:|
| Rated / maximum current |136 /157 mA|94 /109 mA|
| Two-fan current provision, maximum ×1.2 |376.8 mA|261.6 mA|
| Remainder of existing 416 mA digital reserve |39.2 mA|154.4 mA|
| Published speed / free-air flow |7000 rpm /8 CFM|5800 rpm /7 CFM|
| Published static pressure |0.19 inH₂O|0.12 inH₂O|
| Published free-air acoustic value, one fan |27.3 dB(A)|20.6 dB(A)|
| Remaining pressure in most adverse tested new-guard sensitivity |5.080 Pa|0.019 Pa|

The final row uses **9.2 m³/h total**, 8.0 through two 2200 mm² interior ports, a parallel equal-flow fan assumption, 800 mm² guard per fan, assumed discharge coefficient 0.6, 40°C density, and a speed ratio of `0.85 × 4.8/5 = 0.816`. Actual curves are extracted from the exact-part PDFs' blue vector paths, calibrated using their own inch-water axes. The original curve SVGs and extracted points are retained. No curve from the 2026 `10000` suffix is substituted for the exact `1000U` part.

The 0.85 factor comes from the stated speed tolerance. Its combination with voltage and affinity laws is a **sensitivity model**, not a manufacturer's guaranteed lower pressure curve. Neither the 5.080 Pa allowance nor the 0.019 Pa comparison includes unknown channels, baffles, pin losses, fouling, unequal sharing or recirculation. Installed flow, noise and component temperatures remain unproved. The maximum-current rows likewise do not establish startup, locked-rotor or hot installed current. Source current testing is 25°C/free air after ten minutes. The 20% factor is a planning provision.

These fan loads partition the existing digital reserve; they add no second heat load to WU01. The 39.2 mA remainder must also cover NF02's proposed 6 mA digital logic load, fan control, tach pullups and other unassigned loads. P03.J3 copper/return, full fan-voltage intervals, protection and transient capacity need a fresh solve. All motor heat remains inside the air-energy screen; no external heat export is credited.

The exact fan drawing gives **40±0.5 mm square, thickness 10 to10.5 mm, pitch32±0.3 mm and holes4.3±0.3 mm**. The 300±10 mm leads are26AWG; yellow is the third wire. The thinner fan needs a new, toleranced clamping/spacer stack: the old12.5 mm receiving box cannot serve as a physical clamping face. The manufacturer recommends M4 screws/torque; an M3 floating-bolt alternative needs its own clamp/structure proof. No body deformation or screw-torque approval is claimed.

The third wire is an open-collector frequency output with two pulses per revolution. Its 6 V pullup,5 mA sink and0.5 V low rows are specified at25°C/rated5V. Locked output may be high or low; merely reading a static logic level cannot establish fan health. A real protection/interlock circuit must cover partial power, missing fan, pulse loss and failed sensor states. It has not been implemented here.

Primary documents, independently downloaded and visually inspected on the curve/dimension pages:

- [Exact V1 specification D04114160G-02](https://www.sunon.com/PROSEARCH_FILES/%28D04114160G-02%29-1.pdf), SHA-256 `580372d445b040b56f5faab666a1e4b8483154a08bd435485547df66bc393a2a`.
- [Exact V2 specification D04114220G-01](https://www.sunon.com/PROSEARCH_FILES/%28D04114220G-01%29-1.pdf), SHA-256 `541666c0a1a18ed7a34687d0d8532419607157f57902b9a2640d66a50f167b31`.

Both specify3.5–6 V operation and3.5 V starting **at25°C**, with−10 to70°C operating range. That does not establish hot/installed restart voltage. External source PDFs are hash-pinned and left outside the repository; `analysis.json` records exact paths and URLs.

Reproduce from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m hardware.cad.a12.thermal.forced_air_sunon.analyze
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python -m unittest hardware.cad.a12.thermal.forced_air_sunon.test_sunon -v
```

Eight source/curve/current/adverse-sensitivity checks pass. This is a design comparison; physical and fabrication flags remain false.
