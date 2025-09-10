"""Extract invokesRoute relations and their matched route entities
from a large step04_output.json and write them to a smaller JSON file.

Usage: run from the repository root. By default this will read
projects/<project>/output/step04_output.json and write
projects/<project>/output/invokesRoute_extracted.json

This script is conservative and uses brace-balancing to extract the
full JSON object text for relation and route objects.
"""
import argparse
import json
import re
from pathlib import Path


def find_all_matches(text, pattern):
    return [m for m in re.finditer(pattern, text)]

def extract_object_by_index(text, idx):
    # find opening brace before idx
    start = text.rfind('{', 0, idx)
    if start == -1:
        return None
    # balance braces from start
    depth = 0
    end = None
    for i in range(start, len(text)):
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return None
    return text[start:end]

def load_json_obj(text):
    try:
        return json.loads(text)
    except Exception:
        return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--project', default='ct-hr-storm-test')
    p.add_argument('--input', default=None)
    p.add_argument('--output', default=None)
    p.add_argument('--relation-type', default='invokesRoute', help='Relation type to extract (default: invokesRoute)')
    args = p.parse_args()

    project = args.project
    relation_type = args.relation_type
    repo_root = Path(__file__).resolve().parents[1]
    default_input = repo_root / 'projects' / project / 'output' / 'step04_output.json'
    default_output = repo_root / 'projects' / project / 'output' / f'invokesRoute_extracted_{relation_type}.json'
    input_path = Path(args.input) if args.input else default_input
    output_path = Path(args.output) if args.output else default_output

    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return

    print(f"Reading: {input_path}")
    text = input_path.read_text(encoding='utf-8', errors='replace')

    # find relation ids that look like rel_jsp_...->{relation_type}
    rel_pattern = rf'"id"\s*:\s*"(rel_jsp_[^"]*?->{re.escape(relation_type)}:[^"]*?)"'
    rel_matches = find_all_matches(text, rel_pattern)
    print(f"Found {len(rel_matches)} rel_jsp id occurrences for relation type '{relation_type}'")

    extracted = []
    route_cache = {}
    seen_rel_ids = set()

    for m in rel_matches:
        id_pos = m.start(1)
        obj_text = extract_object_by_index(text, id_pos)
        if not obj_text:
            continue
        obj = load_json_obj(obj_text)
        if not obj:
            # try to patch trailing commas
            try:
                cleaned = re.sub(r',\s*([}\]])', r'\1', obj_text)
                obj = json.loads(cleaned)
            except Exception:
                obj = None
        if not obj:
            continue
        # verify it's the requested relation type
        if obj.get('type') != relation_type:
            continue

        rel_id = obj.get('id')
        if rel_id in seen_rel_ids:
            continue
        seen_rel_ids.add(rel_id)

        relation = obj

        # relation may reference a route via 'to', 'to_id', or nested object
        to_route = None
        if isinstance(relation.get('to'), str):
            to_route = relation.get('to')
        elif isinstance(relation.get('to_id'), str):
            to_route = relation.get('to_id')
        elif isinstance(relation.get('to'), dict):
            to_route = relation.get('to').get('id')
        elif isinstance(relation.get('to'), list) and relation.get('to'):
            # take first string id if present
            first = relation.get('to')[0]
            if isinstance(first, str):
                to_route = first
            elif isinstance(first, dict):
                to_route = first.get('id')

        route_obj = None
        if to_route:
            # try cached
            if to_route in route_cache:
                route_obj = route_cache[to_route]
            else:
                # find route id occurrence (best-effort)
                route_pattern = rf'"id"\s*:\s*"({re.escape(to_route)})"'
                rm = re.search(route_pattern, text)
                if rm:
                    route_obj_text = extract_object_by_index(text, rm.start(1))
                    if route_obj_text:
                        route_obj = load_json_obj(route_obj_text)
                        if not route_obj:
                            try:
                                cleaned = re.sub(r',\s*([}\]])', r'\1', route_obj_text)
                                route_obj = json.loads(cleaned)
                            except Exception:
                                route_obj = None
                route_cache[to_route] = route_obj

        extracted.append({'relation': relation, 'route': route_obj})

    # write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(extracted, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Wrote {len(extracted)} entries to {output_path}")

if __name__ == '__main__':
    main()
