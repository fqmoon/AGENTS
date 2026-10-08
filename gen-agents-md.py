#!/usr/bin/env python3
"""Merge default and optional AGENTS instruction files."""

import argparse
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agents", nargs="*", help="additional AGENT keywords, e.g. wsl2 windows")
    parser.add_argument("output_dir", help="output directory (required)")
    args = parser.parse_args()

    for agent in args.agents:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", agent):
            parser.error(f"invalid AGENT keyword: {agent!r}")

    root = Path(__file__).resolve().parent
    try:
        sources = [root / "AGENTS.md"] + [root / f"AGENTS-{agent}.md" for agent in args.agents]
        merged = "\n\n".join(path.read_text(encoding="utf-8").strip() for path in sources) + "\n"
        output = Path(args.output_dir).expanduser() / "AGENTS.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(merged, encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        parser.exit(1, f"error: {exc}\n")

    print(f"Merged instructions written to {output}")


if __name__ == "__main__":
    main()
