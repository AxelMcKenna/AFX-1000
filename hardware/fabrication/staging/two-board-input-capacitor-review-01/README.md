# Buck capacitor selection and derating review

The [native-netlist calculation](review.json) records the actual U20/U23 parts.
No capacitor has been substituted or accepted by this review.

| Role | Current TDK selection | Nominal rating |
| --- | --- | --- |
| Each local input capacitor | C2012X7R1H225K125AC | 2.2 µF, 50 V, X7R, ±10% |
| Each high-frequency input capacitor | C1005X7R1H104K050BB | 100 nF, 50 V, X7R, ±10% |
| Each bulk input capacitor | C3225X7R1H226M250AC | 22 µF, 50 V, X7R, ±20% |
| Each output capacitor | C3225X7S1E476M250AC | 47 µF, 25 V, X7S, ±20% |

The [TPS543620 datasheet](https://www.ti.com/lit/ds/symlink/tps543620.pdf),
sections 9 and 10.1, specifies at least 4 µF effective local ceramic input
capacitance and recommends at least 2 µF at each VIN/PGND side.

Using a multiplicative budget of −10% initial tolerance and −15% dielectric
temperature change, a local 2.2 µF plus 100 nF pair has **1.7595 µF** before
DC-bias and aging losses. The old allocation of 1 µF effective per 2.2 µF part
therefore does not independently establish the per-side target. The complete
network includes two 22 µF capacitors per regulator; their actual topology,
effective capacitance and connection impedance must be evaluated before deciding
whether the smaller local parts need replacement. Nominal net-wide totals alone
do not establish a good local input loop.

A possible 0805 alternative is
[TDK C2012X7R1H475K125AC](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C2012X7R1H475K125AC),
4.7 µF/50 V/X7R/±10%. After the same initial/temperature allocation, its
3.5955 µF budget would need to retain at least **55.6251%** through the remaining
losses to provide 2 µF without crediting the high-frequency capacitor.
Its listed maximum body is 2.25 × 1.50 × 1.50 mm, so land, height and context
checks must accompany any substitution. **It has not been selected.**

Official characterization/model downloads returned HTTP 403; a distributor-mirror
download of TDK's document timed out. Web text exposed ratings and the statement
that characteristic graphs are reference data, but no numerical bias curve or
rendered graph was inspected. No operating-capacitance guarantee or graph-derived
margin is claimed. The initial [download record](sources/download-record.json)
preserves the failed official requests.

The output bank is four actual **25 V X7S** parts per regulator. Its nominal
188 µF becomes a **117.312–275.232 µF engineering allocation** when only initial
±20% and dielectric ±22% factors are combined. These are not full operating
limits: bias, aging, AC amplitude, assembly and stability remain to be assessed.
Do not substitute the older generic 16 V X7R description or its ±15% factor.

Before fabrication, establish an adequate input topology, documented component
and derating margins, ripple/inrush limits and an acceptable output stability
range. First-article measurements remain later acceptance work; this review
does not require an already-built board as evidence for ordering a prototype.
