#!/usr/bin/env python3
"""
Check Step04 output for JSP classification enhancements.
"""

import json
import sys

sys.path.insert(0, 'src')

def main():
    # Read and sample the Step04 output
    with open('projects/ct-hr-storm/output/step04_output.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check JSP entities for classification attributes
    jsp_entities = [e for e in data['entities'] if e['type'] == 'JSP']
    print(f'Total JSP entities: {len(jsp_entities)}')

    # Sample first 5 JSP entities to check for our new attributes
    print('\n=== JSP ENTITY CLASSIFICATION SAMPLE ===')
    classification_attrs = [
        'jsp_function_type', 'is_component', 'ui_complexity', 
        'has_forms', 'has_security', 'classification_confidence',
        'business_domain', 'navigation_role'
    ]
    
    classified_count = 0
    for i, entity in enumerate(jsp_entities[:10]):  # Check first 10
        print(f'\nJSP {i+1}: {entity["name"]}')
        attrs = entity.get('attributes', {})
        
        has_classification = False
        for attr in classification_attrs:
            if attr in attrs:
                print(f'  {attr}: {attrs[attr]}')
                has_classification = True
        
        if has_classification:
            classified_count += 1
            
        # Show file path for reference
        if 'file_path' in attrs:
            print(f'  file_path: {attrs["file_path"]}')
    
    print(f'\n=== CLASSIFICATION SUMMARY ===')
    print(f'JSP entities with classification: {classified_count}/10 sampled')
    
    # Count entities by function type
    function_types = {}
    for entity in jsp_entities:
        attrs = entity.get('attributes', {})
        func_type = attrs.get('jsp_function_type', 'unclassified')
        function_types[func_type] = function_types.get(func_type, 0) + 1
    
    print(f'\n=== JSP FUNCTION TYPE DISTRIBUTION ===')
    for func_type, count in sorted(function_types.items()):
        print(f'{func_type}: {count}')

if __name__ == "__main__":
    main()
    main()
