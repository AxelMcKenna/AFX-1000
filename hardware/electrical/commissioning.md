# A0.2 bring-up record

No physical step below has been performed. Record PCB/enclosure and Seed revisions,
firmware SHA-256, power source, instruments, ambient temperature and wiring.
Attach scope/audio captures; host test passes are not measurement evidence.

## Before power

1. Complete native KiCad/ERC, footprint and netlist review. Check the exact contact
   numbering on purchased relays, switches, jacks, displays and modules.
2. Inspect shorts, negative capacitor orientation and the LT3015 tab isolation.
   Verify raw ±24 V cannot reach the line amplifier, Seed or logic.
3. With power disconnected, verify IN-L→OUT-L and IN-R→OUT-R through NC, no L/R
   short, and K3 grounding each amplifier input.
4. Verify chassis/audio-ground continuity and every harness conductor against
   `carrier-connections.csv`. The old rear CAD does not yet include all new ports.

## Power and digital controls

1. Bring up the power circuit alone with current-limited 12 V DC. Record protected
   input, 5 V, raw ±24 V, regulated ±20 V, ripple, current and temperature under
   representative load. Check startup/turn-off/interruptions, effective output
   capacitance, ESR and regulator stability.
2. Attach the Seed with audio/relays disconnected. Confirm compatible QSPI
   bootloader and 64 MB SDRAM before flashing. Measure boot, cache/DMA behavior,
   SDRAM, stack high-water and worst callback timing.
3. Establish Seed 3.3 V current/headroom with SD, controls and maximum LED/display
   load. Resolve the rail budget before populating the full lighting assembly.
4. Verify all 32 switch bits, eleven analog channels/endpoints/centers, mux spares,
   LEDs and digits. Measure mux settling, crosstalk and reference/noise behavior.
5. Check touch with the real lens and eight electrodes. Disconnect I²C during a
   gesture and verify release. Measure bus rise time with breakout pull-ups.
   Exercise absent/bad cards and boot loading of valid banks/User profiles.

## Relays and supervision

Use a resistive test load and scope before an amplifier/speakers. Use test firmware
with separate deliberate audio-ISR and foreground stalls. Pulling a GPIO alone is
not a crash test.

| Test | Required observation |
| --- | --- |
| Cold boot, missing/bad firmware or allocation failure | Dry remains selected |
| Manual bypass closed, then released | Dry on close; delays and two fresh heartbeat edges before reconnect |
| Each analog rail removed | Health clears, dry returns, no false reconnect |
| 2.5 V reference removed | Reference supervisor prevents reconnect despite invalid comparator inputs |
| Audio ISR stopped, foreground running | D17 withdraws, D28 stops, dry returns |
| Foreground stopped, audio running | D28 stops, external watchdog returns dry |
| Heartbeat frozen high/low through repeated watchdog frames | No re-enable without a complete fresh pulse and second rising edge |
| 3.3 V loss with 5 V held | Both local gate clamps disable drive |
| 5 V collapse with 3.3 V held | No false wet selection through logic power transitions |
| Power loss/quick replug | Dry path and recovery sequence remain valid |

Capture permission, gates/drains, K3 mute, output contact continuity, health and
audio. Measure complete fault-to-dry time across temperature, supply and fault
phase; include TVS energy/temperature/overshoot, coil current, contact bounce and
click amplitude. No maximum complete fault-to-dry bound is qualified yet.

## Audio and enclosure acceptance

1. Measure actual Seed input impedance and ADC/DAC full-scale levels first.
   Complete/qualify input overload and ESD protection before overload testing.
2. With software gains at intended unity and effects neutral, calibrate each
   MASTER trim at +4 dBu into 10k. Enter manual bypass before changing mode;
   calibrate SEND at -10 dBV. Repeat both because feedback branches interact.
   Record any pad/feedback change that exceeds the available trim range.
3. Sweep level/frequency; measure clipping/headroom, phase, round-trip latency,
   channel separation, output impedance, SNR and THD+N. Scope U28 stability with
   actual cable capacitance, load and clipping recovery.
4. Compare with the published targets: 20 Hz–20 kHz, 20 dB headroom, ≥22k input,
   ≤1k output into 10k, 0.005% THD and rated-output SNR 98 dB MASTER / 102 dB SEND.
   Record bandwidth, weighting and signal conditions to make comparisons valid.
5. Capture and compare a physical RMX-1000 effect/control corpus. Electronics
   operation alone does not close the outstanding DSP/interaction requirements.
6. Run a real two-hour audio/control/SD session, repeat fault tests warm, and check
   thermal behavior, enclosure interference, lever return, knob/lens retention
   and connector strain relief.

Original specification/routing source:
[Pioneer operating instructions](https://docs.pioneerdj.com/Manuals/RMX_1000_DRB1649B_manual/).
