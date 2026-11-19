# ADC data at the codec header

A_R216, the 33 Ω ADC data resistor, rotated 180° around its existing center. Its header-side pad now faces A_J203 pin 4. A straight 2.894 mm trace connects them on B.Cu and avoids the PRE_ANALOG_OK via. The resistor body occupies the same envelope and clears the neighboring header envelope by 0.70 mm.

The In6.Cu header ground pour extends under the new trace. KiCad verifies full-width ground coverage beyond the plated pin clearance for ADC data, bit clock and word select. The pour contacts both header ground and the existing ground via. All other filled copper regions match the independently refilled parent.

The signal board has 133 open connections. The source side of A_R216 still awaits the codec footprint. Header timing and assembled signal integrity remain open.

[Route and reference](reference-review.json) · [Native connectivity](native-review.json) · [Resistor placement](component-placement.json) · [Paired placement](placement.json) · [DRC](drc.json) · [ERC](erc.json) · [Previous revision](../native-routes-08/README.md)
