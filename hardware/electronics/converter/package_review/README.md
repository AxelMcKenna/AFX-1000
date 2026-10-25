# ES9292QPRO source and package gate

The [official ESS CODEC listing](https://www.esstech.com/products-overview/codecs/) still points to the [183-page v0.1 datasheet](https://www.esstech.com/wp-content/uploads/2026/08/ES9292_DS_v0.1.pdf). A fresh download matches the existing SHA-256 reference. PDF pinout, layout and ordering pages were visually reviewed using the PDF review workflow.

The audit checks all 49 pin identities and 45 firmware setting masks. Critical clock/format/qualifier values, reserved-bit preservation, GPIO output enabling and fully-ramped-up status are checked separately. Registers 63/64 are independent byte registers combined by the writer. Documentary consistency does not verify actual SAI timing or codec operation.

Package identity is supported; layout dimensions are not. Official resources and manufacturer-approved CAD searches did not locate the required ES9292QPRO drawing. The [ESS announcement](https://www.esstech.com/essnews/ess-technology-unveils-the-worlds-highest-performing-audio-codec-the-sabre-es9292pro-designed-for-uncompromising-performance-flexibility-and-precision-audio-signal-processing/) directs evaluation enquiries to representatives.

Required: revisioned pitch/terminal/tolerance, exposed-pad and thickness/standoff dimensions; recommended land/mask/paste/thermal-via guidance or manufacturer approval. No generic QFN is substituted. No vendor message was sent.

The existing seven-pin E12 J2 interface has one conductor per ADC polarity. Its header taps do not sense voltage at the ESS pins through that harness. The final hardware requires driver/codec co-location or a revised force/sense interface; a separate characterization board does not close this converter loop.

```sh
python3 -m hardware.electronics.converter.package_review.audit
python3 -m hardware.electronics.converter.package_review.audit --check
```
