#!/usr/bin/env python3
"""
Quick analysis of business domain patterns from Step04 JSP file paths.
Focus on identifying realistic business domains from screen directories.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]


def analyze_jsp_paths(step04_data: Dict) -> Dict:
    """Analyze JSP file paths to identify business domain patterns."""
    
    entities = step04_data.get('entities', [])
    jsp_entities = [e for e in entities if e.get('type') == 'JSP']
    
    print(f"Found {len(jsp_entities)} JSP entities in Step04")
    
    # Extract file paths and analyze patterns
    file_paths = []
    route_jsp_mappings = []
    
    for jsp in jsp_entities:
        attrs = jsp.get('attributes', {})
        file_path = attrs.get('file_path') or attrs.get('file', '')
        
        if file_path and file_path.startswith('/jsp/'):
            file_paths.append(file_path)
    
    print(f"Found {len(file_paths)} JSP files with valid paths")
    
    # Analyze directory patterns for business domains
    domain_patterns = defaultdict(list)
    subdomain_patterns = defaultdict(list)
    
    for path in file_paths:
        # Remove /jsp/ prefix and split
        clean_path = path[5:] if path.startswith('/jsp/') else path
        segments = [s for s in clean_path.split('/') if s]
        
        if len(segments) >= 2:
            # First segment after /jsp/ is usually the main domain
            main_domain = segments[0]
            sub_domain = segments[1] if len(segments) > 1 else None
            
            domain_patterns[main_domain].append(path)
            
            if sub_domain:
                combined_domain = f"{main_domain}/{sub_domain}"
                subdomain_patterns[combined_domain].append(path)
    
    # Find routes that map to JSPs
    routes = [e for e in entities if e.get('type') == 'Route']
    
    for route in routes:
        attrs = route.get('attributes', {})
        result_jsp = attrs.get('result_jsp', '')
        action = attrs.get('action', '')
        
        if result_jsp:
            route_jsp_mappings.append({
                'route_name': route.get('name', ''),
                'action': action,
                'jsp_path': result_jsp
            })
    
    print(f"Found {len(route_jsp_mappings)} route->JSP mappings")
    
    return {
        'total_jsp_entities': len(jsp_entities),
        'valid_jsp_paths': len(file_paths),
        'route_jsp_mappings': len(route_jsp_mappings),
        'domain_patterns': {k: len(v) for k, v in domain_patterns.items()},
        'subdomain_patterns': {k: len(v) for k, v in subdomain_patterns.items()},
        'sample_paths': file_paths[:20],
        'sample_mappings': route_jsp_mappings[:10],
        'detailed_domains': {
            k: {
                'count': len(v),
                'sample_paths': v[:5]
            } for k, v in domain_patterns.items()
        }
    }


def analyze_route_patterns(step04_data: Dict) -> Dict:
    """Analyze route patterns and actions."""
    
    entities = step04_data.get('entities', [])
    routes = [e for e in entities if e.get('type') == 'Route']
    
    print(f"Found {len(routes)} route entities")
    
    action_patterns = defaultdict(list)
    action_class_patterns = defaultdict(list)
    
    for route in routes:
        attrs = route.get('attributes', {})
        action = attrs.get('action', '')
        action_class = attrs.get('action_class', '')
        
        if action:
            # Extract domain hints from action names
            if 'Catalog' in action:
                domain_hint = action.replace('Catalog', '').strip()
                action_patterns[domain_hint].append(route.get('name', ''))
        
        if action_class:
            # Extract package-based domain hints
            if 'storm.gsl.' in action_class:
                parts = action_class.split('.')
                try:
                    gsl_index = parts.index('gsl')
                    if gsl_index + 1 < len(parts):
                        package_domain = parts[gsl_index + 1]
                        action_class_patterns[package_domain].append(action_class)
                except ValueError:
                    pass
    
    return {
        'total_routes': len(routes),
        'action_patterns': {k: len(v) for k, v in action_patterns.items()},
        'action_class_patterns': {k: len(v) for k, v in action_class_patterns.items()},
        'sample_actions': {
            k: {
                'count': len(v),
                'samples': v[:3]
            } for k, v in action_patterns.items()
        }
    }


def main() -> None:
    project = sys.argv[1] if len(sys.argv) > 1 else "ct-hr-storm"
    step04_path = ROOT / "projects" / project / "output" / "step04_output.json"
    
    if not step04_path.exists():
        print(f"Step04 output not found: {step04_path}")
        return
    
    with open(step04_path, 'r', encoding='utf-8') as f:
        step04_data = json.load(f)
    
    print(f"=== Analyzing Business Domains for {project} ===\n")
    
    # Analyze JSP patterns
    jsp_analysis = analyze_jsp_paths(step04_data)
    
    print(f"\n=== JSP ANALYSIS ===")
    print(f"Total JSP entities: {jsp_analysis['total_jsp_entities']}")
    print(f"Valid JSP paths: {jsp_analysis['valid_jsp_paths']}")
    print(f"Route->JSP mappings: {jsp_analysis['route_jsp_mappings']}")
    
    print(f"\n=== DOMAIN PATTERNS ===")
    for domain, count in sorted(jsp_analysis['domain_patterns'].items()):
        print(f"  {domain}: {count} screens")
    
    print(f"\n=== SUBDOMAIN PATTERNS ===")
    for subdomain, count in sorted(jsp_analysis['subdomain_patterns'].items()):
        if count > 1:  # Only show subdomains with multiple screens
            print(f"  {subdomain}: {count} screens")
    
    print(f"\n=== SAMPLE JSP PATHS ===")
    for path in jsp_analysis['sample_paths']:
        print(f"  {path}")
    
    # Analyze route patterns
    route_analysis = analyze_route_patterns(step04_data)
    
    print(f"\n=== ROUTE ANALYSIS ===")
    print(f"Total routes: {route_analysis['total_routes']}")
    
    print(f"\n=== ACTION PATTERNS ===")
    for action, count in sorted(route_analysis['action_patterns'].items()):
        print(f"  {action}: {count} routes")
    
    print(f"\n=== ACTION CLASS PATTERNS ===")
    for package, count in sorted(route_analysis['action_class_patterns'].items()):
        print(f"  {package}: {count} action classes")
    
    print(f"\n=== SAMPLE ROUTE->JSP MAPPINGS ===")
    for mapping in jsp_analysis['sample_mappings']:
        print(f"  {mapping['action']} -> {mapping['jsp_path']}")
    
    # Propose business domains
    print(f"\n=== PROPOSED BUSINESS DOMAINS ===")
    
    # Combine JSP directory patterns with route action patterns
    combined_domains = set()
    
    # From JSP directories
    for domain in jsp_analysis['domain_patterns'].keys():
        if jsp_analysis['domain_patterns'][domain] > 2:  # At least 3 screens
            combined_domains.add(domain)
    
    # From route actions
    for action in route_analysis['action_patterns'].keys():
        if route_analysis['action_patterns'][action] > 1:  # At least 2 routes
            combined_domains.add(action.lower())
    
    business_domain_mapping = {
        'gsl': 'Global System Library / Configuration',
        'activityflag': 'Activity and Flag Management',
        'earningcode': 'Payroll and Earning Codes',
        'codegroup': 'Code Group Management',
        'timezone': 'Time Zone and Calendar Management',
        'overtime': 'Overtime Management',
        'quartzcp': 'Batch Processing and Integration',
        'tkholiday': 'Holiday and Calendar Management',
        'feed': 'Data Feed Management',
        'security': 'Security and Access Management'
    }
    
    for domain in sorted(combined_domains):
        business_name = business_domain_mapping.get(domain.lower(), f"Domain: {domain}")
        jsp_count = jsp_analysis['domain_patterns'].get(domain, 0)
        route_count = route_analysis['action_patterns'].get(domain, 0)
        print(f"  {business_name}")
        print(f"    - JSP screens: {jsp_count}")
        print(f"    - Routes: {route_count}")
    
    # Save analysis
    output_path = ROOT / "projects" / project / "output" / "business_domain_analysis.json"
    analysis_result = {
        'project': project,
        'jsp_analysis': jsp_analysis,
        'route_analysis': route_analysis,
        'proposed_domains': list(combined_domains),
        'business_domain_mapping': business_domain_mapping
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed analysis saved to: {output_path}")


if __name__ == "__main__":
    main()
