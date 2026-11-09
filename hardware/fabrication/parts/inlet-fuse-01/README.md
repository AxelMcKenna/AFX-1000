# Inlet fuse correction

Checked 2026-11-06 against the [Littelfuse 451/453 datasheet](https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1), revision GD. 12/01/25, pages 2–4, and the manufacturer's [exact-part certificate](https://www.littelfuse.com/assetdocs/coc-rohs9-045106?assetguid=2b03f122-8ca7-4b0e-bd41-7240ebec4df5).

The earlier `0451006.MRL 6A 125V` is unsupported by the current table.
Select **045106.3MRL, 6.3 A, 125 V** for I_F1's existing 451/453 footprint.
Published cold resistance is nominal **9.6 mΩ**, measured at 25 °C and
10% rated current; melting I²t is nominal **9.17 A²s** at 8 ms. Neither is
a guaranteed hot operating or fault-clearing bound. Apply the stated 25%
continuous-current derating plus temperature rerating. The unchanged lands
are 1.96 × 3.15 mm, 2.95 mm inner gap. Body maxima are 6.30 × 2.94 × 2.94 mm.

At the provisional 4 A allocation, the cold-resistance estimate gives
38.4 mV and 153.6 mW. The 25 °C continuous allowance is 4.725 A; sustaining
4 A requires a temperature multiplier of at least 0.84656. This is a design
screen, not temperature or startup qualification. Current-limit operation
may exceed that allowance and must be time-bounded.

The fuse remains backup protection. Coordinate its actual time-current
behavior with the adapter, TVS, copper, jack and wiring. It cannot alone
enforce the jack's 5 A rating. Obtain the hot resistance, actual fuse ambient,
surge/repetition and fault-energy envelope before release. No package or
routing change is made here. Direct PDF download was blocked by the host;
the official PDF was read through the web tool. No local PDF or visual
inspection is claimed.
