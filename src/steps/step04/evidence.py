from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List, Optional, Tuple

from config.config import Config

from .models import Evidence


class EvidenceUtils:
    """Utility helpers for evidence: path normalization, sampling, and construction.
    Instance-based; requires Config.get_instance() to be initialized.
    """

    def __init__(self) -> None:
        # Require configuration to be initialized; let Config.get_instance() raise if not
        self.cfg = Config.get_instance()

    def _get_sampling_rate(self, default: float = 1.0) -> float:
        try:
            if not self.cfg:
                return default
            rate = float(getattr(self.cfg.provenance, "evidence_sampling_rate", default))
            if rate < 0.0:
                return 0.0
            if rate > 1.0:
                return 1.0
            return rate
        except Exception:  # pylint: disable=broad-except
            return default

    def _stable_hash_fraction(self, key: str) -> float:
        h = hashlib.md5(key.encode("utf-8")).hexdigest()
        # Take first 8 hex chars -> int -> scale to [0,1)
        val = int(h[:8], 16)
        return (val % 10_000_000) / 10_000_000.0

    def normalize_path(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return path
        p = str(path).replace("\\", "/")
        # Remove Windows drive like C:/ or D:/
        if len(p) >= 2 and p[1] == ":":
            p = p[2:]
        # Collapse duplicate slashes
        while "//" in p:
            p = p.replace("//", "/")
        # Best-effort project-relative using known roots
        try:
            if self.cfg is not None:
                roots: List[str] = []
                # Prefer instance values; fall back to class-level attributes if necessary
                for attr in ("project.source_path", "project.default_source_path", "projects_root_path", "code_sight_root_path"):
                    try:
                        root = None
                        if "." in attr:
                            obj_name, prop = attr.split(".", 1)
                            obj = getattr(self.cfg, obj_name, None)
                            root = getattr(obj, prop, None) if obj is not None else None
                        else:
                            inst_val = getattr(self.cfg, attr, None)
                            class_val = getattr(Config, attr, None) if Config is not None else None
                            root = inst_val or class_val
                        if root:
                            r = str(root).replace("\\", "/")
                            if len(r) >= 2 and r[1] == ":":
                                r = r[2:]
                            roots.append(r.rstrip("/"))
                    except Exception:  # pylint: disable=broad-except
                        continue
                for r in roots:
                    if p.startswith(r + "/"):
                        p = p[len(r):]
                        break
        except Exception:  # pylint: disable=broad-except
            pass
        # Ensure leading slash for consistency with tests using "/test/..."
        if not p.startswith("/"):
            p = "/" + p
        return p

    def build_evidence_from_source_ref(self, ref: Dict[str, Any]) -> Evidence:
        file_path = self.normalize_path(ref.get("file"))
        ev = Evidence(
            file=file_path,
            line=ref.get("line") or ref.get("start_line"),
            end_line=ref.get("end_line"),
            chunk_id=ref.get("chunk_id") or (ref.get("chunk_ids", [None]) or [None])[0],
            score=None,
        )
        return ev

    def build_evidence_from_file(self, path: Optional[str], line: Optional[int] = None, end_line: Optional[int] = None, chunk_id: Optional[str] = None) -> Evidence:
        return Evidence(
            file=self.normalize_path(path),
            line=line,
            end_line=end_line,
            chunk_id=chunk_id,
            score=None,
        )

    def maybe_sample_evidence(self, evidence: Iterable[Evidence], key: str) -> List[Evidence]:
        rate = self._get_sampling_rate(1.0)
        if rate >= 1.0:
            return list(evidence)
        if rate <= 0.0:
            return []
        result: List[Evidence] = []
        for ev in evidence:
            # Use relation key + normalized file to decide inclusion deterministically
            hkey = f"{key}|{ev.file or ''}|{ev.line or ''}|{ev.end_line or ''}|{ev.chunk_id or ''}"
            if self._stable_hash_fraction(hkey) < rate:
                result.append(ev)
        return result

    def dedupe_evidence(self, items: Iterable[Evidence]) -> List[Evidence]:
        seen: set[Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]] = set()
        out: List[Evidence] = []
        for ev in items:
            sig = (ev.file, ev.line, ev.end_line, ev.chunk_id)
            if sig in seen:
                continue
            seen.add(sig)
            out.append(ev)
        return out
