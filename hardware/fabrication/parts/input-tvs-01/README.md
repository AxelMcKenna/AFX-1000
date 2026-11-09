# Input TVS source review

Manufacturer PDFs retrieved 2026-11-06:

- [Vishay SMBJ family](https://www.vishay.com/docs/88392/smbj.pdf), document
  88392, revision 09-Jan-2024; local [copy](smbj.pdf).
- [TI TPS2663](https://www.ti.com/lit/ds/symlink/tps2663.pdf), SLVSE94G,
  revised June 2024; local [copy](tps2663.pdf).

The existing SMBJ33CA-E3/52 is bidirectional. At the datasheet's 25 °C
conditions it has 33 V standoff, 36.7–40.6 V breakdown at 1 mA, and 53.3 V
maximum clamp at 11.3 A for the specified 10/1000 µs pulse. The family peak
power rating depends on pulse duration and initial temperature; its stated
test copper is 5 × 5 mm per terminal. The new layout's irregular copper and
via-connected planes do not establish equivalent thermal performance.

TPS2663 IN_SYS has −60/+67 V absolute limits; its positive 10 ms transient
rating at 25 °C is higher. Against the regular limits, the stated TVS clamp
leaves only 6.7 V negative and 13.7 V positive margin before interconnect
overshoot and temperature effects. These differences are a screening
calculation, not a surge rating. The −85 V IN_SYS-to-OUT transient constraint
and the external blocking FET also need checking with the charged output.

TI's layout guidance places transient protection near the protected device
with short connections. D101 is therefore moved beside Q101's input and
connected through short, broad back copper to both DC feed and return planes.
The part, package, pin nets and reverse-polarity circuit remain unchanged.

No surge amplitude, source impedance, repetition rate, temperature, adapter
fault energy or fuse-coordination envelope has been qualified. Verify those
limits and effective local capacitance before fabrication release. Do not
infer a whole-unit immunity class from the eFuse's product description or
the TVS's nominal peak power.
