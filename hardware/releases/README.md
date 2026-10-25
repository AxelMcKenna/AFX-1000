# Hardware review artifacts

Review ZIPs and packaged firmware live outside the source tree in `build/artifacts/releases/`. The [manifest](manifest.json) records their original path, exact size, SHA-256 and, where available, the original Git blob. Existing local files were moved without changing their bytes. No release was uploaded during the folder reorganisation.

From the repository root:

```sh
python3 tools/artifacts/restore.py --list
python3 tools/artifacts/restore.py --verify
python3 tools/artifacts/restore.py --name standalone-review-A04-E18.zip
```

The restore command reads historical Git objects to restore a missing archived artifact. A shallow clone may need its history fetched first. Artifacts marked **local only** were uncommitted review bundles; they require the retained local copy or a separately published release asset. The command never overwrites a mismatching file. ZIP contents preserve the folder layout of their original snapshot.

Future release bundles should be published as versioned release assets with checksums; build outputs stay under `build/artifacts/`. Editable KiCad/OpenSCAD sources, small verification records and selected documentation previews stay tracked. Historical verification records retain their original source paths and hashes.

<a id="button-fit-kit"></a>

## `button-fit-kit.zip`

- Local path: `build/artifacts/releases/button-fit-kit.zip`
- Size: 180,066 bytes
- SHA-256: `b5c2cde89d10b583388f100967cc3046f8f7c44814bf4e92c11e426a8c4406b7`
- Recovery: Git blob `4f0b2ae9793796e45c2ed1d542b83364b2958aae`

<a id="main-power-placement-review-e24"></a>

## `main-power-placement-review-E24.zip`

- Local path: `build/artifacts/releases/main-power-placement-review-E24.zip`
- Size: 4,566,657 bytes
- SHA-256: `0b78ab43d736a7b294a4702ccac1588f59b5ef3feb3fd616ab2107e49603fd98`
- Recovery: local only; retained copy at `/private/tmp/rmx-standalone-recovery/main-power-placement-review-E24.zip`
- Scope: 157-part main-supply placement, four holes, checked inductor lands and passive candidates; zero nonrouting DRC/parity issues and 333 open connections. Twenty-six tooling tests; fresh E14/E16/E17/E20 circuit/interface checks. A07 CAD and earlier routed boards preserved. No copper routing, new firmware build, mechanical render or physical qualification; not a fabrication or assembly release.

<a id="input-and-housing-review-a07-e23"></a>

## `input-and-housing-review-A07-E23.zip`

- Local path: `build/artifacts/releases/input-and-housing-review-A07-E23.zip`
- Size: 5,117,368 bytes
- SHA-256: `c114f5947871568d0d9f4d6d3393d879f67a12b152a080f3c831c7c47eddf471`
- Recovery: local only; retained copy at `/private/tmp/rmx-standalone-recovery/input-and-housing-review-A07-E23.zip`
- Scope: E23 input PCB with profile reliefs and rear-edge components; A07 matched mounts, inlet/switch apertures and housing placement. Zero native ERC/DRC/parity/open items; 690 modeled reserves, seven closed solids and lever/board checks pass; 24 tooling tests. No new firmware build or physical qualification. Remaining boards, wiring, storage and physical power/audio/assembly tests remain open; not a fabrication or assembly release.

<a id="input-protection-review-e22"></a>

## `input-protection-review-E22.zip`

- Local path: `build/artifacts/releases/input-protection-review-E22.zip`
- Size: 4,195,154 bytes
- SHA-256: `b7815be848117ec60ff70b32615e8ba102228a1ae5b0b0f34ad05439a952a917`
- Recovery: local only; retained copy at `/private/tmp/rmx-standalone-recovery/input-protection-review-E22.zip`
- Scope: routed 48-part input/protection PCB; zero native DRC/parity/open items, 22 tooling tests and refreshed E14/E16/E17/E20 circuit/interface checks. No new firmware build or mechanical render. Housing integration, current/thermal and physical protection qualification remain open; not a fabrication or assembly release.

<a id="led-and-housing-review-a06-e20"></a>

## `led-and-housing-review-A06-E20.zip`

- Local path: `build/artifacts/releases/led-and-housing-review-A06-E20.zip`
- Size: 6,010,271 bytes
- SHA-256: `36265e3dc3a2f5debb04d34b8f52d5ef2fa3008f6b9c3fddbb0419c65f7bc90e`
- Recovery: **local only**
- Scope: routed E20 driver, A06 modeled housing integration and F04 ARM/host source snapshot. Power allocation, remaining boards and physical qualification remain open; not build-ready.

<a id="power-load-review-e21"></a>

## `power-load-review-E21.zip`

- Local path: `build/artifacts/releases/power-load-review-E21.zip`
- Size: 4,765,469 bytes
- SHA-256: `e88f3755411a39dc68e55b0d41c178c0ec90db6c6f0b09327dfbc84a73f19a7e`
- Recovery: **local only**
- Scope: E21 candidate power-load/current/ramp/parallel-switch update and unchanged E20 native PCB recheck. Conditional screens pass; all-rail startup, loop, thermal, distribution, power PCB/layout and physical qualification remain open. No new firmware build claim; not build-ready.

<a id="processor-and-housing-review-a05-e19"></a>

## `processor-and-housing-review-A05-E19.zip`

- Local path: `build/artifacts/releases/processor-and-housing-review-A05-E19.zip`
- Size: 2,150,425 bytes
- SHA-256: `f624539eb20053fe7427f26b4071201506d9c9c09a46a766dc4302262c0dd1f9`
- Recovery: **local only**

<a id="standalone-review-a03-e06"></a>

## `standalone-review-A03-E06.zip`

- Local path: `build/artifacts/releases/standalone-review-A03-E06.zip`
- Size: 1,442,475 bytes
- SHA-256: `b1182db7427e8255244c8507eb37c0d3cb3141ae21f0bcdb6562026c66d8bbcb`
- Recovery: Git blob `cba474f1c94d9eeda92608618db799cfdfac8585`

<a id="standalone-review-a03-e07"></a>

## `standalone-review-A03-E07.zip`

- Local path: `build/artifacts/releases/standalone-review-A03-E07.zip`
- Size: 1,528,274 bytes
- SHA-256: `78b53e8324945d01cc5681eaa507b24d2a339e043b4d167ceda51067b6f4775f`
- Recovery: Git blob `967b7e1816f454174c9ae2141f1c1a08c8ab19d1`

<a id="standalone-review-a04-e18"></a>

## `standalone-review-A04-E18.zip`

- Local path: `build/artifacts/releases/standalone-review-A04-E18.zip`
- Size: 13,643,102 bytes
- SHA-256: `0530c8c50cadeb0fcce3f6571417c8326f7c278109dcbb3bf27a434d135e0d05`
- Recovery: Git blob `f13b47dc6f160f4f78e71edac4b0e862f2444098`

<a id="standalone-review-e08"></a>

## `standalone-review-E08.zip`

- Local path: `build/artifacts/releases/standalone-review-E08.zip`
- Size: 1,771,779 bytes
- SHA-256: `559c6a5adf7b87a8cb10e6db41e5a4bdecd65f796838d605f03b4f3771df4e51`
- Recovery: Git blob `75e228659a31167a58a93406bf215f5b7983ad03`

<a id="standalone-review-e09"></a>

## `standalone-review-E09.zip`

- Local path: `build/artifacts/releases/standalone-review-E09.zip`
- Size: 2,100,782 bytes
- SHA-256: `1fd75ebd13928ce89586562c1f91b83af332b1886a38bf9a04a4fbb45d7ce173`
- Recovery: Git blob `669b6cf23f9308304a6a500f7a49cb6c5c6cb0f9`

<a id="standalone-review-e10"></a>

## `standalone-review-E10.zip`

- Local path: `build/artifacts/releases/standalone-review-E10.zip`
- Size: 10,016,899 bytes
- SHA-256: `2c7dcfec7b7acc2f09e1a28111d79b4cea5161e5aeaeb692ed58a80560d296d4`
- Recovery: Git blob `55cb153d553b5b34010979e172ad7b0ef9b0544d`

<a id="standalone-review-e11"></a>

## `standalone-review-E11.zip`

- Local path: `build/artifacts/releases/standalone-review-E11.zip`
- Size: 10,324,527 bytes
- SHA-256: `53cfbd4ac329d361067603776eb5dc90af3f3a948fff00d0f1928a8731f03367`
- Recovery: Git blob `5e524e121346a06791b317baacb929e4c125acaf`

<a id="standalone-review-e12"></a>

## `standalone-review-E12.zip`

- Local path: `build/artifacts/releases/standalone-review-E12.zip`
- Size: 10,648,765 bytes
- SHA-256: `3c492e3f934c5c26e2b9f266a4bc02fd87ee192e63c7c79a46a93e520c80a5a3`
- Recovery: Git blob `861948b388159b70fc9a7bd316bc2099042204f3`

<a id="standalone-review-e13"></a>

## `standalone-review-E13.zip`

- Local path: `build/artifacts/releases/standalone-review-E13.zip`
- Size: 11,394,981 bytes
- SHA-256: `e562c0ec72eb6af4c1bdf789b7955177ffe1e8e014b1a1d93a76e6ec8753122c`
- Recovery: Git blob `55f9148e6fb90458122808b37ab4b0a4b9151727`

<a id="standalone-review-e14"></a>

## `standalone-review-E14.zip`

- Local path: `build/artifacts/releases/standalone-review-E14.zip`
- Size: 12,002,969 bytes
- SHA-256: `2731a7eb23650d3a5ae4bf960b77135db02e0d40875149c1ab1b0984df857909`
- Recovery: Git blob `64b322ad06d1934a85223cb089f75301768b2e94`

<a id="standalone-review-e15"></a>

## `standalone-review-E15.zip`

- Local path: `build/artifacts/releases/standalone-review-E15.zip`
- Size: 12,239,206 bytes
- SHA-256: `476257894c1d24f371a6652d2fa202cbe874925da8e5d2686bbf0080fdffa12b`
- Recovery: Git blob `a68f91111e980197b8a6d0aa408d68ee21cdbf2f`

<a id="standalone-review-e16"></a>

## `standalone-review-E16.zip`

- Local path: `build/artifacts/releases/standalone-review-E16.zip`
- Size: 12,289,893 bytes
- SHA-256: `ef0208813c0a7d8dc61943c3eff253f916ff134adb0343b2cde73e61dfa30349`
- Recovery: Git blob `62b687408903401f7d62e973b485110ecaa55255`

<a id="standalone-review-e17-f04"></a>

## `standalone-review-E17-F04.zip`

- Local path: `build/artifacts/releases/standalone-review-E17-F04.zip`
- Size: 13,034,481 bytes
- SHA-256: `0e0e4557138e5b6b1f0b9b28d74affdafbcf2a50b921a68e77b4d46fed75561e`
- Recovery: Git blob `bc4fa2f75c636523a183ba6fe4c25abf8e1a8a1d`

<a id="standalone-review-e17"></a>

## `standalone-review-E17.zip`

- Local path: `build/artifacts/releases/standalone-review-E17.zip`
- Size: 13,022,277 bytes
- SHA-256: `2effeb8821c156f9c2bb1697ac668c0ded8b88d2e1498b16d85f5a832b306f71`
- Recovery: Git blob `6151b7771ab0e1b9780fe03ff0fa0ee394affbc9`

<a id="bypass-schematic-review"></a>

## `bypass-schematic-review.zip`

- Local path: `build/artifacts/releases/bypass-schematic-review.zip`
- Size: 197,071 bytes
- SHA-256: `5af8f05f4c3284cfc8cfeae1dbf23fdd1f42fbf24600fefcba644d87d2aab777`
- Recovery: Git blob `9e35e089c01acb09f9c5d9f168a9175a7fba8ee0`

<a id="bypass-review-e03"></a>

## `bypass-review-E03.zip`

- Local path: `build/artifacts/releases/bypass-review-E03.zip`
- Size: 288,431 bytes
- SHA-256: `39d7d4c60d26af5f6ae5a1eca85cba4aae5eac096e15426f758edbb69f8ce403`
- Recovery: Git blob `6adbf2f1def9c199b156a06a8903c27e6d1d8fff`

<a id="output-review-e05"></a>

## `output-review-E05.zip`

- Local path: `build/artifacts/releases/output-review-E05.zip`
- Size: 491,224 bytes
- SHA-256: `f5512ff231febbc96248954964387ca47d8ec84059c278f28c8e3555223edd4d`
- Recovery: Git blob `1471e112c7fb725e626b8cdddac1ea8495f3c906`

<a id="e18-firmware-external-bin"></a>

## `e18-firmware/external.bin`

- Local path: `build/artifacts/releases/e18-firmware/external.bin`
- Size: 139,764 bytes
- SHA-256: `1f3bb1a776ee19669c3b1763aa60bd2542106b6c10715340f948bd85e6637907`
- Recovery: Git blob `ac634fff3ab5700740d2fd50569660574d218051`

<a id="e18-firmware-onboard-bin"></a>

## `e18-firmware/onboard.bin`

- Local path: `build/artifacts/releases/e18-firmware/onboard.bin`
- Size: 139,084 bytes
- SHA-256: `e6126a7dcef84637558fd860f966ba4d2e5b23d801bad69c280673fa062b0541`
- Recovery: Git blob `985d6539cf83cf2502f4d5a9cd9e5f7e00944e13`
