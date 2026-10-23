# New Zealand prototype sourcing

Selection preference: parts obtainable through New Zealand suppliers. Checked 22 October 2026. Stock and prices are observations from the linked listings, not reserved inventory or delivery promises. A NZ storefront does not establish local warehouse stock.

## Compute board

Retain the **Daisy Seed with 64 MB external SDRAM and pre-soldered headers** as the current firmware target. [Synthesizer NZ lists it for NZ$89.99](https://synthesizer.nz/products/electro-smith-daisy-seed/), specifies 64 MB SDRAM, and marks it **Pre-order / Out of stock**. No arrival date is shown. The seller says pre-orders ship 1–2 days after arrival in NZ; this is not the lead time from placing an order. Confirm the actual board revision and 64 MB variant before purchase.

This is an identified NZ supplier, **not a verified buy-now local-stock option**. Procurement remains open until an acceptable delivery date or a compatible stocked alternative is established. No order has been placed.

The memory capacity is material: the current host allocation exercise peaks at 58,040,496 bytes during complete sample-bank replacement, within the firmware's 60 MiB arena. Firmware is cross-built for Seed, but has not run on a physical board. See [README](README.md#compute-and-memory) for the capacity and runtime limits.

[MindKits lists Teensy 4.1 for NZ$75.85 including GST](https://www.mindkits.co.nz/teensy-4-1.aspx), but the page shows a notification option rather than confirmed ready stock. It is not a substitute for this firmware: [PJRC specifies 1,024 KB onboard RAM and optional external memory](https://www.pjrc.com/store/teensy41.html). An alternative would require a complete memory-capacity check, audio hardware, a firmware adapter, pin reassignment and target timing validation. Do not reduce sampler capacity or omit effects to make a smaller board appear equivalent.

## Carrier candidates

These are sourcing leads for the A0.2 draft, not a fabrication release. Most control, analog and mechanical BOM entries still need exact part numbers and dimensions.

| Function | Candidate and supplier | Observed availability | Design consequence |
| --- | --- | --- | --- |
| Dry-bypass and input-mute relays, three required | [G5V-2 DC5, element14 NZ order 9949488](https://nz.element14.com/omron-electronic-components/g5v-2-dc5/relay-signal-dpdt-30vdc-2a/dp/9949488) | Listing reports 3,894 globally, **UK stock**, 3–5 business days; NZ$5.61 excluding GST each. Current listing identifies manufacturer as ARATAS while overview describes the Omron series; verify supplied manufacturer/datasheet before footprint selection. | 5 V, non-latching DPDT; listed 50 ohm coil means nominal 100 mA each, 300 mA for three. The A0.2 draft uses two output selectors and one stereo input mute. Driver, suppression and supply budget must match this exact variant. This is overseas dispatch through a NZ storefront. |
| Independent watchdog | **TPS3435AFACADDFRQ1**, [Mouser NZ](https://nz.mouser.com/en/ProductDetail/Texas-Instruments/TPS3435AFACADDFRQ1?qs=Imq1NPwxi779uAij93PjbA%3D%3D), [DigiKey NZ](https://www.digikey.co.nz/en/products/detail/texas-instruments/TPS3435AFACADDFRQ1/21298453) | Indexed listings report 3,294 / 3,551 respectively; single-unit pricing NZ$5.13 / NZ$5.08 excluding GST. Reconfirm stock/delivery before purchase. These are NZ storefronts, **overseas inventory**, not established local NZ stock. | Selected draft replaces unsuitable TPS3431. DDF pinout A and exact suffix matter. 49.995 ms nominal with the selected network; ±20% device timing plus capacitor tolerance. Native/physical qualification pending. |
| Two-stage heartbeat permission | **74LVC74APW,118**, [DigiKey NZ](https://www.digikey.co.nz/en/products/detail/nexperia-usa-inc/74LVC74APW-118/946696) | Indexed listing reports 1,687 and NZ$0.47 excluding GST; overseas stock through NZ storefront. Reconfirm at order time. | Dual flip-flop TSSOP14; both clocks/resets common; stage 1 feeds stage 2. Replaces the single-stage draft. |
| Watchdog timing capacitors | **C0805X103F5GACTU** ×2, [Mouser NZ](https://nz.mouser.com/en/ProductDetail/KEMET/C0805X103F5GACTU?qs=ds50AKTGxA%2FsnToP84oGpw%3D%3D); **C0603C101F5GACTU** ×1 | The 10nF indexed NZ listing reports stock; 100pF NZ availability still requires confirmation. No combined price/lead time asserted. | Manufacturer spec sheets verify C0G 1%, 50V, 0805/0603 respectively. The earlier TDK 100pF lead is NRND and is not selected. |


| 5 V digital/relay converter, one required | **TSR 2-2450**, [DigiKey NZ](https://www.digikey.co.nz/en/products/detail/traco-power/TSR-2-2450/9383726) | NZ storefront listing; cached stock/price must be reconfirmed with delivery at purchase. Local NZ inventory is not established. | 5 V / 2 A draft supply. Exact SIP footprint and full startup/temperature/current budget still require review. |
| Isolated raw analog converters, two required | **TMR 6-1215**, [DigiKey NZ](https://www.digikey.co.nz/en/products/detail/traco-power/TMR-6-1215/9345151) | Indexed listing reports 100, NZ$42.84 excluding GST / NZ$49.266 including GST each. Overseas stock via NZ storefront; not a local warehouse claim. | SINGLE 24 V / 250 mA modules, connected as separate positive/negative rails. Not a dual-output 15 V substitute. Post-regulate before the op-amp. |

The draft also selects **LME49860MAX/NOPB** (active tape-and-reel variant per [TI](https://www.ti.com/product/LME49860/part-details/LME49860MAX/NOPB)), **LT3012EDE#PBF** and **LT3015ET#PBF**. NZ stock/price/delivery for these exact variants has not been established. TI's order page currently shows the selected op-amp unavailable directly; active lifecycle status is not stock. The older MA tube variant must not silently replace the selected MAX orderable part. These remain procurement gaps.

Select switch/pot/display/jack parts from available NZ inventory before committing mounting holes, shaft heights or PCB placement. Use named part numbers and actual drawings for the spring lever, touch lens, connectors and power supply. The current panel and BOM retain generic envelopes and are not ready to fabricate.

## Procurement gates

- Confirm a 64 MB Seed delivery date; local pre-order does not meet immediate-stock availability.
- Freeze relay model, coil load, contact pinout and footprint together. Similar relay suffixes are not automatically interchangeable.
- Reconfirm selected watchdog stock, verify its DDF footprint and define maximum complete fault-to-dry latency separately from nominal timeout.
- Complete line-level analog and power design before buying the carrier BOM or cutting the enclosure.

No aggregate prototype cost is stated: audio conditioning, protection, rails, controls, PCB fabrication and enclosure parts are still unselected.
