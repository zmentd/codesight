#!/usr/bin/env python3
"""
Categorize JSP files to understand screens vs components vs navigation.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]


def categorize_jsp_files(project: str) -> Dict:
    """Categorize JSP files by type and function."""
    
    step04_path = ROOT / "projects" / project / "output" / "step04_output.json"
    
    if not step04_path.exists():
        return {"error": f"Step04 output not found: {step04_path}"}
    
    # Use our existing business analysis
    business_analysis_path = ROOT / "projects" / project / "output" / "business_domain_analysis.json"
    
    if not business_analysis_path.exists():
        return {"error": f"Business analysis not found: {business_analysis_path}"}
    
    with open(business_analysis_path, 'r', encoding='utf-8') as f:
        business_data = json.load(f)
    
    categories = {
        'business_screens': [],      # Main user-facing screens
        'menu_navigation': [],       # Menu and navigation components  
        'fragments_includes': [],    # JSP fragments and includes
        'error_utility': [],         # Error pages and utilities
        'forms_dialogs': [],         # Forms and dialog screens
        'reports': [],               # Report screens
        'admin_setup': []            # Admin and setup screens
    }
    
    # Get all JSP paths from analysis
    all_paths = business_data['jsp_analysis']['sample_paths'] + \
                [detail['sample_paths'] for detail in business_data['jsp_analysis']['detailed_domains'].values()]
    
    # Flatten the nested lists
    flat_paths = []
    for item in all_paths:
        if isinstance(item, list):
            flat_paths.extend(item)
        else:
            flat_paths.append(item)
    
    # Remove duplicates
    unique_paths = list(set(flat_paths))
    
    for path in unique_paths:
        filename = path.split('/')[-1].lower()
        path_lower = path.lower()
        
        # Categorize based on naming patterns and path structure
        if 'menu' in filename or 'tabmenu' in filename:
            categories['menu_navigation'].append(path)
        elif 'error' in filename or 'blank' in filename or 'logout' in filename:
            categories['error_utility'].append(path)
        elif 'report' in path_lower or 'dashboard' in path_lower:
            categories['reports'].append(path)
        elif '/setup/' in path_lower or 'setup' in filename:
            categories['admin_setup'].append(path)
        elif 'details' in filename or 'list' in filename or 'form' in filename:
            categories['business_screens'].append(path)
        elif filename.startswith('inc_') or '_inc' in filename or 'include' in filename:
            categories['fragments_includes'].append(path)
        elif 'dialog' in filename or 'popup' in filename or 'modal' in filename:
            categories['forms_dialogs'].append(path)
        else:
            # Default to business screens for main functional areas
            if any(domain in path for domain in ['/asl/', '/dsl/', '/gsl/']):
                categories['business_screens'].append(path)
            else:
                categories['error_utility'].append(path)
    
    # Calculate statistics
    total_categorized = sum(len(cat) for cat in categories.values())
    
    statistics = {
        'total_jsp_paths_analyzed': len(unique_paths),
        'total_categorized': total_categorized,
        'category_counts': {k: len(v) for k, v in categories.items()},
        'categories': categories
    }
    
    return statistics


def main() -> None:
    project = "ct-hr-storm"
    
    print(f"=== JSP File Categorization for {project} ===\n")
    
    categorization = categorize_jsp_files(project)
    
    if 'error' in categorization:
        print(f"Error: {categorization['error']}")
        return
    
    print(f"=== JSP CATEGORIZATION SUMMARY ===")
    print(f"Total JSP paths analyzed: {categorization['total_jsp_paths_analyzed']}")
    print(f"Total categorized: {categorization['total_categorized']}")
    
    print(f"\n=== CATEGORY BREAKDOWN ===")
    for category, count in categorization['category_counts'].items():
        percentage = (count / categorization['total_categorized'] * 100) if categorization['total_categorized'] > 0 else 0
        print(f"{category.replace('_', ' ').title()}: {count} files ({percentage:.1f}%)")
    
    print(f"\n=== SAMPLE FILES BY CATEGORY ===")
    for category, files in categorization['categories'].items():
        if files:
            print(f"\n{category.replace('_', ' ').title()} (showing first 5):")
            for file in files[:5]:
                print(f"  {file}")
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more")
    
    print(f"\n=== INTERPRETATION ===")
    print(f"Business Screens: Actual user-facing functional screens")
    print(f"Menu/Navigation: Components that provide navigation between screens")
    print(f"Fragments/Includes: Reusable JSP components and partials")
    print(f"Error/Utility: System pages like error handlers and logout")
    print(f"Forms/Dialogs: Modal dialogs and popup forms")
    print(f"Reports: Reporting and dashboard screens")
    print(f"Admin/Setup: System administration and configuration screens")
    
    # Save detailed analysis
    output_path = ROOT / "projects" / project / "output" / "jsp_categorization_analysis.json"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(categorization, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed categorization saved to: {output_path}")


if __name__ == "__main__":
    main()
