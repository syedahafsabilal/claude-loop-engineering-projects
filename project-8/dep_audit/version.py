"""Minimal semver-lite utilities used by the audit, maker and checker."""

import re
from dataclasses import dataclass

_VERSION_RE = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)\s*$")


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.major}.{self.minor}.{self.patch}"

    def as_tuple(self):
        return (self.major, self.minor, self.patch)


def parse_version(text: str) -> Version:
    if isinstance(text, Version):
        return text
    m = _VERSION_RE.match(text)
    if not m:
        raise ValueError(f"Invalid version string: {text!r}")
    return Version(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def compare_versions(a, b) -> int:
    """Return -1, 0 or 1 comparing a and b."""
    va, vb = parse_version(a).as_tuple(), parse_version(b).as_tuple()
    if va < vb:
        return -1
    if va > vb:
        return 1
    return 0


def bump_type(old, new) -> str:
    """Classify the change between two versions as major / minor / patch."""
    o, n = parse_version(old), parse_version(new)
    if n.major != o.major:
        return "major"
    if n.minor != o.minor:
        return "minor"
    return "patch"


_COMPARATOR_RE = re.compile(r"^(<=|>=|==|=|<|>)?\s*(.+)$")


def version_in_range(version, range_str: str) -> bool:
    """Return True if ``version`` satisfies every comma-separated comparator.

    Supported comparators: ``<``, ``<=``, ``>``, ``>=``, ``=``/``==``.
    Example: ``"<4.17.19,>=1.0.0"``.
    """
    ver = parse_version(version)
    for part in (p.strip() for p in range_str.split(",") if p.strip()):
        m = _COMPARATOR_RE.match(part)
        if not m:
            raise ValueError(f"Invalid comparator: {part!r}")
        op = m.group(1) or "="
        bound = parse_version(m.group(2))
        c = compare_versions(ver, bound)
        if op == "<" and not c < 0:
            return False
        if op == "<=" and not c <= 0:
            return False
        if op in ("=", "==") and not c == 0:
            return False
        if op == ">" and not c > 0:
            return False
        if op == ">=" and not c >= 0:
            return False
    return True
