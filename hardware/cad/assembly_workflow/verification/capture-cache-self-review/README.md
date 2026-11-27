# Capture cache self-review

The first capture-selector cache condition checked whether the requested path appeared anywhere in the prior source-hash map. Selecting a PCB/source file as the capture could therefore return a prior valid result without parsing the invalid capture.

The corrected bridge records an explicit `mechanical_capture` identity and requires an exact match before cache reuse. A regression requests a bound PCB file as the capture and proves it reaches validation rather than inheriting the old success. Existing capture-switch and unchanged-input cache tests remain. The pre-fix runtime source is retained to interpret earlier native evidence; the final selected assembly is rechecked with the corrected runtime.
