"""Consume one bounded native WAV at a time without restarting DSP state."""
import os
from pathlib import Path
import subprocess
import time


def windows(space, renderer, input_path, directory, program, count, sanitized=False):
    directory = Path(directory)
    env = os.environ | dict(ASAN_OPTIONS='halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    space.check()
    with subprocess.Popen(list(map(str, [renderer, input_path, directory, program])), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env) as process:
        try:
            for index in range(count):
                deadline = time.monotonic() + 1800
                while not (directory / f'{index}.ready').exists():
                    space.check()
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise ValueError('Native batch stopped before a complete window')
                    time.sleep(.2)
                space.check()
                wave = directory / f'{index}.wav'
                yield index, wave
                if wave.exists():
                    raise ValueError('Batch consumer did not delete its WAV')
                (directory / f'{index}.ack').touch(exist_ok=False)
            stdout, stderr = process.communicate(timeout=30)
            space.check()
            if process.returncode or stdout or sanitized and stderr or not (directory / 'complete').exists():
                raise ValueError('Invalid native batch completion: ' + stderr.decode(errors='replace')[-3000:])
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
