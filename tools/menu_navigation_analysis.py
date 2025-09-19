#!/usr/bin/env python3
"""
Analyze menu structure and navigation in STORM application.
Focus on understanding how menus map to business domains.
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

ROOT = Path(__file__).resolve().parents[1]


def analyze_menu_structure(project: str) -> Dict:
    """Analyze menu JSPs and their business domain organization."""
    
    # Find all menu JSP files
    project_root = Path(f"d:\\Prj\\NBCU\\storm\\{project}")
    menu_files = []
    
    # Search for menu files
    for jsp_file in project_root.rglob("*Menu*.jsp"):
        menu_files.append(jsp_file)
    
    for jsp_file in project_root.rglob("*menu*.jsp"):
        menu_files.append(jsp_file)
    
    # Remove duplicates
    menu_files = list(set(menu_files))
    
    menu_analysis = {
        'total_menu_files': len(menu_files),
        'menu_by_domain': defaultdict(list),
        'menu_files': []
    }
    
    for menu_file in menu_files:
        rel_path = str(menu_file.relative_to(project_root))
        
        # Extract domain from path
        domain = 'unknown'
        if '/jsp/asl/' in rel_path:
            domain = 'asl'
        elif '/jsp/dsl/' in rel_path:
            domain = 'dsl'
        elif '/jsp/gsl/' in rel_path:
            domain = 'gsl'
        elif '/jsp/isl/' in rel_path:
            domain = 'isl'
        elif 'WebContent/' in rel_path and '/jsp/' not in rel_path:
            domain = 'legacy'
        
        menu_info = {
            'file': rel_path,
            'domain': domain,
            'name': menu_file.stem
        }
        
        menu_analysis['menu_files'].append(menu_info)
        menu_analysis['menu_by_domain'][domain].append(menu_info)
    
    return menu_analysis


def analyze_navigation_patterns(project: str) -> Dict:
    """Analyze navigation patterns from Step04 data."""
    
    step04_path = ROOT / "projects" / project / "output" / "step04_output.json"
    
    if not step04_path.exists():
        return {"error": f"Step04 output not found: {step04_path}"}
    
    try:
        # Read only a sample since file is large
        nav_patterns = {
            'menu_jsps': [],
            'navigation_routes': [],
            'security_contexts': []
        }
        
        # Look for menu-related entities in our existing analysis
        business_analysis_path = ROOT / "projects" / project / "output" / "business_domain_analysis.json"
        
        if business_analysis_path.exists():
            with open(business_analysis_path, 'r', encoding='utf-8') as f:
                business_data = json.load(f)
            
            # Find menu-related paths
            for path in business_data['jsp_analysis']['sample_paths']:
                if 'menu' in path.lower() or 'Menu' in path:
                    nav_patterns['menu_jsps'].append(path)
        
        return nav_patterns
        
    except Exception as e:
        return {"error": f"Failed to analyze navigation: {e}"}


def extract_menu_functionality(menu_file_path: Path) -> Dict:
    """Extract functionality from a menu JSP file."""
    
    try:
        with open(menu_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        functionality = {
            'security_checks': [],
            'menu_items': [],
            'javascript_functions': [],
            'links': []
        }
        
        # Extract security level checks
        security_matches = re.findall(r'getSecurity\(\)\.get(\w+)\(\)', content)
        functionality['security_checks'] = list(set(security_matches))
        
        # Extract JavaScript function names
        js_matches = re.findall(r'function\s+(\w+)\s*\(', content)
        functionality['javascript_functions'] = list(set(js_matches))
        
        # Extract href links
        href_matches = re.findall(r'href=["\']([^"\']*)["\']', content, re.IGNORECASE)
        functionality['links'] = [link for link in href_matches if link and not link.startswith('#')]
        
        # Look for menu structure hints
        menu_hints = re.findall(r'<s:text\s+name=["\']([^"\']*)["\']', content)
        functionality['menu_items'] = list(set(menu_hints))
        
        return functionality
        
    except Exception as e:
        return {"error": f"Failed to read menu file: {e}"}


def main() -> None:
    project = "ct-hr-storm"
    
    print(f"=== Menu and Navigation Analysis for {project} ===\n")
    
    # Analyze menu structure
    menu_analysis = analyze_menu_structure(project)
    
    print(f"=== MENU FILE STRUCTURE ===")
    print(f"Total menu files found: {menu_analysis['total_menu_files']}")
    
    print(f"\n=== MENU FILES BY DOMAIN ===")
    for domain, menus in menu_analysis['menu_by_domain'].items():
        print(f"\n{domain.upper()} Domain ({len(menus)} menus):")
        for menu in menus:
            print(f"  {menu['name']}: {menu['file']}")
    
    # Analyze specific menu functionality
    print(f"\n=== MENU FUNCTIONALITY ANALYSIS ===")
    
    sample_menus = [
        "d:\\Prj\\NBCU\\storm\\ct-hr-storm\\Deployment\\Storm2\\WebContent\\jsp\\asl\\links\\Menu.jsp",
        "d:\\Prj\\NBCU\\storm\\ct-hr-storm\\Deployment\\Storm2\\WebContent\\jsp\\asl\\setup\\SetupMenu.jsp",
        "d:\\Prj\\NBCU\\storm\\ct-hr-storm\\Deployment\\Storm2\\WebContent\\jsp\\dsl\\tour\\tourTabMenu.jsp"
    ]
    
    for menu_path in sample_menus:
        menu_file = Path(menu_path)
        if menu_file.exists():
            print(f"\n--- {menu_file.stem} ---")
            functionality = extract_menu_functionality(menu_file)
            
            if 'error' not in functionality:
                print(f"Security checks: {functionality['security_checks']}")
                print(f"Menu items: {functionality['menu_items'][:5]}...")  # First 5
                print(f"JS functions: {functionality['javascript_functions'][:3]}...")  # First 3
                print(f"Links: {functionality['links'][:3]}...")  # First 3
            else:
                print(f"Error: {functionality['error']}")
    
    # Analyze navigation patterns
    nav_analysis = analyze_navigation_patterns(project)
    
    if 'error' not in nav_analysis:
        print(f"\n=== NAVIGATION PATTERNS ===")
        if nav_analysis['menu_jsps']:
            print(f"Menu JSPs in business domains:")
            for jsp in nav_analysis['menu_jsps']:
                print(f"  {jsp}")
    
    print(f"\n=== MENU VS SCREEN ANALYSIS ===")
    print(f"Menu files are navigation components, not business screens.")
    print(f"They provide:")
    print(f"  - Security-controlled navigation")
    print(f"  - Domain-specific menu structures") 
    print(f"  - Links to actual business screens")
    print(f"  - User role-based access control")
    
    print(f"\nBusiness Domain Menu Structure:")
    print(f"  ASL: Production scheduling and management menus")
    print(f"  DSL: Tour/scene management navigation")
    print(f"  GSL: System configuration menus") 
    print(f"  Legacy: Older navigation components")
    
    # Save analysis
    output_path = ROOT / "projects" / project / "output" / "menu_navigation_analysis.json"
    analysis_result = {
        'project': project,
        'menu_analysis': dict(menu_analysis['menu_by_domain']),
        'total_menu_files': menu_analysis['total_menu_files'],
        'navigation_patterns': nav_analysis
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed menu analysis saved to: {output_path}")


if __name__ == "__main__":
    main()
