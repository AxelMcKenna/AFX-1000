"""Check project C++/Objective-C formatting, excluding SDKs and build products."""

import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formatter", default="clang-format")
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    files = sorted(
        str(path)
        for folder in ("include", "src", "tests", "tools", "hardware/firmware")
        for path in (root / folder).rglob("*")
        if path.suffix in (".h", ".cpp", ".mm")
        and not any(part.startswith("build") for part in path.relative_to(root).parts)
    )
    flags = ["-i"] if args.fix else ["--dry-run", "--Werror"]
    subprocess.run([args.formatter, *flags, *files], cwd=root, check=True)


if __name__ == "__main__":
    main()
