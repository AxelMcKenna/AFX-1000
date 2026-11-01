# RT01 supplier nominal R/T review

SEMITEC publishes a public legacy AT-series catalogue with a **203AT nominal
resistance/temperature table** on printed page13/PDF page2. The PDF/text are
captured under `sources/`; the table was visually checked. No vendor form or
personal information submission was used.

The nominal20 kΩ sensor is4.943 kΩ at60°C. The B25/85=4013 K approximation gives
4.863 kΩ, about1.615% lower. The beta-only temperature estimate therefore deserves
an explicit correction comparison. This supplier table is sparse nominal data;
it does not specify a complete manufacturing tolerance envelope or the error
between its10°C-spaced points.

`analysis.json` compares all19 published nominal points. A piecewise ln(R)
versus1/T interpolation, perturbed by the same conditional R25/beta/ADC/resistor
receiving corners, shifts the modeled186-code trip interval to approximately
**61.303–64.671°C**, versus the earlier60.871–64.266°C beta model. This is a
sensitivity comparison. Interpolation error, true local R/T tolerance, complete
ADC accuracy, sensor location/contact, thermal lag and temperature rise after
shutdown remain unbounded. No65°C assembled shutdown guarantee follows.

The existing FH01 firmware threshold and sealed FH02 circuit remain unchanged.
The older claim that a true continuous curve had not been obtained remains a
historical statement; this later packet adds a sparse supplier nominal table.
All physical, thermal and fabrication-release flags remain false.

```sh
.venv/bin/python -m hardware.qualification.boards.fan_health.rt_curve_review.analyze
.venv/bin/python -m hardware.qualification.boards.fan_health.rt_curve_review.test_curve
```
