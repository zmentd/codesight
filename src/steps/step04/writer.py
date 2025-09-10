from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from steps.step04.models import Step04Output


def write_step04_output(output: Step04Output, project_dir: str) -> str:
    """Persist Step04Output to projects/{project}/output/step04_output.json"""
    out_dir = Path(project_dir) / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "step04_output.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output.to_dict(), f, ensure_ascii=False, indent=2)
    return str(out_path)


def read_step04_output(project_dir: str) -> Step04Output:
    path = Path(project_dir) / "output" / "step04_output.json"
    with path.open("r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    return Step04Output.from_dict(data)
