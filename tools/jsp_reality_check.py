#!/usr/bin/env python3
"""
Deep dive analysis to understand why we have so many JSP "screens".
Check for duplicates, fragments, includes, and other non-user-facing JSPs.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]


def analyze_jsp_reality_check(step04_data: Dict) -> Dict:
    """Deep analysis to understand what these 595 JSPs actually are."""
    
    entities = step04_data.get('entities', [])
    jsp_entities = [e for e in entities if e.get('type') == 'JSP']
    
    print(f"=== DEEP DIVE: {len(jsp_entities)} JSP ENTITIES ===\n")
    
    # Categorize JSPs
    real_screens = []
    fragments = []
    includes = []
    duplicates = []
    system_pages = []
    unknown = []
    
    file_paths = set()
    name_patterns = Counter()
    
    for jsp in jsp_entities:
        jsp_id = jsp.get('id', '')
        jsp_name = jsp.get('name', '')
        attrs = jsp.get('attributes', {})
        file_path = attrs.get('file_path') or attrs.get('file', '')
        
        # Track name patterns
        if jsp_name:
            # Extract pattern from name
            if jsp_name.endswith('Details'):
                name_patterns['Details'] += 1
            elif jsp_name.endswith('List'):
                name_patterns['List'] += 1
            elif jsp_name.endswith('Form'):
                name_patterns['Form'] += 1
            elif jsp_name.endswith('Page'):
                name_patterns['Page'] += 1
            elif 'Fragment' in jsp_name or 'fragment' in jsp_name:
                name_patterns['Fragment'] += 1
            elif 'Include' in jsp_name or 'include' in jsp_name:
                name_patterns['Include'] += 1
            else:
                name_patterns['Other'] += 1
        
        # Check for duplicate file paths
        if file_path:
            if file_path in file_paths:
                duplicates.append({
                    'id': jsp_id,
                    'name': jsp_name,
                    'file_path': file_path
                })
            else:
                file_paths.add(file_path)
        
        # Categorize by file path patterns
        if file_path:
            path_lower = file_path.lower()
            
            # System/infrastructure pages
            if any(x in path_lower for x in ['error', 'blank', 'logout', 'login', 'frame']):
                system_pages.append({
                    'id': jsp_id,
                    'name': jsp_name,
                    'file_path': file_path,
                    'category': 'system'
                })
            # Fragment/include files
            elif any(x in path_lower for x in ['fragment', 'include', 'header', 'footer', 'menu']):
                fragments.append({
                    'id': jsp_id,
                    'name': jsp_name,
                    'file_path': file_path,
                    'category': 'fragment'
                })
            # Real business screens (likely)
            elif file_path.startswith('/jsp/') and not any(x in path_lower for x in ['fragment', 'include', 'common']):
                real_screens.append({
                    'id': jsp_id,
                    'name': jsp_name,
                    'file_path': file_path,
                    'category': 'business_screen'
                })
            else:
                unknown.append({
                    'id': jsp_id,
                    'name': jsp_name,
                    'file_path': file_path,
                    'category': 'unknown'
                })
        else:
            unknown.append({
                'id': jsp_id,
                'name': jsp_name,
                'file_path': file_path,
                'category': 'no_path'
            })
    
    # Analyze real screens by domain
    real_screen_domains = defaultdict(list)
    for screen in real_screens:
        path = screen['file_path']
        if path.startswith('/jsp/'):
            segments = path[5:].split('/')
            if segments:
                domain = segments[0]
                real_screen_domains[domain].append(screen)
    
    # Sample analysis
    print("=== CATEGORIZATION RESULTS ===")
    print(f"Real Business Screens: {len(real_screens)}")
    print(f"System Pages: {len(system_pages)}")
    print(f"Fragments/Includes: {len(fragments)}")
    print(f"Duplicates: {len(duplicates)}")
    print(f"Unknown/No Path: {len(unknown)}")
    print(f"Total: {len(real_screens) + len(system_pages) + len(fragments) + len(duplicates) + len(unknown)}")
    
    print(f"\n=== NAME PATTERNS ===")
    for pattern, count in name_patterns.most_common():
        print(f"  {pattern}: {count}")
    
    print(f"\n=== REAL SCREENS BY DOMAIN ===")
    for domain, screens in sorted(real_screen_domains.items()):
        print(f"  {domain}: {len(screens)} screens")
    
    print(f"\n=== SAMPLE SYSTEM PAGES ===")
    for page in system_pages[:10]:
        print(f"  {page['name']} -> {page['file_path']}")
    
    print(f"\n=== SAMPLE FRAGMENTS ===")
    for frag in fragments[:10]:
        print(f"  {frag['name']} -> {frag['file_path']}")
    
    print(f"\n=== SAMPLE REAL SCREENS ===")
    for screen in real_screens[:20]:
        print(f"  {screen['name']} -> {screen['file_path']}")
    
    print(f"\n=== DUPLICATES ===")
    for dup in duplicates[:10]:
        print(f"  {dup['name']} -> {dup['file_path']}")
    
    # Look for patterns that might indicate generated or template screens
    generated_patterns = []
    template_patterns = []
    
    for screen in real_screens:
        name = screen['name']
        path = screen['file_path']
        
        # Check for generated patterns
        if any(x in name.lower() for x in ['generated', 'auto', 'template']):
            generated_patterns.append(screen)
        
        # Check for very similar names (might be templates)
        base_name = name.replace('Details', '').replace('List', '').replace('Form', '')
        if len(base_name) < 3:  # Very short base names might indicate templates
            template_patterns.append(screen)
    
    print(f"\n=== POTENTIALLY GENERATED SCREENS ===")
    print(f"Generated patterns: {len(generated_patterns)}")
    for gen in generated_patterns[:5]:
        print(f"  {gen['name']} -> {gen['file_path']}")
    
    print(f"\nTemplate patterns: {len(template_patterns)}")
    for tmp in template_patterns[:5]:
        print(f"  {tmp['name']} -> {tmp['file_path']}")
    
    return {
        'total_jsp_entities': len(jsp_entities),
        'categorization': {
            'real_business_screens': len(real_screens),
            'system_pages': len(system_pages),
            'fragments_includes': len(fragments),
            'duplicates': len(duplicates),
            'unknown': len(unknown)
        },
        'name_patterns': dict(name_patterns),
        'real_screen_domains': {k: len(v) for k, v in real_screen_domains.items()},
        'samples': {
            'real_screens': real_screens[:10],
            'system_pages': system_pages[:5],
            'fragments': fragments[:5],
            'duplicates': duplicates[:5]
        },
        'potentially_generated': len(generated_patterns) + len(template_patterns)
    }


def check_route_connections(step04_data: Dict) -> Dict:
    """Check how many JSPs are actually connected to routes."""
    
    entities = step04_data.get('entities', [])
    relations = step04_data.get('relations', [])
    
    # Get all JSP entities
    jsp_entities = {e.get('id'): e for e in entities if e.get('type') == 'JSP'}
    route_entities = {e.get('id'): e for e in entities if e.get('type') == 'Route'}
    
    # Find renders relationships (route -> JSP)
    renders_relations = [r for r in relations if r.get('type') == 'renders']
    
    print(f"\n=== ROUTE CONNECTION ANALYSIS ===")
    print(f"Total JSP entities: {len(jsp_entities)}")
    print(f"Total Route entities: {len(route_entities)}")
    print(f"Renders relations: {len(renders_relations)}")
    
    # Which JSPs are referenced by routes?
    jsps_with_routes = set()
    route_jsp_mappings = []
    
    for rel in renders_relations:
        from_id = rel.get('from_id')  # route
        to_id = rel.get('to_id')      # jsp
        
        route_entity = route_entities.get(from_id)
        jsp_entity = jsp_entities.get(to_id)
        
        if route_entity and jsp_entity:
            jsps_with_routes.add(to_id)
            route_jsp_mappings.append({
                'route_name': route_entity.get('name', ''),
                'jsp_name': jsp_entity.get('name', ''),
                'jsp_path': jsp_entity.get('attributes', {}).get('file_path', '')
            })
    
    jsps_without_routes = set(jsp_entities.keys()) - jsps_with_routes
    
    print(f"JSPs connected to routes: {len(jsps_with_routes)}")
    print(f"JSPs NOT connected to routes: {len(jsps_without_routes)}")
    
    print(f"\n=== SAMPLE CONNECTED JSPs ===")
    for mapping in route_jsp_mappings[:10]:
        print(f"  {mapping['route_name']} -> {mapping['jsp_name']} ({mapping['jsp_path']})")
    
    print(f"\n=== SAMPLE UNCONNECTED JSPs ===")
    unconnected_samples = []
    for jsp_id in list(jsps_without_routes)[:10]:
        jsp = jsp_entities[jsp_id]
        unconnected_samples.append({
            'name': jsp.get('name', ''),
            'path': jsp.get('attributes', {}).get('file_path', '')
        })
        print(f"  {jsp.get('name', '')} -> {jsp.get('attributes', {}).get('file_path', '')}")
    
    return {
        'total_jsps': len(jsp_entities),
        'connected_to_routes': len(jsps_with_routes),
        'not_connected_to_routes': len(jsps_without_routes),
        'route_jsp_mappings': route_jsp_mappings,
        'unconnected_samples': unconnected_samples
    }


def main() -> None:
    project = sys.argv[1] if len(sys.argv) > 1 else "ct-hr-storm"
    step04_path = ROOT / "projects" / project / "output" / "step04_output.json"
    
    if not step04_path.exists():
        print(f"Step04 output not found: {step04_path}")
        return
    
    with open(step04_path, 'r', encoding='utf-8') as f:
        step04_data = json.load(f)
    
    print(f"=== JSP REALITY CHECK for {project} ===\n")
    
    # Deep analysis of JSP types
    jsp_analysis = analyze_jsp_reality_check(step04_data)
    
    # Check route connections
    connection_analysis = check_route_connections(step04_data)
    
    # Final summary
    print(f"\n{'='*50}")
    print(f"REALITY CHECK SUMMARY")
    print(f"{'='*50}")
    print(f"Total JSP entities found: {jsp_analysis['total_jsp_entities']}")
    print(f"Likely real business screens: {jsp_analysis['categorization']['real_business_screens']}")
    print(f"System/infrastructure pages: {jsp_analysis['categorization']['system_pages']}")
    print(f"Fragments/includes: {jsp_analysis['categorization']['fragments_includes']}")
    print(f"Connected to routes: {connection_analysis['connected_to_routes']}")
    print(f"Not connected to routes: {connection_analysis['not_connected_to_routes']}")
    
    realistic_estimate = min(
        jsp_analysis['categorization']['real_business_screens'],
        connection_analysis['connected_to_routes'] + 20  # Allow for some unconnected business screens
    )
    
    print(f"\nREALISTIC BUSINESS SCREEN ESTIMATE: {realistic_estimate}")
    
    # Save detailed analysis
    output_path = ROOT / "projects" / project / "output" / "jsp_reality_check.json"
    result = {
        'project': project,
        'jsp_analysis': jsp_analysis,
        'connection_analysis': connection_analysis,
        'realistic_estimate': realistic_estimate
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed analysis saved to: {output_path}")


if __name__ == "__main__":
    main()
