# Audio routing

## Mac-only rekordbox test

On macOS 14.2 or later:

1. Open rekordbox and load a track.
2. Open the native RMX application and choose **File → Audio & MIDI setup** (`Cmd+,`).
3. Set input to **rekordbox — direct app capture** and output to **MacBook Pro Speakers**, headphones, or another physical output.
4. Start audio and allow audio capture if macOS asks. Start playback in rekordbox.
5. Check the input/output meters, start with neutral isolator controls, and enable one effect at a time.

The application creates a private, temporary Core Audio process tap and aggregate device. Only rekordbox is captured. While the tap is being read, the original application's direct playback is muted to avoid hearing a duplicate dry signal. Stopping RMX destroys the private route and restores normal playback.

This direct mixdown is intended for the Mac-only test. Do not assume it preserves separate cue/master channels when controller headphones are in use. The FLX routes below require their own acceptance test.

## FLX4 / FLX6 with an audio interface

`FLX MASTER RCA → stereo interface LINE inputs → RMX → interface outputs → speakers`

Keep headphones connected to the FLX for rekordbox cueing. In RMX choose the interface input and output pairs. Turn Wet Only off. Disable interface direct monitoring so only RMX feeds the speakers. FLX4 and FLX6 do not have an external send/return loop.

## FLX4 / FLX6 using BlackHole

Create a macOS aggregate device containing the controller and BlackHole 2ch. In rekordbox choose that aggregate and map master to BlackHole, headphones to the controller headphone channels. In RMX choose BlackHole as input and a physical speaker/interface output. Keep one consistent sample rate, with drift correction for secondary devices.

Never return RMX's output to its own BlackHole input. Do not send both the dry controller master and processed master to the same speakers. Channel labels and offsets must be checked on the attached controller; this configuration has not been tested on physical FLX hardware here.

## Other mixers

A physical send/return loop uses `mixer SEND → interface input → RMX → interface output → mixer RETURN`. Wet Only is for a parallel loop where the mixer retains the dry source. Leave it off for an insert that replaces the source.

The displayed I/O latency is calculated from device/buffer information. It is not a physical round-trip measurement. Software bypass still depends on the application and computer running.

When input and output use separate devices, RMX initially reserves two negotiated callback quanta plus interpolation headroom. Frame counts are converted to the input device's sample rate. An underrun increases the reserve by up to one additional quantum until the route restarts. At matching 48 kHz/128-frame settings the initial reserve is about 5.4 ms; device and callback latency are additional. Verify the latency/dropout tradeoff on the actual devices with a loopback test.
