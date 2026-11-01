# ESS data request ready for owner review

Status: **draft only; not sent**. No vendor response, drawing approval or sample availability is implied. The recipient is a proposed routing contact, not a confirmed New Zealand representative. ESS lists this contact under Singapore and Southeast Asia on its [sales offices page](https://www.esstech.com/sales-offices/); ESS also lists `sales@mouser.com` under USA.

Proposed recipient: `singapore@mouser.com`

Subject: ES9292QPRO package drawing and ADC interface data request - AFX-1000

Hello,

We are developing a standalone stereo audio effects unit and reviewing an ES9292QPRO converter with THS4551 differential ADC drivers. Could you route this request to the appropriate ESS application engineer or authorized representative for a New Zealand project?

We have the official ES9292PRO public datasheet, revision 0.1 (August 2026). We need the following before completing the native PCB layout and ADC interface verification:

1. The revisioned, dimensioned ES9292QPRO 7 mm x 7 mm, 48-QFN package outline: terminal pitch/width/length and tolerances, pin-1 orientation, exposed-pad size, body thickness and standoff.
2. Recommended PCB copper lands, solder mask, stencil/paste and exposed-pad thermal-via construction, or the process for ESS review of a proposed footprint. A CAD model is useful but must identify the applicable package/drawing revision.
3. Clarification of the ADC input impedance in Table 44: its units, whether it is per pin or differential, the DC equivalent/reference, input current bounds versus common mode and sample rate, and the switched-input model or recommended driver/RC network. A static resistor to ground can overload the common-mode control in a vendor driver macromodel; we need the applicable ESS model or limits.
4. Guaranteed ADC pin/reference behavior and injection limits with any supply absent, during CHIP_EN changes, and during power up/down. Please distinguish absolute-stress limits from operating/partial-power limits and advise on signal isolation/protection.
5. Access and ordering information for the ES9292PRO evaluation board, including its revisioned schematic/BOM/layout or driver reference design, errata and a suitable sample source.

Please identify any access terms before supplying restricted documents. We can keep manufacturer material outside the public project repository; we are requesting the data needed to verify the design, not permission to redistribute your documents.

Thank you,
Axel

## Data receipt review

Record the actual source, document revision, receipt date, file hash, applicable order code and any redistribution terms. Independently review dimension arrows and package orientation before assigning the footprint. Re-run the converter pin contract and ADC simulations with the applicable manufacturer input model. Receipt of a drawing does not establish physical assembly or electrical qualification.
