#!/usr/bin/env python3
"""Generate repeatable probes and compare stereo captures using the Python stdlib.

Metrics are diagnostics, not an audio quality score. Never remove an effect's
delay by estimating alignment from its wet output. Calibrate using bypass first.
"""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import sys


def save_json(path, value):
    with Path(path).open("x") as f:
        f.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_wav(path, max_seconds=180):
    """Read mono/stereo RIFF PCM16/24/32 or float32, including extensible WAV."""
    with Path(path).open("rb") as f:
        header = f.read(12)
        if len(header) != 12 or header[:4] != b"RIFF" or header[8:] != b"WAVE":
            raise ValueError("Expected little-endian RIFF WAV")
        fmt = None
        data = None
        while True:
            chunk = f.read(8)
            if not chunk:
                break
            if len(chunk) != 8:
                raise ValueError("Truncated WAV chunk")
            kind, length = struct.unpack("<4sI", chunk)
            if length > 256 * 1024 * 1024:
                raise ValueError("WAV chunk exceeds 256 MiB limit")
            if kind == b"fmt ":
                fmt = f.read(length)
                if len(fmt) != length:
                    raise ValueError("Truncated WAV format")
            elif kind == b"data":
                data = f.read(length)
                if len(data) != length:
                    raise ValueError("Truncated WAV data")
            else:
                f.seek(length, 1)
            if length & 1:
                f.seek(1, 1)
    if fmt is None or len(fmt) < 16 or data is None:
        raise ValueError("Missing WAV format/data")
    encoding, channels, rate, _, align, bits = struct.unpack_from("<HHIIHH", fmt)
    if encoding == 0xFFFE:
        if len(fmt) < 40 or fmt[26:40] != bytes.fromhex("000000001000800000aa00389b71"):
            raise ValueError("Unsupported extensible WAV GUID")
        encoding = struct.unpack_from("<H", fmt, 24)[0]
    if channels not in (1, 2) or not 8000 <= rate <= 192000:
        raise ValueError("Expected mono/stereo WAV at 8-192 kHz")
    if (encoding, bits) not in ((1, 16), (1, 24), (1, 32), (3, 32)):
        raise ValueError("Expected PCM16/24/32 or float32 WAV")
    width = bits // 8
    if align != channels * width or len(data) % align:
        raise ValueError("Invalid WAV frame alignment")
    if len(data) // align > rate * max_seconds:
        raise ValueError("WAV exceeds duration limit")
    out = array("f")
    if bits == 24:
        values = (int.from_bytes(data[i:i + 3], "little", signed=True) / 8388608
                  for i in range(0, len(data), 3))
    else:
        code = "f" if encoding == 3 else ("h" if bits == 16 else "i")
        scale = 1 if encoding == 3 else 2 ** (bits - 1)
        values = (x[0] / scale for x in struct.iter_unpack("<" + code, data))
    for value in values:
        if not math.isfinite(value):
            raise ValueError("Non-finite WAV sample")
        out.append(value)
        if channels == 1:
            out.append(value)
    if not out:
        raise ValueError("Empty WAV")
    return rate, out


def write_wav(path, rate, samples):
    data = array("f", samples)
    if sys.byteorder != "little":
        data.byteswap()
    raw = data.tobytes()
    fmt = struct.pack("<HHIIHH", 3, 2, rate, rate * 8, 8, 32)
    Path(path).write_bytes(b"RIFF" + struct.pack("<I", 36 + len(raw)) + b"WAVEfmt "
                           + struct.pack("<I", 16) + fmt + b"data"
                           + struct.pack("<I", len(raw)) + raw)


def db(value):
    return 20 * math.log10(max(1e-15, abs(value)))


def envelope(samples, rate, window_ms=5):
    window = max(1, round(rate * window_ms / 1000)) * 2
    return [math.sqrt(sum(x * x for x in samples[i:i + window]) /
                      len(samples[i:i + window]))
            for i in range(0, len(samples), window)]


def band_levels(samples, rate):
    """RMS through fixed Q=1 octave-ish bandpasses. Not an FFT response curve."""
    result = {}
    for hz in (63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000):
        if hz >= rate * .45:
            continue
        omega = 2 * math.pi * hz / rate
        alpha = math.sin(omega) / 2
        a0 = 1 + alpha
        b0, b2 = alpha / a0, -alpha / a0
        a1, a2 = -2 * math.cos(omega) / a0, (1 - alpha) / a0
        x1 = [0., 0.]
        x2 = [0., 0.]
        y1 = [0., 0.]
        y2 = [0., 0.]
        energy = 0.
        for i, x in enumerate(samples):
            c = i & 1
            y = b0 * x + b2 * x2[c] - a1 * y1[c] - a2 * y2[c]
            energy += y * y
            x2[c], x1[c], y2[c], y1[c] = x1[c], x, y1[c], y
        result[str(hz)] = db(math.sqrt(energy / len(samples)))
    return result


def decay_t20(env, step_seconds):
    """Fit Schroeder -5 to -25 dB decay, rejecting short or non-decaying tails."""
    energy = [x * x for x in env]
    total = sum(energy)
    if total < 1e-20:
        return None
    integrated = []
    remaining = total
    for e in energy:
        integrated.append(10 * math.log10(max(1e-30, remaining / total)))
        remaining = max(0., remaining - e)
    points = [(i * step_seconds, y) for i, y in enumerate(integrated) if -25 <= y <= -5]
    if len(points) < 10:
        return None
    xs, ys = zip(*points)
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    xx = sum((x - mx) ** 2 for x in xs)
    yy = sum((y - my) ** 2 for y in ys)
    xy = sum((x - mx) * (y - my) for x, y in points)
    if xx <= 0 or yy <= 0 or xy >= 0:
        return None
    r2 = xy * xy / (xx * yy)
    return {"extrapolated_rt60_seconds": -60 * xx / xy, "fit_r_squared": r2,
            "valid_for_decaying_impulse_only": True}


def describe(samples, rate, include_bands=True):
    n = len(samples) // 2
    left = sum(samples[i] ** 2 for i in range(0, len(samples), 2))
    right = sum(samples[i] ** 2 for i in range(1, len(samples), 2))
    cross = sum(samples[i] * samples[i + 1] for i in range(0, len(samples), 2))
    env = envelope(samples, rate)
    step_seconds = round(rate * .005) / rate
    threshold = max(env) * .01
    active = [i for i, x in enumerate(env) if x > max(threshold, 1e-7)]
    result = {"frames": n, "duration_seconds": n / rate,
              "peak_dbfs": db(max(abs(x) for x in samples)),
              "rms_dbfs": db(math.sqrt((left + right) / (2 * n))),
              "dc_left": sum(samples[0::2]) / n, "dc_right": sum(samples[1::2]) / n,
              "samples_at_or_above_unity": sum(abs(x) >= 1 for x in samples),
              "left_right_level_db": db(math.sqrt(left / right)) if left * right > 0 else None,
              "stereo_correlation": cross / math.sqrt(left * right) if left * right > 0 else None,
              "onset_seconds_5ms": active[0] * step_seconds if active else None,
              "last_active_seconds_5ms": (active[-1] + 1) * step_seconds if active else None}
    # A short list of separated local maxima makes echo onset spacing visible.
    peaks = [i for i in range(1, len(env) - 1)
             if env[i] > max(threshold, 1e-7) and env[i] > env[i - 1] and env[i] >= env[i + 1]]
    selected = []
    for i in sorted(peaks, key=lambda x: env[x], reverse=True):
        if all(abs(i - previous) * step_seconds >= .025 for previous in selected):
            selected.append(i)
            if len(selected) == 32:
                break
    result["separated_envelope_peaks_seconds_5ms"] = [i * step_seconds for i in sorted(selected)]
    if include_bands:
        result["bandpass_rms_dbfs"] = band_levels(samples, rate)
    return result


def compare(reference, candidate, rate, shift_frames=0, tail_start=None, bands=True):
    # Positive means the candidate arrives later. Only trim latency established
    # by a separate bypass capture; never search wet audio for best similarity.
    r0, c0 = max(0, -shift_frames) * 2, max(0, shift_frames) * 2
    length = min(len(reference) - r0, len(candidate) - c0)
    if length < rate // 10 * 2:
        raise ValueError("Need at least 100 ms overlapping audio after alignment")
    ref, cand = reference[r0:r0 + length], candidate[c0:c0 + length]
    rr = sum(x * x for x in ref)
    cc = sum(x * x for x in cand)
    dot = sum(x * y for x, y in zip(ref, cand))
    gain = dot / cc if cc > 1e-30 else 0
    error = sum((x - y) ** 2 for x, y in zip(ref, cand))
    fitted = sum((x - gain * y) ** 2 for x, y in zip(ref, cand))
    a, b = envelope(ref, rate), envelope(cand, rate)
    result = {"alignment_candidate_delay_frames": shift_frames,
              "overlap_frames": length // 2,
              "uncompared_reference_frames": (len(reference) - length) // 2,
              "uncompared_candidate_frames": (len(candidate) - length) // 2,
              "reference": describe(ref, rate, bands), "candidate": describe(cand, rate, bands),
              "candidate_minus_reference_rms_db": db(math.sqrt(cc / rr)) if rr > 1e-30 else None,
              "sample_correlation": dot / math.sqrt(rr * cc) if rr * cc > 0 else None,
              "error_relative_to_reference_db": db(math.sqrt(error / rr)) if rr > 1e-30 else None,
              "diagnostic_candidate_gain_to_reference": gain if cc > 1e-30 else None,
              "gain_fitted_error_relative_db": db(math.sqrt(fitted / rr)) if rr > 1e-30 else None,
              "envelope_absolute_error_rms": math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a)),
              "limitations": ["No resampling or clock-drift correction is applied.",
                              "Null errors are not perceptual quality scores.",
                              "Bandpasses overlap and do not measure a transfer function."]}
    if tail_start is not None:
        if tail_start < 0 or tail_start * rate * 2 >= length:
            raise ValueError("Tail start must lie inside aligned overlap")
        start = round(tail_start * rate) * 2
        step_seconds = round(rate * .005) / rate
        result["tail_reference"] = decay_t20(envelope(ref[start:], rate), step_seconds)
        result["tail_candidate"] = decay_t20(envelope(cand[start:], rate), step_seconds)
    return result


def calibrate(reference, candidate, rate):
    """Impulse-only diagnostic: strongest per-channel peaks establish route delay."""
    frames_a, frames_b = len(reference) // 2, len(candidate) // 2
    a = [max(range(frames_a), key=lambda i: abs(reference[2 * i + ch])) for ch in (0, 1)]
    b = [max(range(frames_b), key=lambda i: abs(candidate[2 * i + ch])) for ch in (0, 1)]
    for samples, positions in ((reference, a), (candidate, b)):
        if any(abs(samples[2 * i + ch]) < 1e-5 for ch, i in enumerate(positions)):
            raise ValueError("Missing impulse in a calibration channel")
    # Fixture left/right peaks are four seconds apart. This guards against
    # accidentally calibrating a noise or music recording.
    if abs((a[1] - a[0]) / rate - 4) > .1 or abs((b[1] - b[0]) / rate - 4) > .1:
        raise ValueError("Calibration requires the generated impulses probe in bypass")
    delays = [y - x for x, y in zip(a, b)]
    agreement = abs(delays[0] - delays[1])
    return {"kind": "bypass-impulse-calibration", "verified": False,
            "candidate_delay_frames": round(sum(delays) / 2),
            "channel_delay_frames": delays, "channel_delay_disagreement_frames": agreement,
            "interval_change_ppm": ((b[1] - b[0]) / (a[1] - a[0]) - 1) * 1e6,
            "usable_integer_alignment": agreement <= 2,
            "note": "Confirm bypass, same routing, channel order and absence of drift before using. Peak timing includes converter filtering."}


def generate(directory, rate, duration=16):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise ValueError("Choose an empty session directory; existing captures and manifests are preserved")
    names = ("impulses", "sweep", "rhythm", "noise")
    stimulus = []
    for name in names:
        samples = array("f", [0]) * (duration * rate * 2)
        rng = random.Random(1000)
        phase = 0.
        for i in range(duration * rate):
            t = i / rate
            left = right = 0.
            if name == "impulses":
                left = .5 if i == rate * 2 else 0.
                right = .5 if i == rate * 6 else 0.
            elif name == "sweep" and 2 <= t < 10:
                elapsed = t - 2
                frequency = 30 * (min(18000, rate * .4) / 30) ** (elapsed / 8)
                phase += 2 * math.pi * frequency / rate
                fade = min(1., elapsed * 100, (10 - t) * 100)
                left = right = .125 * math.sin(phase) * fade
            elif name == "rhythm" and 2 <= t < 10:
                elapsed = (t - 2) % .5
                left = .25 * math.sin(2 * math.pi * 110 * elapsed) * math.exp(-elapsed * 60)
                right = .2 * math.sin(2 * math.pi * 440 * elapsed) * math.exp(-elapsed * 80)
            elif name == "noise" and 2 <= t < 10:
                fade = min(1., (t - 2) * 100, (10 - t) * 100)
                left = .125 * rng.uniform(-1, 1) * fade
                right = .125 * rng.uniform(-1, 1) * fade
            samples[2 * i], samples[2 * i + 1] = left, right
        path = directory / (name + ".wav")
        write_wav(path, rate, samples)
        stimulus.append({"id": name, "path": path.name, "sha256": sha256(path),
                         "rate": rate, "frames": duration * rate,
                         "active_seconds": [2, 6] if name == "impulses" else [2, 10]})
    common = {"input_gain": 0, "output_gain": 0, "wet_only": 0, "auto_tempo": 0,
              "quantize": 0, "tempo": 120, "scene_source": 0, "isolate_source": 0,
              "sample_source": 0, "sampler_mute": 1, "scene_on": 0, "isolate_on": 0,
              "scene_depth": .65, "scene_time": 3, "scene_resonance": .3}
    cases = [{"id": "neutral", "parameters": common.copy()}]
    scene_names = ["bpf-echo", "echo", "noise", "spiral-up", "reverb-up", "hpf-echo",
                   "lpf-echo", "crush-echo", "spiral-down", "reverb-down"]
    for i, name in enumerate(scene_names):
        cases.append({"id": name, "parameters": dict(common, scene_on=1, scene_type=i)})
    for band in ("low", "mid", "high"):
        for position, value in (("cut", -1), ("boost", 1)):
            cases.append({"id": "isolate-" + band + "-" + position,
                          "parameters": dict(common, isolate_mode=0, isolate_on=1, **{band: value})})
    for case in cases:
        case["preset"] = case["id"] + ".rmx"
        case["stimuli"] = list(names)
        case["hardware_controls"] = {"status": "not_captured",
            "note": "Document actual panel positions and firmware. Software parameter values alone do not establish hardware equivalence."}
        preset = "RMX_STATE 1\n" + "".join("param %s %s\n" % item for item in case["parameters"].items())
        (directory / case["preset"]).write_text(preset)
    manifest = {"schema_version": 1, "kind": "rmx-reference-session", "status": "awaiting_reference",
                "stimuli": stimulus, "cases": cases, "captures": [],
                "calibration": {"candidate_delay_frames": 0, "verified": False,
                    "note": "Measure bypass loopback through identical converters and route before comparing effects."},
                "limitations": ["No hardware reference audio is included.",
                    "Static presets do not exercise button transitions, release lever reset, sampler events or DAW automation.",
                    "Probes may truncate long tails; use --duration to extend silence for long feedback settings."]}
    save_json(directory / "manifest.json", manifest)
    return manifest


def render(args):
    path = Path(args.manifest).resolve()
    data = json.loads(path.read_text())
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    renderer = Path(args.renderer).resolve()
    results = []
    stimuli = {s["id"]: s for s in data["stimuli"]}
    selected = [case for case in data["cases"] if not args.case or case["id"] == args.case]
    destinations = [output / (case["id"] + "--" + name + ".wav")
                    for case in selected for name in case["stimuli"]]
    if (output / "render-report.json").exists() or any(p.exists() for p in destinations):
        raise ValueError("Choose a fresh render directory; existing audio and reports are preserved")
    for case in data["cases"]:
        if args.case and case["id"] != args.case:
            continue
        for name in case["stimuli"]:
            source = path.parent / stimuli[name]["path"]
            if sha256(source) != stimuli[name]["sha256"]:
                raise ValueError("Stimulus hash mismatch: " + str(source))
            destination = output / (case["id"] + "--" + name + ".wav")
            process = subprocess.run([str(renderer), str(source), str(destination),
                                      str(path.parent / case["preset"])],
                                     capture_output=True, text=True, timeout=args.timeout)
            if process.returncode:
                raise RuntimeError(process.stderr or process.stdout)
            results.append({"case": case["id"], "stimulus": name, "path": str(destination),
                            "sha256": sha256(destination),
                            "preset_sha256": sha256(path.parent / case["preset"])})
    if not results:
        raise ValueError("No cases selected")
    save_json(output / "render-report.json", {"renderer_sha256": sha256(renderer),
              "manifest_sha256": sha256(path), "results": results})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate_parser = sub.add_parser("generate", help="Create deterministic probes and capture plan")
    generate_parser.add_argument("directory")
    generate_parser.add_argument("--rate", type=int, choices=(44100, 48000, 88200, 96000), default=48000)
    generate_parser.add_argument("--duration", type=int, choices=range(16, 121), default=16, metavar="16..120")
    render_parser = sub.add_parser("render", help="Render manifest using existing rmx_render")
    render_parser.add_argument("manifest")
    render_parser.add_argument("output")
    render_parser.add_argument("--renderer", default="build/rmx_render")
    render_parser.add_argument("--case")
    render_parser.add_argument("--timeout", type=float, default=120)
    compare_parser = sub.add_parser("compare", help="Compare capture or rendered WAV files")
    compare_parser.add_argument("reference")
    compare_parser.add_argument("candidate")
    compare_parser.add_argument("--report", required=True)
    compare_parser.add_argument("--candidate-delay-frames", type=int, default=0)
    compare_parser.add_argument("--tail-start", type=float)
    compare_parser.add_argument("--skip-bands", action="store_true")
    calibration_parser = sub.add_parser("calibrate", help="Measure route delay from bypass impulse captures")
    calibration_parser.add_argument("reference")
    calibration_parser.add_argument("candidate")
    calibration_parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            generate(args.directory, args.rate, args.duration)
            print("Generated probes and manifest. Hardware references remain absent.")
        elif args.command == "render":
            render(args)
            print("Rendered selected cases. See render-report.json for hashes.")
        else:
            if Path(args.report).exists():
                raise ValueError("Report already exists; choose a new report path")
            rate_a, a = read_wav(args.reference)
            rate_b, b = read_wav(args.candidate)
            if rate_a != rate_b:
                raise ValueError("Sample rates differ; repeat capture at matching rates")
            if args.command == "calibrate":
                result = calibrate(a, b, rate_a)
            else:
                result = compare(a, b, rate_a, args.candidate_delay_frames, args.tail_start,
                                 not args.skip_bands)
            result["files"] = {"reference": {"path": args.reference, "sha256": sha256(args.reference)},
                               "candidate": {"path": args.candidate, "sha256": sha256(args.candidate)}}
            save_json(args.report, result)
            print("Wrote diagnostic comparison. No sonic parity verdict is assigned.")
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
