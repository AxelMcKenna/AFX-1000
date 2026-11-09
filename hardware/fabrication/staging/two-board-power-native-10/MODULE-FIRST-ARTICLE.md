# Module-feed first-article procedure — TBP10 design baseline

This is a procedure for the eventual prototype, not a record of completed
measurements. Update it against the final routed revision, BOM and receiving
limits before use. Fabricating the first prototype does not require prior
measurements of that same unbuilt board; it requires a reviewed design,
manufacturing package and executable bring-up plan. Production qualification
requires the subsequent results.

## Fixture and recorded signals

Use an isolated programmable DC source, current monitor, electronic load,
programmable shorting fixture and differential probes. Record instrument
bandwidth, shunt value/insertion loss, temperature, PCB revision, component lot,
firmware configuration and all loads. Use differential probes for MODULE_RTN
and each isolated secondary: a grounded probe clip must not join those domains.

Measure P03 protected feed at G_U1 IN 8/9, OUT 23/24, module inputs at N_U17.2/.1
and N_U22.2/.1, branch current, each module's current, RTN-to-GND voltage,
GLOBAL_MASTER and E28 fault latch. Record both secondary outputs with their own
references. Add accessible pads for these nodes during final placement.

The fixture must remove power after **10 ms of sustained abnormal branch
conduction** in the explicit overcurrent tests below. This is a provisional
prototype acceptance/abort criterion, not a TPS26601 datasheet maximum or an
output discharge specification. Size the fixture for the actual source and
stored energy. Start protector tests with dummy loads and without the modules;
only fit the modules after the limiter, voltage thresholds and latch pass.

## Unpowered and low-energy checks

1. Verify the exact **TPS26601RHFR** marking, pin-one orientation, both IN/OUT
   terminals and soldered exposed pad. TPS26600/02 are not permitted substitutes.
2. Verify R5=22.1k and two 100nF C0G ramp capacitors. Check the final complete
   tolerance/temperature budgets and capacitor voltage ratings against the BOM.
3. Inspect RTN copper and thermal vias against the PCB netlist. Confirm there
   is no copper short to GND; ordinary resistance readings can include the IC's
   internal circuitry and are not a standalone isolation test. Check the unique
   G_NT1 return connection and the secondary-domain isolation boundaries.
4. With the DC/DC modules disconnected, start with an energy-limited 12 V source
   and a light dummy load. Establish correct input/output polarity and static
   operation. Increase fixture current capacity before testing the protector's
   own limit so the supply does not mask its action.

## Electrical matrix

| Test | Stimulus and capture | Acceptance / follow-up |
| --- | --- | --- |
| Voltage window | Slowly sweep branch input through UV on/off and OV off/re-enable with a light dummy load; measure input and RTN offset simultaneously. | Measured thresholds agree with actual-part limits and the calculated windows. Correct calculations for measured/reference bounds. Do not expose fitted modules to an unverified OV path. |
| Current threshold | At 12 V, sweep dummy load through the breaker threshold in short controlled pulses, recording threshold and duration. Repeat at voltage/temperature corners. | No nuisance trip at accepted normal current; sustained overcurrent causes timer shutdown and latch-off. The 0.404–0.623 A screen is an engineering envelope, not a guaranteed receiving range. Establish an accepted bound or redesign. |
| Moderate fault | Use a load that drives the switch into current limit with output near 8–9 V. | Fault clears within the provisional 10 ms criterion without depending on thermal shutdown. Record time above threshold and switch voltage/current; abort on failure. |
| Hard short after startup | Apply a low-inductance output short after stable operation. Capture the first fast-trip pulse, restart and timed cutoff. | Include the complete pulse/restart sequence in the energy measurement. No repeated autonomous retries after the timer latch; external fixture aborts at its limit. |
| Short before power-up | Hold output shorted, then apply input. | Timer cutoff and retained latch-off occur; no sustained current or endless retry. |
| Reset | Remove the fault while input remains valid, then exercise RUN, then remove external DC and measure residual branch VIN. | Fault removal alone does not restart. Record RUN behavior but do not rely on it as reset. Confirm VIN has fallen below 1 V before reapplying DC for this test. Verify a clean new startup. |
| Actual module startup | Fit N_U17/N_U22 with final local capacitors and accepted secondary loads. Test simultaneous start at 11.4, 12 and 12.6 V branch input, cold/hot and rapid cycling. | No false cutoff; measure total and individual current, primary capacitance/inrush and secondary settling. Verify the 0.35 A/60uF assumptions or revise the circuit. The ideal 16–27 ms ramp is not itself a loaded-startup guarantee. |
| Operating voltage floor | With accepted full load, reduce input toward UV-off; record voltage directly at both module pins. | Neither module remains operating below 9 V. Verify total copper/contact drop ≤0.1 V and the separate RTN allowance ≤10 mV, or recalculate thresholds. Check transients separately from steady limits. |
| One module faulty | Test each module independently with a controlled input fault and separately with a secondary-output overload/short while the other operates. | Determine which protection acts and both modules' resulting current/temperature. Shared breaker action is not proof of individual module containment; complete the separate containment design before release. |
| System UV and fault interlock | Exercise shallow/short UV, sustained UV and deep AUX loss with the actual NF/E28 loads; capture ARM, fault request, latch and GLOBAL. | Record minimum captured pulse and physical OFF interval. Verify intended restart policy. AUX_VALID loss currently resets E28's latch; do not claim retention through deep AUX loss from settled Boolean checks. |
| Heat and extended operation | Run accepted maximum load at the final enclosure ambient/airflow corners; measure device, module, diode and capacitor temperatures. | Meet the final component derating and enclosure thermal limits. An open-bench temperature pass cannot qualify the installed housing. |

In overcurrent tests, integrate measured switch dissipation and primary pulse
energy; a modeled 0.093 J at 14.8 V, 10 ms and 0.628 A is only a fixture-sizing
screen, not guaranteed device withstand. External capacitors can discharge into
a fault after the switch opens; include that energy separately.

## Design work before first prototype release

- Finalize per-module fault containment and the normal/fault load envelope.
  The common nominal 0.513 A breaker is not equivalent to two independent
  250 mA slow fuses. Confirm time/current coordination and added voltage drop.
- Resolve the narrow startup margin using supported current bounds, actual
  capacitor data and module requirements. Do not use nominal efficiency as a
  guaranteed minimum or capacitance marked on an MLCC as its effective value.
- Complete critical placement, short clamp/bypass paths, the RTN thermal
  copper/vias, force-return star and accessible test nodes. Validate final
  DRC/ERC, all native connections, stack-up, paste/mask and assembly details.
- Record final acceptance values and temperature range in the manufacturing
  package. Any alternative to the provisional 10 ms criterion needs a supported
  energy/thermal assessment, not a relabeling of the nominal datasheet delay.

Save raw scope captures, setup photographs, CSV traces, instrument settings and
pass/fail observations keyed to final PCB/BOM hashes. No test in this document
has been performed on physical hardware.
