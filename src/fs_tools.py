from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

# Helpers ---------------------------------------------------------------

def _expand_braces(pattern: str) -> List[str]:
    """
    Expand simple single-level brace patterns like **/*.{jsp,java,html}.
    If no braces, returns [pattern].
    """
    if "{" not in pattern or "}" not in pattern:
        return [pattern]
    pre, rest = pattern.split("{", 1)
    inner, post = rest.split("}", 1)
    parts = [p.strip() for p in inner.split(",") if p.strip()]
    return [f"{pre}{p}{post}" for p in parts]


def _iter_files(root: Path, pattern: str) -> Iterable[Path]:
    for p in root.rglob(pattern):
        if p.is_file():
            yield p


# Public API ------------------------------------------------------------

@dataclass
class ListFilesResult:
    count: int
    sample: List[str]


def list_files(
    root: Path,
    glob_pattern: str,
    sample_size: int = 10,
) -> ListFilesResult:
    paths: List[Path] = []
    for pat in _expand_braces(glob_pattern):
        paths.extend(_iter_files(root, pat))
    # Deduplicate and sort for stability
    uniq = sorted({str(p) for p in paths})
    return ListFilesResult(count=len(uniq), sample=uniq[:sample_size])


@dataclass
class GrepMatch:
    path: str
    line_no: int
    line: str


@dataclass
class GrepResult:
    total_matches: int
    files_with_matches: int
    sample: List[GrepMatch]


def grep(
    root: Path,
    regex: str,
    glob_pattern: str,
    max_matches: int = 20,
    flags: int = re.MULTILINE | re.DOTALL,
) -> GrepResult:
    """
    Search files matching glob_pattern for regex.
    - Supports multi-line patterns (DOTALL) and line-anchored patterns (MULTILINE).
    - Returns up to max_matches sample entries with file path, line number, and
      the line content containing the match (trimmed).
    """
    pat = re.compile(regex, flags)
    sample: List[GrepMatch] = []
    total = 0
    files = 0

    for file_path in {p for p in _iter_files(root, glob_pattern)}:
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        file_has = False
        for m in pat.finditer(text):
            total += 1
            if not file_has:
                files += 1
                file_has = True
            if len(sample) < max_matches:
                # Compute 1-based line number where match starts
                start = m.start()
                line_no = text.count("\n", 0, start) + 1
                # Extract the full line content containing the match
                ls = text.rfind("\n", 0, start) + 1
                le = text.find("\n", m.end())
                if le == -1:
                    le = len(text)
                line_txt = text[ls:le].strip()
                sample.append(GrepMatch(str(file_path), line_no, line_txt))
        # Continue to next file after scanning this one

    return GrepResult(
        total_matches=total,
        files_with_matches=files,
        sample=sample,
    )


@dataclass
class ReadFileResult:
    path: str
    size: int
    preview: str


def read_file(root: Path, path: str, max_chars: int = 20000) -> ReadFileResult:
    p = Path(path)
    if not p.is_absolute():
        p = (root / p).resolve()
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ReadFileResult(path=str(p), size=0, preview="")
    preview = text[:max_chars]
    return ReadFileResult(path=str(p), size=len(text), preview=preview)
