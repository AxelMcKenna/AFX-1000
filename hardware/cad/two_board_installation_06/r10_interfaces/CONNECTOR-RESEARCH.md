# Connector selection research (not adopted geometry)

The four26-way LED headers can use a Molex C-Grid III candidate pair901310133 male /901420026 female with901192120 loose tin contacts. The manufacturer exact-part page confirms26circuits,dualrow2.54pitch,vertical,2.90mmPCBtail,tin male. The90142 manufacturer catalogue explicitly mates with90131 and uses90119. This is an unshrouded male: do not claim polarity protection or friction-lock retention from the female housing alone. Retention and insertion orientation require explicit project provisions. No substituted header or plugged envelope is yet approved in CAD or BOM.

Sources checked2026-11-12:
- https://www.molex.com/en-us/products/part-detail/901310133
- https://www.molex.com/en-us/products/part-detail/0901420026
- https://www.molex.com/en-us/products/part-detail/901420008 (samefamily mating compatibility)
- https://www.molex.com/en-us/products/series-chart/90119 (901192120:26–28AWG,insulationOD0.76–1.22mm,tin,bag)
- Manufacturer catalogue mirror: https://www.official.cz/static/_dokumenty/7/0/1/3/90142_Dual_Row.pdf

Alpha5853 is a compatible wire-diameter candidate:26AWG7/34silverplatedcopper,PTFE,OD0.039±0.004in =0.889..1.0922mm. Manufacturer bendradius10×OD gives minimum10.922mm using worstOD; plan11mm. DCR38ohm/1000ft nominal. https://www.alphawire.com/disteAPI/SpecPDF/DownloadProductSpecPdf?productPartNumber=5853 . This verifies contact insulation range, not crimp-tool qualification or full current/temperature acceptance.

Reject Harwin M20-1071300 as a new selection: manufacturer obsolescence notice13May2019 lists it. https://cdn.harwin.com/pdfs/Obsolescence_notification_2019-05-13_Harwin.pdf . A12+12 housing is not a26-circuit substitute. Harwin M20-9991346 is single-row13; correct dual-row male isM20-9981346, but absence of a current13+13 housing prevents adopting this exact pair.

Dimensional closure remains outstanding. C-Grid housing15.24mm height plus male-base mating stack may exceed old14.22mm generic boxes. Current sales drawing section dimensions need direct visual verification before assigning axes or modeling an exact plugged envelope. Several manufacturer/distributor downloads failed HTTP2/403/timeouts; no dimension has been silently guessed and no old generic envelope is promoted to manufacturer clearance evidence. The catalogue is marked reference only; current controlled drawing or actual receiving metrology is required for release.

Follow-on visual inspection succeeded for the manufacturer catalogue mirror. SHA256 9b92b5d2c37941a9139f2b46fa8fee634b3de7ceae48d964b4b6f477d1c0aeb7. Housing section confirms15.24axialheight; front view6.20maxbodywidth and7.72overallincluding asymmetric latch. Catalogue26way length33.17max,16way20.47max. These clarify axes but do not replace current controlled tolerances or establish seated axial stack. The female is therefore materially wider than old6.09generic boxes.
