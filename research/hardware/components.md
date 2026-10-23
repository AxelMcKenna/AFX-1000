# Standalone prototype component selection

This is the working standalone BOM and fit basis. Selection does not establish
stock availability, final analog performance, or a fabrication-ready PCB. Buy
one fit/sample set before committing to the full control surface.

| Function | Qty | Working component | Fit / remaining decision |
| --- | ---: | --- | --- |
| Prototype audio processor and converters | 1 | Daisy Seed3 with 64 MB external SDRAM | Firmware/control bring-up platform; onboard TAC5242 is not approved for the reference-performance path after the E04 noise screen. 51 × 18 mm module; socket stack and MCU timing remain unverified. |
| Reference-performance converter candidate | 1 | ESS ES9292QPRO | Separate differential analog board; 7 × 7 mm QFN-48. Revision-0.1 datasheet reviewed. Procurement, loaded stages, clock/configuration driver, SAI2 pin reassignment and PCB remain open. See E04. |
| High-voltage analog candidate | Pending circuit | TI OPA2992D | Input buffer/master-driver candidate on proposed regulated ±19 V; voltage/noise screening only. No complete analog schematic, regulator or power BOM selected. |
| Low-voltage analog candidates | Pending circuit | TI OPA1612 / OPA1632 | Receiver/consumer driver and differential ADC-driver candidates. Separate lower-voltage rails required. Loaded filter, bias/current noise, stability and dissipation need circuit analysis. |
| Non-detent rotary controls | 6 | Bourns PTV09A-6020F-B103 candidate configuration | 10 kΩ linear, M9 threaded bushing, 20 mm flatted shaft. Verify exact ordering code and shaft/cap stack with supplier. |
| Center-detent rotary controls | 4 | Bourns PTV09A-6220F-B103 candidate configuration | Low, Mid, Hi and Pitch. Same mounting family; confirm center-detent option. |
| Momentary switches | 29 | Omron/ARATAS B3F-1000 | 6 × 6 mm body, 4.3 mm height, nominal 0.98 N. Separate LEDs and custom plungers/caps provide illumination and RMX-style shapes. Switch bodies/pins reserve 8 × 10 mm. |
| Default/User selector | 1 | C&K JS202011CQN | DPDT, two maintained positions. Use one pole for logic. Actuator cap and carrier height need a fit sample. |
| Release-mode selector | 1 | C&K JS203011SCQN | DP3T, three maintained positions. Model allows 13 × 8 mm including terminal reserve. Use a consistent custom carrier; do not substitute a right-angle variant. |
| BPM digits | 3 | Kingbright SA36-11YWA | Common anode, yellow, 7.5 × 14 × 8.5 mm per digit; total body 22.5 × 14. Pin length 4 mm requires space below the board. |
| Touch acquisition | 1 | Bela Trill Craft | 52 × 21 mm module; eight custom foil/PCB electrodes under a nonconductive X-Pad cover. Tune scan settings and test cover thickness, moisture rejection and latency. |
| Button/selector inputs | 3 in both profiles | Microchip MCP23017-E/SO at0x20/0x21/0x22 | F04 maps32 front inputs across14+14+4 valid inputs. GPA7/GPB7 are output-only under DS20001952D and remain unconnected. Third-chip GPB0..3 carry Scene9, Default/User and both Release endpoints. See [pin map](../../hardware/firmware/control-inputs.json); older two-chip wiring is incompatible. |
| External-profile rear/status inputs | Included in the three above | MCP23017-E/SO at0x22 GPA0..3 | Connection mode/bypass/ANALOG_OK/INPUT_READY stay on GPA0..3. F04 firmware verifies direction/pull-up/latch configuration. E18 now routes these inputs with ANALOG_OK47k,INPUT_READY270k and reset100k receiving pull-downs. J4 is external-profile only; physical qualification remains open. D0 codec-run shares all three expanders' reset line. |
| LED sinks | 4 | TI TLC5947DAPR | 96 PWM current-sink channels. Common-anode display and LED wiring are required. Current-setting resistors, brightness and thermal performance need bench validation. |
| Lever position | 1 | ams OSRAM AS5600-ASOM | Contactless angle sensor on a custom vertical PCB; magnet-presence status must be checked. Board placement is a reserve, not a routed sensor board. |
| Lever magnet | 1 | Ø6 × 2 mm diametrically magnetized disk | Exact supplier/grade to be chosen against the sensor field requirement. An axially magnetized disk is unsuitable. |
| Lever pivot | 1 set | Ø3 mm nonmagnetic shaft, collar, washers, M3 grub screw | Prototype bore is Ø3.2; tap the radial Ø2.5 pilot M3. Shaft retention, end play and printed journal wear require assembly testing. |
| Lever return | 1 | Extension spring, supplier part pending | Target eye spacing about 13.4 mm at rest and 18.2 mm pulled; ≤4 mm outside diameter. Spring force, hooks and anchor tolerances must be selected and tested. No spring force is claimed. |
| 1/4-inch line jacks | 4 | REAN NYS229, TS/unbalanced | 3/8-32 thread; Ø9.8 prototype mounting hole. Conservative Ø19 × 28 mm internal reserve includes contacts. Confirm insulating washers, panel thickness and cable exits. |
| RCA line connectors | 4 | Insulated panel RCA, exact part pending | Ø8.2 holes are interface reserves. Input RCA and TS alternatives must not connect two separate sources together. |
| Dry bypass / processing-input isolation | 2 | Omron/ARATAS G6K-2F-Y DC5 candidate | One DPDT selects dry/processed stereo output; one disconnects processing inputs when unpowered. 10 × 6.5 × 5.2 mm nominal body. Footprint, suppression, contact behavior and assembled fit remain open. |
| Line gain switching | 2 | G6K-2F-Y DC5 candidate | E05 assigns K3 to stereo output-driver selection; the stereo input-range relay remains open. E01 per-channel feedback shunts rejected. D9 remains low Master / high Send-Return. |
| Output coupling | 8 | WIMA MKS2C044701O00KSSD | Parallel pairs of 4.7 µF/63 V/10% film capacitors, nominal body 7.2 × 11 × 18 mm, pitch 5 mm. E07 footprint placement and A03 maximum case/seating reserves clear the modeled internals. Physical fit and remaining height qualifications are open. |
| Input range / preamplifier | 1 set | OPA1656ID, G6K-2F-Y DC5, two 1 µF/63 V WIMA MKS2 film caps and passives | E10 native 28-component circuit supplies loaded master attenuation before a low-voltage FET buffer. E11/F02 implement the independent input-precharge schematic/firmware. ADC driver, scale/noise closure, PCB/enclosure placement and physical timing/audio remain unfinished. Capacitor nominal body 7.2 × 5 × 10 mm, 5 mm pitch; final fit/leakage/pulse qualification open. |
| DAC I/V / receiver | 1 set | 4 × OPA1612AID + 1 × OPA1656ID | E08 native circuit uses ten amplifier units for I/V, common-mode feedback, differential receiving and post-coupling buffers. Uses ±12 V; raw converter scale, fault protection, noise closure and PCB/enclosure placement are unfinished. These counts exclude the E05 output drivers. |
| Receiver DC blocking | 2 | WIMA MKS2C042201K00KSSD | 2.2 µF/63 V/10% nonpolar PET, nominal 7.2 × 7.2 × 13 mm, 5 mm pitch. E08 parts have not been placed in the CAD. Fit, leakage at temperature and analog/codec settling qualification remain open. |
| External converter core | 1 | ESS ES9292QPRO | E09 native pin contract covers 49 pins. Nominal 7 × 7 mm 48-QFN; the public document lacks the referenced dimensioned land/EP drawing, so its footprint is unassigned. ADC/input circuit, raw scale and physical audio remain open; F02 configuration/qualification firmware has build/host checks only. |
| Converter oscillator | 1 | ECS-2520MVLC-245.7-BN-TR | 24.576 MHz, nominal 2.5 × 2.0 × 0.8 mm. Codec-master synchronous 48 kHz/32-bit stereo plan; loaded duty/jitter/SI unverified. Not placed in CAD. |
| Converter local analog regulators | 2 | TPS7A2033PDBVR / TPS7A2045PDBVR | E09 local 3.3 V/4.5 V from internal regulated 4.90–5.10 V. SOT-23-5; capacitor bias/ESR, reverse-current behavior and complete system power budget require qualification. |
| Converter reset / settling | 1 set | 3 × TPS389033DSET + 1 × TPS389001DSET, SN74HCS08DR, SN74LVC1G08DCKR | E09 qualifies three local rails, external analog-rail status and codec flags. Conditional timer minimum1.21 s; CT MPN/leakage/bias limits and physical startup/fault response remain open. |
| Output-board inserts | 4 | CNC Kitchen M2 × 3 | OD3.6, recommended Ø3.2 bore, minimum wall1.3. A03 uses Ø7.2 bosses with through bores and M2 × 4 board screws. Verify printed fit, insertion, floor stiffness and engagement. |
| Independent watchdog / fault latch | 1 set | TPS3431SDRBR + SN74LVC1G74DCTR + SN74HCS08DR | E02 native schematic uses a 150 pF C0G timing capacitor, Schmitt qualification and an edge-armed latch. Zero ERC issues; no routed board/bench proof. |
| Local rail supervisors | 2 | TPS3808G33DBVR / TPS3808G50DBVR | Monitor 3.3 V/5 V; CT open. Independent monitors for all four E05 analog rails (±19 V and ±12 V) remain unselected. |
| Relay coil drivers / clamps | 2 each | AO3400A + Littelfuse SMF9.0A candidate | Separate paired bypass/gain coil drivers. Gate resistors and drain clamps are in E02; energy, pulse voltage, release and physical fit remain unverified. |
| Rear hardware controls | 3 | Bypass, line-level mode and power; exact parts pending | Apertures and body depths are reserves. Power must be rated for inrush; bypass request must gate the relay independently of firmware. |
| Storage | 1 | microSD socket/card, exact part pending | Rear slot is near the processor to keep the SDMMC path short. ESD, detect, trace routing, sample limits and filesystem behavior remain open. |
| Service port | 1 | Panel USB-C extension, exact part pending | Short cable to the module; service/updates only. Reserved rectangle is not a selected connector footprint. |
| Power input | 1 candidate | External12V3A low-voltage DC adapter | E14 uses a protected10.5–13.2V boundary. Adapter, connector/polarity, reverse/inrush/eFuse protection and downstream OV disconnects remain unselected/unimplemented; not an ordering or fabrication approval. |

## LED channel budget

Reserve 25 button indicators (Scene 10, Isolate 4, sources 2, pads 4,
Quantize/Auto/Roll/Overdub/Hold 5), 40 meter segments, four bank indicators,
24 digit segments including decimal points, and three ring-color channels.
Total: **96 channels**, exactly four TLC5947 devices. Bank, Tap and nudge buttons
have no separate indicator channels in this revision.

A prototype current ceiling of approximately 3 mA per sink would bound all 96
channels to roughly 0.29 A before duty-cycle reduction. Ring optics may need
different emitter/current arrangements; the channel budget does not prove
uniform illumination. All unused channels must initialize off; BLANK must hold
the drivers off during reset. Final resistor values follow the manufacturer's
equation and measured brightness/thermal requirements.

## Sources checked

- [Daisy Seed3 documentation and technical assets](https://docs.daisy.audio/hardware/Seed3/)
- [Bourns PTV09 manufacturer drawings and ordering scheme](https://www.bourns.com/docs/product-datasheets/PTV09.pdf), especially PTV09A-6 and mounting hardware
- [B3F manufacturer datasheet](https://omronfs.omron.com/en_US/ecb/products/pdf/en-b3f.pdf)
- [C&K JS series manufacturer drawings](https://www.ckswitches.com/media/1422/js.pdf)
- [Kingbright SA36-11YWA drawing and common-anode pinout](https://www.kingbrightusa.com/images/catalog/SPEC/SA36-11YWA.pdf)
- [Trill Craft physical size](https://shop.bela.io/products/trill-craft) and [scan-time settings](https://learn.bela.io/using-trill/settings-and-sensitivity/)
- [MCP23017 DS20001952D, including output-only GPA7/GPB7 restriction](https://ww1.microchip.com/downloads/aemDocuments/documents/APID/ProductDocuments/DataSheets/MCP23017-Data-Sheet-DS20001952.pdf)
- [TLC5947 manufacturer specification](https://www.ti.com/product/TLC5947)
- [AS5600 manufacturer datasheet](https://look.ams-osram.com/m/7059eac7531a86fd/original/AS5600-DS000365.pdf)
- [REAN NYS229 manufacturer drawing](https://www.rean-connectors.com/media/14496/download/NYS229.pdf?v=1)
- [E01 audio, gain and independent bypass design basis with manufacturer sources](../../hardware/electronics/README.md)
- [E04 converter/line-stage screen and primary-source hashes](../../hardware/electronics/audio-sources.json)
- [CNC Kitchen insert dimensions and design guidelines](https://www.cnckitchen.com/s/CNCKitchen_Heat-Set-Insert-Dimensions-and-Design-Guidelines.pdf)

The touch design uses Trill rather than CAP1188: the latter's minimum specified
cycle is 35 ms, which is a poor starting point for this performance strip. See
[Microchip's cycle-timing application note](https://www.microchip.com/content/dam/mchp/documents/OTH/ApplicationNotes/ApplicationNotes/AN22.13-SampleandCycleTiming.pdf).

## Manufacturing approach

Prototype with a PETG/PA12 shell, a 2 mm aluminum top panel, separate printed
control carriers, and nonconductive optical/touch inserts. The full 334 mm body
needs a sufficiently large build volume or an outsourced print. The first print
should be the small fit coupon and release bracket/rotor, followed by a fitted
button/plunger sample. Full-width printing precedes neither those checks nor
the audio/power PCB layout.

Panel knobs use Ø9.3 clearances for M9 bushings. The supplied washer can reach
Ø16 at its tolerance limit; the small Ø16 caps may leave washer edges visible.
If the chosen caps need to hide all mounting hardware, enlarge those caps or
choose matching hardware after checking nearby finger clearance. Nut flats,
anti-rotation features and final thread engagement must be checked on samples.

The A03/E07 output subassembly has actual footprints and routed copper, with
zero native KiCad DRC/parity issues and open connections. Other carrier/control
shapes remain placement reserves. The component reserve check excludes wiring
and unmodeled features; it is separate from PCB design-rule checking. Three
remaining relays, the converter/input stages and final supply still need actual
placement. Input jacks also need a normalling/selection decision: the NYS229
candidate alone must not be used to tie two independent RCA/TS sources together.

The separate [B01 switch test PCB and mechanical kit](../../hardware/cad/BUTTON-FIT.md) now has
a routed passive test board. It does not replace the carrier/control-board
reserves above. Its extra return spring (OD ≤6, ID ≥5.4, free length near 4.5,
solid height ≤1.2 mm) and Ø3 × 2 mm compliant silicone contact are specification
targets with no selected supplier part or physical force evidence.

E11 replaces the E02/E03 driver/contact assemblies for the external converter
profile. Its55-component schematic adds LTC6994HS6-1#TRMPBF, an additional
SN74HCS08DR, SN74HCS86DR, AO3400A input driver and timing/passive parts.
Use its [BOM and timing allocations](../../hardware/electronics/sequenced_bypass/README.md);
exact passive MPNs, connector/harness parts and physical timing remain open.
Do not count or assemble the superseded relays twice.

The [E12 ADC driver](../../hardware/electronics/adc_driver/README.md) adds2×THS4551IDGKR,
1×OPA1656ID input-buffer dual,1×OPA4192ID reference/servo quad and2×LM7705MM/NOPB.
Its79-component native schematic preserves E10 input loading and uses
low-voltage raw ADC drivers. Exact passive selections,
actual ADC load/stability, protection, calibrated scale and complete weighted
noise remain open. No E12 board or full enclosure placement is complete.

The [E13 rail monitor](../../hardware/electronics/rail_monitor/README.md) adds 4×TLV1824IDR,
1×OPA4192ID, 1×REF5025EIDR (enhanced E grade), TPS3808G01DBVR,
TPS3808G33DBVR and 4×SN74LVC08APWR. Its 181-part schematic monitors all eight
main/digital/bias rails. Precision resistors require 0.01%, 5 ppm/°C parts and
a qualified total error budget. Exact passive MPNs, final connectors, board
layout and physical timing remain open. These monitors supply PRE_ANALOG_OK;
main power generation and overvoltage disconnects are still unfinished.

The [E14 supply](../../hardware/electronics/power_supply/README.md) now adds2×LT3471EDD#PBF,
2×TPS62933FDRLR (FCCM variant),2×LT3080IMS8E#PBF,1×LT3080IQ#PBF in DD-PAK,
2×LT3090IDD#PBF,1×REF5025EIDR,1×LT1634AIS8-2.5#PBF,1×OPA4192ID,
1×OPA2192ID,4×SS16-E3/61T and passives. Its155-component native schematic
generates the candidate raw/final rails and checks the original analog targets.
Shielded inductors, effective capacitors, precision resistor MPNs, production
connectors, protection/disconnects, integrated PCBs and physical qualification
remain open. No E14 parts are included in the current enclosure clearance claim.
