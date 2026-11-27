# TBH05 spring assembly candidate — current spring-verified-r2

Use the **replacement spring bracket and arm** from `spring-verified-r2`, together with the unchanged r3 sensor carrier/cap and TBH03 r5 bearing guard/shims. This supersedes the old spring-anchor arrangement for this candidate only. Do not mix the old arm with the new fixed anchor or vice versa.

The fixed eye rises from Z35.6 to **Z38.6**. The moving eye radius changes from 10 to **7.5 mm**. The spring lies outboard at **X327.5**, above the bearing. These changes make room for real retaining hardware; the original moving-eye height put a retaining nut into the guide, and the first lowered-eye arrangement put the spring into the hub. Both failed trials are retained and excluded.

`spring.scad` is sealed at SHA256 `087e3dbba7096beee54fcd21b2709ed99b14dc39fb680f05a53a0a99ade86782`. `spring-verified-r2/review.json` records fourteen empty clearance/preservation cases, four positive end-stop/loop-retention cases and two valid printable solids. The continuous rotor envelopes include 0.1 mm radial expansion and ±0.5 mm axial travel; bracket fit uses ±0.3 mm. Spring-to-rotor checks pair the conservative spring and individual rotor primitive hulls over each 1° interval, avoiding a misleading intersection between unrelated angles. Pivot, handle, magnet and shaft geometry are independently unchanged outside the declared spring-lug region.

## Selected spring candidate and expected feel

Select **Lee Spring LE 014A 01 M**, music wire, as the first-article candidate. The [manufacturer catalogue](https://www.leespring.co.uk/sites/default/files/2020-01/Lee_Spring_Catalogue_UK_Eng.pdf) lists nominal OD3.18 mm, wire0.36 mm, free length12.70 mm measured inside loops, rate0.350 N/mm, initial tension0.53 N, maximum load4.89 N and extended length25.15 mm. Confirm the current supplier drawing and availability before ordering; no purchase has been made. The catalogue's loop position is random. Receive only a sample whose loops fit the two parallel pins freely without twisting the spring or bending its loops; otherwise request a manufacturer-approved parallel-loop variant and rerun receiving. Do not treat random-loop stock as a guaranteed match.

`spring-force-model.json` / `spring_analysis.py` calculate **0.989 N at rest and 2.499 N at 35°**, giving 7.41–15.89 Nmm restoring torque. At a 24 mm handle radius this is approximately **0.309–0.662 N tangential hand force**, before friction, gravity or acceleration. This is a light-return prototype choice, not a measured replication of the original product's feel.

The force calculation uses inside-loop length **pin-center distance +2 mm**, because the loops bear on the outside surfaces of the Ø2 pins. Center spacing alone would underestimate extension and force. The new inside-loop length is14.010–18.324 mm. Do not use the prior r5 eye-spacing calculation for this assembly.

## Custom hardware receiving drawing

These are **custom specified parts**, not unnamed assumed stock. A machine shop may make the smooth headed pins and spacers; equivalents are accepted only after measurement to this drawing and fit checks. Use brass or another verified noncorroding, low-magnetic material for the pins/spacers. The music-wire spring itself must be included in magnetic-field/angle verification.

| Part | Qty | Manufacturing / receiving requirements |
|---|---:|---|
| Headed clevis pin |2|Smooth shaft Ø1.98–2.00 mm; under-head length17.0±0.1 mm; head OD≤3.8 mm and height≤1.6 mm. Cross-drill Ø0.60±0.03 mm perpendicular to shaft, center15.60±0.05 mm from under-head plane. Deburr and polish spring-bearing surface; no threaded bearing substitution.|
| Spacer |2|OD≤4.0 mm, ID2.20–2.30 mm, length8.15±0.03 mm, square burr-free ends.|
| Retaining washer |2|OD≤4.0 mm, ID2.10–2.20 mm, thickness0.40±0.03 mm.|
| Split pin |2|Nominal Ø0.5 mm, compatible with measured cross hole. Spread/bend positively after assembly, with all installed material inside X328.2..330, Yeye±3, Zeye±1.2 mm at nominal lever axial position. A starting6 mm length may require trimming/bending on the bench; the installed envelope is the acceptance requirement. Do not reuse a fatigued split pin.|
| Spring |1|Candidate above; measured body/loop OD≤3.28 mm, loops fit the smooth pins freely, no forced loop deformation.|

The metal parts have **no strength or fatigue qualification yet**. Avoid treating print geometry or low calculated force as proof of pin bending strength, printed-anchor durability, spring life or shock retention.

## Bench assembly and adjustment

1. Assemble with the entire lever unit removed from the case. Keep metal cutting/deburring debris away from boards. Print the replacement bracket and arm; retain r5 bearing cap, steel pivot and measured thrust shims. The new parts preserve the previous pivot assembly sequence and its endplay requirement.
2. Insert each clevis pin from −X through its corresponding Ø2.2 printed eye. The head seats at X313, and the smooth shaft extends toward +X. Do not drill the spring loop or force an undersized printed hole.
3. Slide the8.15 mm spacer onto each pin against the +X eye face at X319. Fit the spring's closed loops over the exposed smooth pin. Fit retaining washers, then split pins through the cross holes; bend the split pins so washers cannot pass them.
4. Measure the free space between each spacer outer face and retaining washer inner face. Accept **0.65–0.80 mm**, with the spring loop rotating freely and no pinch. The nominal modeled space is0.70 mm. Adjust washer/spacer length within receiving limits or reject the stack; do not tighten a nut onto a loop.
5. At centered lever endplay, measure the loop center within **X327.2..327.8**. With actual rotor axial movement≤±0.3 mm this stays inside the modeled spring reserve X327.5±0.6. Confirm both heads and split pins remain captured at the full measured axial movement.
6. Install the assembly with the r3 sensor carrier on the left mounting bolts. Check all hardware against the guide and bearing guard at every angle before closing the lid. Return must be free and repeatable throughout0–35°, including gentle release near home. Do not test stop strength by snapping the lever.
7. Measure force with a small force gauge at24 mm radius. Record rest/full-pull force and hysteresis. Verify sensor AGC/field status and angle with and without the spring to detect magnetic influence. Follow with cycling, wear and retention tests before functional release.

The split pin provides positive axial capture; it is not a friction-only retention scheme. The native positive controls show the spring ring is blocked by both the spacer and retaining washer. Printed holes, custom pin tolerance, loop orientation and physical force remain receiving/calibration gates.

## Integration

Use `spring_bracket_world()` and `translate([0,0,7.6]) lever_arm_spring(angle)` instead of the old bracket/arm. `spring_installed_envelope()` exposes the entire spring and hardware motion reserve; `spring_arm_sweep()` exposes the replacement moving arm. The r3 `tbh05_installed()` carrier assembly is unchanged.

The original r5/r6 archives remain unchanged. `mechanical-contract.json` retains the r3 carrier and original-anchor reference; this document and `spring-force-model.json` supersede its original spring section for the new assembly. Whole-unit hardware ordering, electrical qualification and physical acceptance are still outstanding.
