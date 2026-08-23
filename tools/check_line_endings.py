"""
Line-ending gate.

This exists because the CRLF bug was fixed once and then reintroduced within the
hour — by the fixing script itself. On Windows, `open(path, "w")` defaults to
`newline=None`, which silently translates every `\\n` back to `\\r\\n`. So any
tool that rewrites a file in text mode undoes the fix, and nothing complains
until GitHub Actions runs the workflow on Ubuntu and bash reports:

    $'\\r': command not found

A one-time fix to a problem the toolchain actively recreates is not a fix. This
runs in CI ahead of everything else so a CR can never reach a shell script again.

Only files whose line endings actually matter are checked: anything CI executes
or parses as a script.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Files where a stray CR changes behaviour rather than just looking untidy.
CHECKED_SUFFIXES = {".yml", ".yaml", ".sh", ".py"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv",
             "public.staging", "dist", "build"}


def offenders(root: Path) -> list[tuple[Path, int]]:
    out: list[tuple[Path, int]] = []
    for p in root.rglob("*"):
        if not p.is_file() or any(s in p.parts for s in SKIP_DIRS):
            continue
        if p.suffix.lower() not in CHECKED_SUFFIXES:
            continue
        # Count EVERY carriage return, not just CRLF pairs. A lone CR inside a
        # shell script is exactly as fatal, and the first version of this gate —
        # which checked only for CRLF — walked straight past one in its own
        # workflow file on its very first run.
        cr = p.read_bytes().count(b"\r")
        if cr:
            out.append((p, cr))
    return out


def main(root: str = ".") -> int:
    base = Path(root)
    bad = offenders(base)
    checked = sum(1 for p in base.rglob("*")
                  if p.is_file()
                  and p.suffix.lower() in CHECKED_SUFFIXES
                  and not any(s in p.parts for s in SKIP_DIRS))

    print(f"  checked {checked} executable/parsed files")
    if not bad:
        print("  RESULT: CLEAN — all LF")
        return 0

    print(f"  RESULT: BLOCKED — {len(bad)} file(s) contain carriage returns\n")
    for p, n in bad:
        print(f"    {p.as_posix()}   ({n} CR bytes)")
    print("\n  A CR inside a GitHub Actions `run:` block reaches bash as part of")
    print("  the command and fails with $'\\r': command not found.")
    print("  Fix with a BINARY rewrite (text mode on Windows re-adds CRLF):")
    print("    p.write_bytes(p.read_bytes().replace(b'\\r\\n', b'\\n'))")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
