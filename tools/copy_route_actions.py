import json
import shutil
from pathlib import Path
from typing import Set

BASE = Path(__file__).resolve().parents[1]
OUTPUT_JSON = BASE / "projects" / "ct-hr-storm-test" / "output" / "step04_output.json"

# Map package segment to source base in the main repo
SRC_BASES = {
    "dsl": Path(r"d:\Prj\NBCU\storm\ct-hr-storm\Deployment\Storm_Aux\src"),
    "gsl": Path(r"d:\Prj\NBCU\storm\ct-hr-storm\Deployment\Storm_Aux\src"),
    "isl": Path(r"d:\Prj\NBCU\storm\ct-hr-storm\Deployment\Storm_Aux\src"),
    "asl": Path(r"d:\Prj\NBCU\storm\ct-hr-storm\Deployment\Storm2\src"),
}

# Mirror destination structure in the test project
DST_BASES = {
    "dsl": BASE / "projects" / "ct-hr-storm-test" / "Deployment" / "Storm_Aux" / "src",
    "gsl": BASE / "projects" / "ct-hr-storm-test" / "Deployment" / "Storm_Aux" / "src",
    "isl": BASE / "projects" / "ct-hr-storm-test" / "Deployment" / "Storm_Aux" / "src",
    "asl": BASE / "projects" / "ct-hr-storm-test" / "Deployment" / "Storm2" / "src",
}


def main() -> None:
    data = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    actions: Set[str] = set()
    for e in data.get("entities", []):
        if e.get("type") == "Route":
            attrs = e.get("attributes") or {}
            cls = attrs.get("action_class")
            if isinstance(cls, str) and cls:
                actions.add(cls)

    copied, skipped, missing = 0, 0, 0
    for cls in sorted(actions):
        parts = cls.split(".")
        # Expected: com.nbcuni.dcss.storm.<segment>....
        segment = parts[4] if len(parts) >= 5 else ""
        segment_key = segment if segment in SRC_BASES else "gsl"  # default to Storm_Aux
        src_base = SRC_BASES[segment_key]
        dst_base = DST_BASES[segment_key]

        rel = Path(*parts)
        src = src_base / rel.with_suffix(".java")
        dst = dst_base / rel.with_suffix(".java")

        if dst.exists():
            skipped += 1
            continue
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"COPIED {src} -> {dst}")
            copied += 1
        else:
            print(f"MISSING SOURCE for {cls} at {src}")
            missing += 1

    print(f"Summary: copied={copied}, skipped={skipped}, missing={missing}, total={len(actions)}")


if __name__ == "__main__":
    main()
