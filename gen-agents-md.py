#!/usr/bin/env python3
"""Merge numbered AGENTS instruction fragments into a single AGENTS.md.

Input files are discovered next to this script.  A file participates in the
merge only when its name follows the convention

    NNN-name.md

where NNN is exactly three decimal digits and name is a non-empty identifier
made of letters, digits, underscores and hyphens.  Files that do not match are
ignored, and the scan never descends into subdirectories.

Digits carry two meanings:

* They define the merge order: files are concatenated by ascending number.
* They define mutual-exclusion groups: several files sharing one number are
  candidates for the same slot.  Use -s/--select to choose one, or omit the
  selection to use NNN-default.md when it exists.  Without a default, a group
  with several candidates requires a selection.  A single file is selected
  automatically.

The name "default" is reserved for automatic fallback within its own number;
it cannot be passed to -s.  An explicit selection replaces that group's default.
A default file may be empty when the group should contribute no text by default.

Selections name the fragment, not the number, so renumbering existing files or
adding a second candidate to a slot never invalidates an existing command.

Usage:

    python3 gen-agents-md.py OUTPUT_DIR [-s NAME ...]

Example, with the files 000-default.md, 010-windows.md, 010-wsl2.md,
020-tools.md, 030-default.md, 030-gpt.md and 030-cline.md:

    python3 gen-agents-md.py ./output -s wsl2
    python3 gen-agents-md.py ./output -s wsl2 -s gpt

The first command uses 030-default.md; the second replaces it with 030-gpt.md.

Exit status is 0 after the merge is written, and 1 when the input files cannot
be scanned, the selection is invalid or incomplete, or reading/writing fails.
All validation happens before the output file is touched, and the output is
replaced atomically, so a failing run never leaves a truncated AGENTS.md.
"""

import argparse
import os
from pathlib import Path
import re
import sys

FILE_NAME = "AGENTS.md"
FILE_PATTERN = re.compile(r"([0-9]{3})-([A-Za-z0-9][A-Za-z0-9_-]*)\.md")
NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


def discover(root):
    """Map each three-digit number to its candidates, ordered by number, name."""
    groups = {}
    for entry in root.iterdir():
        if not entry.is_file():
            continue
        match = FILE_PATTERN.fullmatch(entry.name)
        if match is None:
            continue
        groups.setdefault(match.group(1), []).append((match.group(2), entry))
    for members in groups.values():
        members.sort(key=lambda member: member[0])
    return dict(sorted(groups.items(), key=lambda group: int(group[0])))


def describe(members):
    return ", ".join(f"{name} ({path.name})" for name, path in members)


def resolve(groups, selections):
    """Validate selections and return ({number: path}, [error, ...]).

    A number with a single candidate is selected automatically.  For several
    candidates, an explicit selection overrides the default; without either,
    the group requires a selection.
    """
    errors = []
    located = {}
    for number, members in groups.items():
        for name, path in members:
            if name != "default":
                located.setdefault(name, []).append((number, path))

    unique = []
    reported = set()
    for name in selections:
        if name == "default":
            if name not in reported:
                reported.add(name)
                errors.append("'default' is reserved for automatic fallback; select a named alternative")
        elif NAME_PATTERN.fullmatch(name) is None:
            if name not in reported:
                reported.add(name)
                errors.append(f"invalid selection {name!r}: names match {NAME_PATTERN.pattern}")
        elif name in unique:
            if name not in reported:
                reported.add(name)
                errors.append(f"duplicate selection {name!r}")
        else:
            unique.append(name)

    picked = {}
    for name in unique:
        candidates = located.get(name)
        if not candidates:
            available = ", ".join(sorted(located)) or "none"
            errors.append(f"unknown selection {name!r}; available names: {available}")
            continue
        if len(candidates) > 1:
            where = ", ".join(f"{number} ({path.name})" for number, path in candidates)
            errors.append(f"ambiguous selection {name!r}: found under numbers {where}")
            continue
        number, path = candidates[0]
        picked.setdefault(number, []).append((name, path))

    chosen = {}
    for number, members in groups.items():
        selected = picked.get(number, [])
        if len(selected) > 1:
            errors.append(
                f"number {number} has {len(selected)} selections: "
                + ", ".join(name for name, _ in selected)
            )
        elif selected:
            chosen[number] = selected[0][1]
        elif len(members) == 1:
            chosen[number] = members[0][1]
        elif default := next((path for name, path in members if name == "default"), None):
            chosen[number] = default
        else:
            errors.append(
                f"number {number} has {len(members)} candidates; "
                f"select one with -s: {describe(members)}"
            )

    return chosen, errors


def render(paths):
    """Read every source in order and join them with a blank line between."""
    parts = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            parts.append(handle.read())
    return "\n\n".join(part.strip() for part in parts) + "\n"


def create_temporary(parent):
    """Open a fresh temporary file in `parent` and return (path, handle)."""
    for attempt in range(1, 101):
        candidate = parent / f".{FILE_NAME}-{os.getpid()}-{attempt}.tmp"
        try:
            return candidate, open(candidate, "x", encoding="utf-8")
        except FileExistsError:
            continue
    raise OSError(f"cannot create a temporary file in {parent}")


def write_atomic(path, text):
    """Write `text` to `path` via a temporary file and an atomic rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        mode = path.stat().st_mode & 0o777
    except FileNotFoundError:
        mode = None

    temporary, handle = create_temporary(path.parent)
    try:
        with handle:
            handle.write(text)
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def fail(errors):
    for message in errors:
        print(f"error: {message}", file=sys.stderr)
    return 1


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-s", "--select", action="append", default=[], metavar="NAME",
        help="fragment name to select instead of its group's default; required for groups "
        "with several candidates and no default; repeatable",
    )
    parser.add_argument("output_dir", help="output directory (required)")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parent

    try:
        groups = discover(root)
    except OSError as exc:
        return fail([f"cannot scan {root}: {exc}"])

    if not groups:
        return fail([f"no input files in {root}: expected files named NNN-name.md"])

    chosen, errors = resolve(groups, args.select)
    if errors:
        return fail(errors)

    paths = list(chosen.values())
    try:
        merged = render(paths)
    except (OSError, UnicodeError) as exc:
        return fail([f"cannot read input file: {exc}"])

    output = Path(args.output_dir).expanduser() / FILE_NAME
    try:
        write_atomic(output, merged)
    except OSError as exc:
        return fail([f"cannot write {output}: {exc}"])

    print(f"Merging {FILE_NAME}:")
    for index, path in enumerate(paths, start=1):
        print(f"  {index}. {path.name}")
    print()
    print(f"Written to: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
