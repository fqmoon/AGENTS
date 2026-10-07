#!/usr/bin/env python3
"""Merge common and platform-specific AGENTS instructions."""

import argparse
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", help="platform name, e.g. wsl2")
    parser.add_argument("output_dir", help="output directory (required)")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.platform):
        parser.error("platform must contain only letters, digits, underscores or hyphens")

    root = Path(__file__).resolve().parent
    try:
        common = (root / "AGENTS.md").read_text(encoding="utf-8")
        platform = (root / f"AGENTS-{args.platform}.md").read_text(encoding="utf-8")
        merged = common.rstrip() + "\n\n" + platform.strip() + "\n"
        output = Path(args.output_dir).expanduser() / "AGENTS.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(merged, encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        parser.exit(1, f"error: {exc}\n")

    print(f"Merged instructions written to {output}")


if __name__ == "__main__":
    main()
