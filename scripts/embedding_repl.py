#!/usr/bin/env python
"""
Simple interactive REPL for querying CodeSight Step03 embeddings from the command line.

Features:
- Load persisted FAISS index and metadata
- Query by free text (embeds on the fly) or by existing chunk id
- Optional filtering by chunk type and subdomain (and advanced :where)
- Adjustable top-k results
- Cluster browsing (:clusters, :cluster <id>)

Usage:
  python scripts/embedding_repl.py [--project <name>] [--threshold <float>] [--topk <int>]


Docs: see docs/STEP03_OUTPUTS_AND_SEARCH_API.md

Commands inside the REPL:
  :help                 Show help
  :exit | :quit | :q    Exit
  :topk N               Set number of results (default from config)
  :type X               Filter results by chunk type (method|class|jsp|config). Use :type any to clear
  :subdomains           List all subdomain names in the index
  :subdomain NAME       Restrict results to a subdomain (use :subdomain any to clear)
  :values KEY           List distinct values for a metadata key or field (e.g., subdomain_name)
  :where k=v            Set a filter (e.g., subdomain_name=Storm2, has_sql=true). Use :where clear to clear all
  :filters              Show active filters
  :stats                Show index statistics
  :clusters [N]         Compute and list N clusters (default 10)
  :cluster ID           Show details for a cluster ID from the last :clusters run
  :chunk CHUNK_ID       Query by an existing chunk id
  :show CHUNK_ID        Show details of a chunk
  Plain text            Queries similar chunks to the provided text
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

# Ensure project src is on sys.path when running as a script
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[1]  # codesight/
SRC_ROOT = PROJECT_ROOT / "src"
for p in (str(SRC_ROOT), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from config.config import Config  # noqa: E402
from domain.embedding_models import EmbeddingChunk, SearchFilters, SemanticCluster  # noqa: E402
from embeddings.embedding_generator import EmbeddingGenerator  # noqa: E402
from embeddings.faiss_manager import FaissManager  # noqa: E402


def print_banner(project: str) -> None:
    print("CodeSight Embeddings REPL (Step03)")
    print(f"Project: {project}")
    print("Type :help for commands, or enter free text to query similar code chunks.")


def print_help() -> None:
    print(
        "\nCommands:\n"
        "  :help                 Show this help\n"
        "  :exit | :quit | :q    Exit\n"
        "  :topk N               Set number of results (default from config)\n"
        "  :type X               Filter by chunk type (method|class|jsp|config). Use :type any to clear\n"
        "  :subdomains           List all subdomain names in the index\n"
        "  :subdomain NAME       Restrict results to a subdomain (use :subdomain any to clear)\n"
        "  :values KEY           List distinct values for a key (e.g., subdomain_name, source_directory_name)\n"
        "  :where k=v            Set a filter (e.g., subdomain_name=Storm2, has_sql=true). Use :where clear to clear all\n"
        "  :filters              Show active filters\n"
        "  :stats                Show index statistics\n"
        "  :clusters [N]         Compute and list N clusters (default 10)\n"
        "  :cluster ID           Show details for a cluster ID from the last :clusters run\n"
        "  :chunk CHUNK_ID       Query by existing chunk id from the index\n"
        "  :show CHUNK_ID        Show details for a chunk id\n"
        "  Plain text            Query by text (embedded on the fly)\n"
        "\nDocs: docs/STEP03_OUTPUTS_AND_SEARCH_API.md\n"
    )


def show_chunk(fm: FaissManager, chunk_id: str) -> None:
    chunk = fm._get_chunk_by_id(chunk_id)  # noqa: SLF001 (accessing a helper on purpose)
    if not chunk:
        print(f"Chunk not found: {chunk_id}")
        return
    info = {
        "chunk_id": chunk.chunk_id,
        "type": chunk.chunk_type,
        "source": chunk.source_path,
        "lines": f"{chunk.start_line}-{chunk.end_line}",
        "metadata_keys": list((chunk.metadata or {}).keys()),
        "has_embedding": bool(chunk.embedding is not None),
    }
    for k, v in info.items():
        print(f"  {k}: {v}")


def _list_values(fm: FaissManager, key: str) -> None:
    key = key.strip()
    values = set()
    key_lower = key.lower()
    for ch in fm.chunk_metadata.values():
        if key_lower == "chunk_type" or key_lower == "type":
            values.add(ch.chunk_type)
            continue
        if key_lower == "source_path":
            values.add(ch.source_path)
            continue
        # metadata-backed keys
        val = (ch.metadata or {}).get(key)
        if val is None and key_lower == "subdomain":
            val = (ch.metadata or {}).get("subdomain_name")
        if val is None and key_lower == "source_dir":
            val = (ch.metadata or {}).get("source_directory_name")
        if isinstance(val, list):
            for v in val:
                if isinstance(v, str):
                    values.add(v)
        elif isinstance(val, (str, int, float, bool)):
            values.add(str(val))
    vals = sorted(v for v in values if v is not None)
    print(f"{len(vals)} distinct values for '{key}':")
    for v in vals[:200]:
        print(f"  - {v}")
    if len(vals) > 200:
        print("  ... (truncated)")


def _apply_where(filters: SearchFilters, expr: str) -> Optional[str]:
    expr = expr.strip()
    if expr.lower() == "clear":
        # Reset all filters
        for f in (
            "chunk_type",
            "subdomain_name",
            "source_directory_name",
            "file_language",
            "file_type",
            "package_name",
            "class_name",
            "method_name",
            "stored_procedure_name",
            "entity_mapping_table",
            "file_path",
            "source_relative_path",
        ):
            setattr(filters, f, None)
        filters.has_sql = None
        return "filters cleared"
    if "=" not in expr:
        return "Usage: :where key=value (or :where clear)"
    key, val = [x.strip() for x in expr.split("=", 1)]
    if not key:
        return "Invalid key"
    # synonyms
    key_map = {
        "type": "chunk_type",
        "subdomain": "subdomain_name",
        "subdomain_name": "subdomain_name",
        "source_dir": "source_directory_name",
        "source_directory_name": "source_directory_name",
        "language": "file_language",
        "file_language": "file_language",
        "file_type": "file_type",
        "package": "package_name",
        "package_name": "package_name",
        "class": "class_name",
        "class_name": "class_name",
        "method": "method_name",
        "method_name": "method_name",
        "has_sql": "has_sql",
        "stored_procedure_name": "stored_procedure_name",
        "entity_mapping_table": "entity_mapping_table",
        "file_path": "file_path",
        "source_relative_path": "source_relative_path",
    }
    field = key_map.get(key.lower())
    if not field:
        return f"Unknown key '{key}'"
    if field == "has_sql":
        if val.lower() in ("true", "1", "yes", "y"):  # noqa: SIM103
            filters.has_sql = True
        elif val.lower() in ("false", "0", "no", "n"):
            filters.has_sql = False
        elif val.lower() in ("any", "*"):
            filters.has_sql = None
        else:
            return "has_sql must be true|false|any"
        return f"has_sql set to {filters.has_sql}"
    if val.lower() in ("any", "*"):
        setattr(filters, field, None)
        return f"{field} cleared"
    setattr(filters, field, val)
    return f"{field} set to '{val}'"


def handle_text_query(eg: EmbeddingGenerator, fm: FaissManager, text: str, k: int, filters: SearchFilters) -> None:
    # Create a transient query chunk with an embedding to satisfy generator cache if needed
    _ = EmbeddingChunk(
        chunk_id=f"query_{int(time.time()*1000)}",
        content=text,
        chunk_type="query",
        source_path="<query>",
        start_line=0,
        end_line=0,
        metadata={"mode": "text"},
    )
    hits = fm.search_text(text, top_k=k, filters=filters)
    print_hits(hits)


def handle_chunk_query(fm: FaissManager, chunk_id: str, k: int, filters: SearchFilters) -> None:
    hits = fm.search_chunk(chunk_id, top_k=k, filters=filters)
    if not hits:
        print("No results.")
        return
    print_hits(hits)


def print_hits(hits: list) -> None:
    if not hits:
        print("No results.")
        return
    print(f"\nResults: {len(hits)}")
    for i, hit in enumerate(hits, start=1):
        ch = hit.chunk
        sub = ((ch.metadata or {}).get("subdomain_name")) or "?"
        print(f"  {i:2d}. {ch.chunk_id}  score={hit.score:.3f}  type={ch.chunk_type}  subdomain={sub}  src={ch.source_path}")


def main() -> int:
    # CLI args
    parser = argparse.ArgumentParser(description="CodeSight Step03 Embeddings REPL")
    parser.add_argument("--project", dest="project", help="Project name (defaults to CODESIGHT_PROJECT env or ct-hr-storm-test)")
    parser.add_argument("--threshold", dest="threshold", type=float, help="Similarity threshold override (e.g., 0.7)")
    parser.add_argument("--topk", dest="topk", type=int, help="Default top-k override")
    args = parser.parse_args()

    project_name = args.project or os.environ.get("CODESIGHT_PROJECT") or "ct-hr-storm-test"

    # Initialize Config and components
    try:
        Config.initialize(project_name=project_name)
        _ = Config.get_instance()
    except Exception as e:  # pylint: disable=broad-except
        print(f"Failed to initialize Config: {e}")
        return 1

    eg = EmbeddingGenerator()
    fm = FaissManager()

    if args.threshold is not None:
        try:
            fm.similarity_threshold = float(args.threshold)
        except Exception:  # pylint: disable=broad-except
            pass

    if not fm.load_index_with_metadata():
        print("Failed to load FAISS index/metadata. Run Step03 first to build and save the index.")
        return 2

    # Defaults
    try:
        default_k = int(getattr(fm, "max_results", 10) or 10)
    except Exception:  # pylint: disable=broad-except
        default_k = 10
    k = args.topk if isinstance(args.topk, int) and args.topk > 0 else default_k
    filters = SearchFilters()

    # Cache for last computed clusters
    last_clusters: Dict[str, SemanticCluster] = {}

    print_banner(project_name)
    print(f"Loaded index with {len(fm.chunk_metadata)} chunks. Default top-k={k}.\n")

    while True:
        try:
            line = input("emb> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not line:
            continue

        if line in (":exit", ":quit", ":q"):
            print("Bye.")
            break
        if line == ":help":
            print_help()
            continue
        if line.startswith(":topk "):
            try:
                k = max(1, int(line.split(None, 1)[1]))
                print(f"top-k set to {k}")
            except Exception:  # pylint: disable=broad-except
                print("Usage: :topk N")
            continue
        if line.startswith(":type "):
            val = line.split(None, 1)[1].strip()
            if val.lower() in ("any", "*"):
                filters.chunk_type = None
                print("type filter cleared")
            else:
                filters.chunk_type = val
                print(f"type filter set to '{filters.chunk_type}'")
            continue
        if line == ":subdomains":
            all_names: list[str] = []
            for ch in fm.chunk_metadata.values():
                n = (ch.metadata or {}).get("subdomain_name")
                if isinstance(n, str) and n:
                    all_names.append(n)
            names = sorted(set(all_names))
            print(f"{len(names)} subdomains:")
            for n in names:
                print(f"  - {n}")
            continue
        if line.startswith(":subdomain "):
            val = line.split(None, 1)[1].strip()
            if val.lower() in ("any", "*"):
                filters.subdomain_name = None
                print("subdomain filter cleared")
            else:
                filters.subdomain_name = val
                print(f"subdomain filter set to '{filters.subdomain_name}'")
            continue
        if line.startswith(":values "):
            key = line.split(None, 1)[1].strip()
            if key:
                _list_values(fm, key)
            else:
                print("Usage: :values KEY")
            continue
        if line.startswith(":where "):
            expr = line.split(None, 1)[1]
            msg = _apply_where(filters, expr)
            if msg:
                print(msg)
            continue
        if line == ":filters":
            # Show non-empty filters
            active = {k: v for k, v in vars(filters).items() if v not in (None, "")}
            if not active:
                print("No active filters.")
            else:
                for k_, v_ in active.items():
                    print(f"  {k_}={v_}")
            continue
        if line == ":stats":
            stats = fm.get_index_statistics()
            print(
                "Index stats:\n"
                f"  total_chunks: {stats.get('total_chunks')}\n"
                f"  ntotal: {stats.get('ntotal')}\n"
                f"  dim: {stats.get('dimension')}  type: {stats.get('index_type')}\n"
                f"  threshold: {stats.get('similarity_threshold')}  trained: {stats.get('is_trained')}\n"
            )
            dist = stats.get("chunk_type_distribution", {})
            if dist:
                print("  chunk types:")
                for t, c in sorted(dist.items(), key=lambda x: (-x[1], x[0])):
                    print(f"    - {t}: {c}")
            continue
        if line.startswith(":clusters"):
            parts = line.split()
            n = 10
            if len(parts) > 1:
                try:
                    n = max(1, int(parts[1]))
                except Exception:  # pylint: disable=broad-except
                    pass
            clusters = fm.perform_semantic_clustering(n_clusters=n)
            last_clusters = {c.cluster_id: c for c in clusters}
            print(f"Computed {len(clusters)} clusters:")
            for c in clusters:
                print(
                    f"  - {c.cluster_id}: size={len(c.chunks)} avg={c.avg_similarity:.3f} "
                    f"type={c.dominant_type or '?'} conf={c.domain_confidence:.3f}"
                )
            continue
        if line.startswith(":cluster "):
            cid = line.split(None, 1)[1].strip()
            if not last_clusters:
                print("No clusters cached. Run :clusters first.")
                continue
            cl = last_clusters.get(cid)
            if not cl:
                print(f"Cluster not found in cache: {cid}")
                continue
            print(f"Cluster {cid}: {len(cl.chunks)} chunks")
            for i, ch_id in enumerate(cl.chunks[:50], start=1):
                ch = fm._get_chunk_by_id(ch_id)  # pylint: assignment
                if not ch:
                    print(f"  {i:2d}. {ch_id} (not in index)")
                    continue
                sub = ((ch.metadata or {}).get("subdomain_name")) or "?"
                print(f"  {i:2d}. {ch.chunk_id}  type={ch.chunk_type}  subdomain={sub}  src={ch.source_path}")
            if len(cl.chunks) > 50:
                print("  ... (truncated)")
            continue
        if line.startswith(":chunk "):
            cid = line.split(None, 1)[1].strip()
            handle_chunk_query(fm, cid, k, filters)
            continue
        if line.startswith(":show "):
            cid = line.split(None, 1)[1].strip()
            show_chunk(fm, cid)
            continue

        # Default: treat as free-text query
        handle_text_query(eg, fm, line, k, filters)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
