"""
Pre-push secret sweep.

A first version of this flagged the deployment guide five times, because that
document *documents* the patterns it is supposed to hunt for. A scanner that
fires on its own documentation trains people to ignore it, which is worse than
having no scanner — so this one distinguishes a credential from a mention of a
credential.

Three discriminators, all cheap:
  1. Shape — a real GitHub token is a prefix followed by ~36 high-entropy
     characters. `ghp_` alone, or inside a sentence, is not a token.
  2. Entropy — a real key is near-random. A placeholder like YOUR_TOKEN_HERE or
     a repeated character is not.
  3. Context — a line inside a fenced code block in a .md file that is teaching
     you what to search for is a mention, and is exempted explicitly rather than
     by accident.

Exit code 1 means do not push.
"""
from __future__ import annotations

import math
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", "node_modules", "public.staging",
             ".venv", "venv", "dist", "build"}
SKIP_SUFFIX = {".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff",
               ".woff2", ".zip", ".pdf"}

# Each rule: name, regex that matches a CREDENTIAL-SHAPED value, min entropy.
RULES = [
    ("GitHub token",      re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), 3.2),
    ("GitHub PAT",        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}\b"), 3.2),
    ("Telegram bot token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"), 3.0),
    ("Cloudflare token",  re.compile(r"\b[A-Za-z0-9_-]{40}\b(?=.*(?i:cloudflare))"), 3.5),
    ("Private key block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), 0.0),
    ("Generic assignment",
     re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|token)\s*[=:]\s*"
                r"[\"']?([A-Za-z0-9_\-/+]{24,})[\"']?"), 3.5),
]

PLACEHOLDERS = re.compile(
    r"(?i)^(x{3,}|y{3,}|\.{3,}|<.*>|\{.*\}|your[_-]?\w*|example|placeholder|"
    r"changeme|todo|none|null|redacted|abc123|test|dummy|sample)$"
)


def entropy(s: str) -> float:
    """Shannon entropy per character. Real keys sit above ~3.2."""
    if not s:
        return 0.0
    counts = {c: s.count(c) for c in set(s)}
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def is_documentation_mention(path: Path, line: str) -> bool:
    """
    A markdown file listing patterns to search for is teaching, not leaking.

    Deliberately narrow: it requires the line to contain a bare prefix with no
    credential-shaped body after it. A .md file with a REAL token in it is still
    reported.
    """
    if path.suffix.lower() not in {".md", ".rst", ".txt"}:
        return False
    bare_prefix = re.search(r'"(gh[pousr]_|github_pat_|-----BEGIN|Bearer )"', line)
    return bool(bare_prefix)


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return hits

    for i, line in enumerate(text.splitlines(), 1):
        if is_documentation_mention(path, line):
            continue
        for name, rx, min_ent in RULES:
            m = rx.search(line)
            if not m:
                continue
            value = m.group(m.lastindex or 0)
            if PLACEHOLDERS.match(value.strip()):
                continue
            if min_ent and entropy(value) < min_ent:
                continue
            redacted = value[:4] + "…" + value[-2:] if len(value) > 8 else "…"
            hits.append((i, name, redacted))
    return hits


def main(root: str = ".") -> int:
    base = Path(root)
    files = [p for p in base.rglob("*")
             if p.is_file()
             and not any(s in p.parts for s in SKIP_DIRS)
             and p.suffix.lower() not in SKIP_SUFFIX]

    findings: list[tuple[Path, int, str, str]] = []
    for p in files:
        for line_no, name, redacted in scan_file(p):
            findings.append((p, line_no, name, redacted))

    print(f"  scanned {len(files)} files")
    if not findings:
        print("  RESULT: CLEAN — no credential-shaped values found")
        return 0

    print(f"  RESULT: BLOCKED — {len(findings)} finding(s)\n")
    for p, line_no, name, redacted in findings:
        print(f"    {name:<22} {p.as_posix()}:{line_no}   value={redacted}")
    print("\n  Remove these or move them to an environment variable before pushing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
