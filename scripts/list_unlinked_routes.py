import re
from pathlib import Path

file_path = Path(r"d:\Prj\NBCU\storm\codesight\projects\ct-hr-storm-test\output\step04_output.json")

routes = set()
renders = set()
handles = set()

with file_path.open("r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        m = re.search(r'"id"\s*:\s*"(route_[^"]+)"', line)
        if m:
            routes.add(m.group(1))
        m2 = re.search(r'"id"\s*:\s*"rel_route_([^>-]+)->renders', line)
        if m2:
            renders.add('route_' + m2.group(1))
        m3 = re.search(r'"id"\s*:\s*"rel_route_([^>-]+)->handlesRoute', line)
        if m3:
            handles.add('route_' + m3.group(1))

unlinked = sorted(routes - renders - handles)

# Persist output to a file for environments where stdout isn't captured
out_path = Path(r"d:\Prj\NBCU\storm\codesight\scripts\unlinked_routes_out.txt")
with out_path.open("w", encoding="utf-8") as out_f:
    out_f.write(f"routes_total={len(routes)}\n")
    out_f.write(f"renders={len(renders)}\n")
    out_f.write(f"handles={len(handles)}\n")
    out_f.write(f"unlinked_count={len(unlinked)}\n")
    for r in unlinked:
        out_f.write(r + "\n")
