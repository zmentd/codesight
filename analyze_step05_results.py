#!/usr/bin/env python3
"""
Analysis script to examine Step 05 business domain grouping results
and compare with previous route-specific approach.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path


def load_json_file(filepath):
    """Load JSON file safely."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error in {filepath}: {e}")
        return None

def analyze_step04_routes(step04_data):
    """Analyze Step 04 JSP routes to understand the baseline."""
    if not step04_data or 'jsp_analysis' not in step04_data:
        return None
    
    routes = []
    for jsp_file, analysis in step04_data['jsp_analysis'].items():
        if 'routes' in analysis:
            for route in analysis['routes']:
                routes.append({
                    'jsp_file': jsp_file,
                    'url_pattern': route.get('url_pattern', ''),
                    'description': route.get('description', ''),
                    'business_context': route.get('business_context', ''),
                    'entities': route.get('entities', [])
                })
    
    return routes

def analyze_step05_capabilities(step05_data):
    """Analyze Step 05 capabilities to see business domain grouping."""
    if not step05_data or 'capabilities' not in step05_data:
        return None
    
    capabilities = []
    for cap in step05_data['capabilities']:
        capabilities.append({
            'name': cap.get('name', ''),
            'description': cap.get('description', ''),
            'business_domain': cap.get('business_domain', ''),
            'routes_count': len(cap.get('routes', [])),
            'routes': cap.get('routes', []),
            'entities': cap.get('entities', [])
        })
    
    return capabilities

def extract_business_domains(capabilities):
    """Extract unique business domains from capabilities."""
    domains = defaultdict(list)
    for cap in capabilities:
        domain = cap.get('business_domain', 'Unknown')
        domains[domain].append(cap)
    return dict(domains)

def analyze_route_coverage(routes, capabilities):
    """Analyze how routes are covered by capabilities."""
    route_patterns = set()
    for route in routes:
        route_patterns.add(route['url_pattern'])
    
    covered_patterns = set()
    for cap in capabilities:
        for route in cap.get('routes', []):
            if 'url_pattern' in route:
                covered_patterns.add(route['url_pattern'])
    
    coverage_pct = len(covered_patterns) / len(route_patterns) if route_patterns else 0
    return {
        'total_routes': len(route_patterns),
        'covered_routes': len(covered_patterns),
        'coverage_percentage': coverage_pct,
        'uncovered_patterns': route_patterns - covered_patterns
    }

def main():
    """Main analysis function."""
    print("🔍 Step 05 Business Domain Analysis")
    print("=" * 50)
    
    # Load data files
    project_dir = Path("d:/Prj/NBCU/storm/codesight/projects/ct-hr-storm")
    step04_file = project_dir / "output" / "step04_output.json"
    step05_file = project_dir / "output" / "step05_output.json"
    
    print(f"📂 Loading Step 04 data from: {step04_file}")
    step04_data = load_json_file(step04_file)
    
    print(f"📂 Loading Step 05 data from: {step05_file}")
    step05_data = load_json_file(step05_file)
    
    if not step04_data:
        print("❌ Cannot proceed without Step 04 data")
        return
    
    # Analyze Step 04 routes (baseline)
    print("\n📊 Step 04 Route Analysis")
    print("-" * 30)
    routes = analyze_step04_routes(step04_data)
    if routes:
        print(f"✅ Total routes found: {len(routes)}")
        
        # Show route distribution by URL pattern
        url_domains = defaultdict(int)
        for route in routes:
            pattern = route['url_pattern']
            if pattern.startswith('/'):
                parts = pattern.split('/')
                if len(parts) > 1:
                    domain = parts[1] if parts[1] else 'root'
                    url_domains[domain] += 1
        
        print(f"📈 Route distribution by URL prefix:")
        for domain, count in sorted(url_domains.items(), key=lambda x: x[1], reverse=True):
            print(f"   /{domain}/*: {count} routes")
    else:
        print("❌ No routes found in Step 04 data")
        return
    
    # Analyze Step 05 capabilities
    print("\n📊 Step 05 Capability Analysis")
    print("-" * 30)
    
    if not step05_data:
        print("⚠️  No Step 05 output found - validation may have prevented file creation")
        print("   This suggests the business domain grouping worked but failed validation")
        
        # Try to find temporary or debug output
        temp_files = list(project_dir.glob("**/step05*.json"))
        if temp_files:
            print(f"🔍 Found potential Step 05 files: {[str(f) for f in temp_files]}")
        
        return
    
    capabilities = analyze_step05_capabilities(step05_data)
    if capabilities:
        print(f"✅ Total capabilities created: {len(capabilities)}")
        
        # Analyze business domains
        domains = extract_business_domains(capabilities)
        print(f"📈 Business domains identified: {len(domains)}")
        
        for domain, caps in domains.items():
            total_routes = sum(cap['routes_count'] for cap in caps)
            print(f"   🏢 {domain}: {len(caps)} capabilities, {total_routes} routes")
            for cap in caps:
                print(f"      • {cap['name']} ({cap['routes_count']} routes)")
        
        # Analyze coverage
        coverage = analyze_route_coverage(routes, capabilities)
        print(f"\n📊 Coverage Analysis")
        print(f"   Total Step 04 routes: {coverage['total_routes']}")
        print(f"   Covered by Step 05: {coverage['covered_routes']}")
        print(f"   Coverage percentage: {coverage['coverage_percentage']:.1%}")
        
        if coverage['uncovered_patterns']:
            print(f"   ❌ Uncovered routes: {len(coverage['uncovered_patterns'])}")
            for pattern in sorted(coverage['uncovered_patterns'])[:5]:
                print(f"      • {pattern}")
            if len(coverage['uncovered_patterns']) > 5:
                print(f"      ... and {len(coverage['uncovered_patterns']) - 5} more")
    
    # Compare with previous approach
    print(f"\n📊 Comparison: Route-specific vs Business Domain")
    print("-" * 50)
    route_count = len(routes)
    capability_count = len(capabilities) if capabilities else 0
    
    if capability_count > 0:
        reduction_pct = (route_count - capability_count) / route_count
        print(f"   Routes (old approach): {route_count}")
        print(f"   Capabilities (new): {capability_count}")
        print(f"   Reduction: {reduction_pct:.1%} ({route_count - capability_count} fewer)")
        print(f"   Consolidation ratio: {route_count / capability_count:.1f}:1")
    else:
        print(f"   Routes (baseline): {route_count}")
        print(f"   Capabilities: Not available (validation failed)")
        print(f"   Expected reduction: ~48% (based on log coverage)")

if __name__ == "__main__":
    main()
    main()
