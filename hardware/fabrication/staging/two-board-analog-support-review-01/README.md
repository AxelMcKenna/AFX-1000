# Analog eFuse local support review

TBP44 is still the selected board. This review defines the next construction
work for U13, U14 and U32; it is not a completed routing checkpoint.

TI recommends nearby support parts, short local control returns, a quiet eFuse
ground island with a star connection to system ground, and low ILM parasitic
capacitance. See [TPS25948 Rev. D](https://www.ti.com/lit/ds/symlink/tps25948.pdf),
section 8.9.1. These requirements motivate regrouping the three ILM resistors,
DVDT resistor/capacitor pairs and enable pulldowns. Values and packages remain.

The existing analog pin-8, pin-2 and pin-4 grounds are open. Pulldown ground
ends are also open. The connected R98–C39 branch has 69 tracks and two vias;
it will be replaced with a short local connection. Three long enable-pulldown
branches will be replaced while preserving the remaining control-net groups.
[circuit-review.json](circuit-review.json) identifies the exact source objects
and required restorations. Input/output force copper, input bypass loops,
transients, current capacity and full installed fit still need completion.

The separate digital R104 pulldown return remains in the outstanding startup
work. No blanket PWR_AGND join is authorized by a matching net name: every new
quiet return must preserve the four existing digital islands and their stars.
