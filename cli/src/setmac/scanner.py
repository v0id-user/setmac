"""Find secrets and personal data in dotfiles before they are captured or applied.

High findings (tokens, keys) always block. Medium findings (emails, home paths, local
hostnames, high-entropy strings) block unless the caller accepts them. Either can be
allowed for specific files with a `.setmac-scan-allow` file in the profile, one
`rule-id:path-glob` per line. Findings never include the full matched value.
"""

from __future__ import annotations

import fnmatch
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

HIGH = "high"
MEDIUM = "medium"


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    pattern: re.Pattern
    why: str


RULES = [
    Rule("github-token", HIGH, re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})"), "GitHub token"),
    Rule("api-key", HIGH, re.compile(r"\bsk-(ant-|proj-)?[A-Za-z0-9_-]{20,}"), "OpenAI or Anthropic style API key"),
    Rule("slack-token", HIGH, re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    Rule("aws-key", HIGH, re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    Rule("private-key", HIGH, re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY( BLOCK)?-----"), "private key"),
    Rule("jwt", HIGH, re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "JSON web token"),
    Rule("assigned-secret", HIGH,
         re.compile(r"(?i)\b(token|secret|password|passwd|api[_-]?key)\b\s*[=:]\s*['\"]?([^\s'\"#]{16,})"),
         "a secret assigned to a token/secret/password/api key setting"),
    Rule("email", MEDIUM, re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b"), "email address"),
    Rule("home-path", MEDIUM, re.compile(r"/Users/(?!Shared\b)[A-Za-z0-9._-]+"), "path inside a specific user's home"),
    Rule("local-host", MEDIUM, re.compile(r"\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:local|lan|internal)\b"), "local network host name"),
]

# Strings long and random enough to be a credential even without a known prefix.
CANDIDATE = re.compile(r"[A-Za-z0-9+/=_-]{24,}")


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    path: str
    line: int
    snippet: str
    why: str

    def describe(self) -> str:
        return (f"[{self.severity}] {self.rule} at {self.path}:{self.line}: {self.snippet} ({self.why}). "
                f"To allow it, add `{self.rule}:{self.path}` to .setmac-scan-allow")


def redact(value: str) -> str:
    """Enough to recognise the value, never enough to use it."""
    if len(value) <= 8:
        return "****"
    return value[:4] + "…" + f"({len(value)} chars)"


def _entropy(text: str) -> float:
    counts = Counter(text)
    return -sum(n / len(text) * math.log2(n / len(text)) for n in counts.values())


def _high_entropy(token: str) -> bool:
    classes = sum(bool(re.search(p, token)) for p in (r"[a-z]", r"[A-Z]", r"[0-9]"))
    return classes == 3 and _entropy(token) >= 4.0


def scan_text(text: str, path: str) -> list[Finding]:
    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        covered: list[tuple[int, int]] = []
        for rule in RULES:
            for match in rule.pattern.finditer(line):
                value = match.group(match.lastindex or 0) if rule.id == "assigned-secret" else match.group(0)
                findings.append(Finding(rule.id, rule.severity, path, number, redact(value), rule.why))
                covered.append(match.span())
        for match in CANDIDATE.finditer(line):
            inside = any(start <= match.start() and match.end() <= end for start, end in covered)
            if not inside and _high_entropy(match.group(0)):
                findings.append(Finding("high-entropy", MEDIUM, path, number, redact(match.group(0)),
                                        "long random-looking string, possibly a credential"))
    return findings


def _files(root: Path) -> list[Path]:
    if root.is_file() or root.is_symlink():
        return [root]
    return sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink())


def scan(path: Path, label: str) -> list[Finding]:
    """Scan a file or a directory. `label` is how paths are shown (and matched by allow globs)."""
    findings: list[Finding] = []
    for file in _files(path):
        shown = label if file == path else f"{label}/{file.relative_to(path).as_posix()}"
        try:
            text = file.read_text()
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable: nothing textual to leak
        findings += scan_text(text, shown)
    return findings


def load_allow(profile_root: Path | None) -> list[tuple[str, str]]:
    """`rule-id:path-glob` lines from the profile's .setmac-scan-allow."""
    if profile_root is None:
        return []
    try:
        lines = (profile_root / ".setmac-scan-allow").read_text().splitlines()
    except OSError:
        return []
    allowed = []
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if ":" in line:
            rule, glob = line.split(":", 1)
            allowed.append((rule.strip(), glob.strip()))
    return allowed


def blocking(findings: list[Finding], allow: list[tuple[str, str]], accept_medium: bool = False) -> list[Finding]:
    """Findings that stop the operation: not allowed by the allow file, and not an accepted medium."""
    def allowed(f: Finding) -> bool:
        return any(rule in (f.rule, "*") and fnmatch.fnmatch(f.path, glob) for rule, glob in allow)

    return [f for f in findings if not allowed(f) and (f.severity == HIGH or not accept_medium)]
