# Follow-up: remove thermal dependence from module short-fault cutoff

TBP08's independent audit identifies a post-fast-trip current-limit condition
that the input UV comparator cannot see. A 12 V input and 8.7 V output at the
nominal 0.514 A setting dissipate about 1.70 W in the protector. The example
41.7°C/W, 25°C-ambient calculation reaches about 96°C, below the typical thermal
trip. This is a counterexample to assuming thermal shutdown always clears a
module undervoltage state, not a validated transient simulation.

**Next candidate: TPS26601RHFR with MODE left open.** The manufacturer's
[TPS2660 datasheet](https://www.ti.com/lit/ds/symlink/tps2660.pdf), section 9.4,
explicitly runs its fault timer during startup current limiting. A hot short
fast-trips, restarts in current limit and follows that startup behavior. The
TPS26601 variant then remains off; TPS26600 and TPS26602 in the same open-MODE
configuration retry. Do not substitute those variants.

The table gives a **nominal 4 ms** circuit-breaker delay with no maximum listed.
This supports a timer-operated topology, not a guaranteed 4 ms upper bound.
Specify and verify acceptable startup and fault duration in the first-article
plan; use an external timed shutdown if the final required bound cannot be
supported by this part's specification and qualification.

The archived original is [sources/tps2660.pdf](sources/tps2660.pdf), SLVSDG2G,
December 2019, with the current ordering addendum. Pages 9 and 27 were rendered
and visually checked; sections 9.3.5.1.2, 9.3.5.2 and 9.3.5.5 were read.

## Required implementation changes

- Recalculate current setting: IOL = 12 / RILIM(kΩ), and nominal ICB = IOL − 0.03 A.
  Do not reuse TPS25947's 6.49 kΩ setting. Table limits at other resistor values
  must not be presented as guaranteed limits at an interpolated setting.
- Recalculate slew capacitance from the 23.75–25.5 gain and 4–5.5 µA charging
  current, and check that normal startup does not trip the fault timer.
- Replace the 10-pin RPW land with the exact 24-pin RHF package and exposed pad.
  TPS26601 is not the HTSSOP variant. Check the manufacturer's actual drawing.
- Connect both input pins 8/9 and both output pins 23/24. Connect GND 17 to the
  module force return. Keep RTN 15 and the exposed pad on a **separate local
  internal-reference net**; connect support components to RTN. The manufacturer
  explicitly warns that shorting RTN to GND defeats reverse-polarity protection
  and can damage the device during reverse input.
- MODE 13 stays open; SHDN 14 has its own internal bias and requires a reviewed
  enable/reset policy. FLT 22 and IMON 18 may be left open if unused. UVLO 10,
  OVP 12, ILIM 19 and dVdT 20 need the revised passive network.
- Retain the system return star, upstream P03 source, separate module primary
  return and the original isolated secondary references. Correct the long
  net-tie symbol pin names and hide long PCB value text in the new cell.
- Review whether one common timed protector adequately contains each module
  fault or whether separate module protection is required. The recommended
  250 mA slow fuse per module is not identical to a shared electronic limit.

This comparison is an implementation decision, not an adopted native revision
or fabrication release. No parts were ordered and no supplier was contacted.
