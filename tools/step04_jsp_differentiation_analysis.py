#!/usr/bin/env python3
"""
Analyze Step04 output to see if it differentiates between JSP types.
Check what attributes and metadata are available for different JSP entities.
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set

ROOT = Path(__file__).resolve().parents[1]


def analyze_step04_jsp_differentiation(project: str) -> Dict:
    """Analyze how Step04 differentiates JSP entities."""
    
    step04_path = ROOT / "projects" / project / "output" / "step04_output.json"
    
    if not step04_path.exists():
        return {"error": f"Step04 output not found: {step04_path}"}
    
    print("Loading Step04 data (this may take a moment for large files)...")
    
    try:
        with open(step04_path, 'r', encoding='utf-8') as f:
            step04_data = json.load(f)
        
        entities = step04_data.get('entities', [])
        jsp_entities = [e for e in entities if e.get('type') == 'JSP']
        
        print(f"Found {len(jsp_entities)} JSP entities")
        
        # Analyze JSP entity attributes
        attribute_analysis = {
            'all_attributes': set(),
            'attribute_frequency': Counter(),
            'sample_entities': [],
            'path_patterns': defaultdict(list),
            'functional_classifications': defaultdict(list)
        }
        
        for i, jsp in enumerate(jsp_entities[:100]):  # Sample first 100 for analysis
            attrs = jsp.get('attributes', {})
            entity_id = jsp.get('id', f'jsp_{i}')
            name = jsp.get('name', 'unknown')
            
            # Collect all attribute keys
            for key in attrs.keys():
                attribute_analysis['all_attributes'].add(key)
                attribute_analysis['attribute_frequency'][key] += 1
            
            # Sample entity for detailed analysis
            if i < 10:
                attribute_analysis['sample_entities'].append({
                    'id': entity_id,
                    'name': name,
                    'attributes': attrs
                })
            
            # Analyze file paths
            file_path = attrs.get('file_path') or attrs.get('file', '')
            if file_path:
                # Extract pattern hints
                if 'menu' in file_path.lower():
                    attribute_analysis['functional_classifications']['menu'].append(entity_id)
                elif 'error' in file_path.lower() or 'blank' in file_path.lower():
                    attribute_analysis['functional_classifications']['utility'].append(entity_id)
                elif 'report' in file_path.lower() or 'dashboard' in file_path.lower():
                    attribute_analysis['functional_classifications']['report'].append(entity_id)
                elif 'setup' in file_path.lower():
                    attribute_analysis['functional_classifications']['admin'].append(entity_id)
                else:
                    attribute_analysis['functional_classifications']['business'].append(entity_id)
                
                # Analyze path segments
                if file_path.startswith('/jsp/'):
                    segments = file_path[5:].split('/')
                    if len(segments) >= 2:
                        domain_path = f"{segments[0]}/{segments[1]}"
                        attribute_analysis['path_patterns'][domain_path].append(entity_id)
        
        # Check for relationships that might indicate JSP types
        relationships = step04_data.get('relationships', [])
        jsp_relationships = defaultdict(list)
        
        for rel in relationships:
            source_type = rel.get('source_type', '')
            target_type = rel.get('target_type', '')
            rel_type = rel.get('type', '')
            
            if source_type == 'JSP' or target_type == 'JSP':
                jsp_relationships[rel_type].append(rel)
        
        return {
            'total_jsp_entities': len(jsp_entities),
            'attribute_analysis': {
                'unique_attributes': sorted(list(attribute_analysis['all_attributes'])),
                'attribute_frequency': dict(attribute_analysis['attribute_frequency']),
                'sample_entities': attribute_analysis['sample_entities'],
                'functional_classifications': dict(attribute_analysis['functional_classifications']),
                'path_patterns': dict(attribute_analysis['path_patterns'])
            },
            'relationship_analysis': {
                'jsp_relationship_types': list(jsp_relationships.keys()),
                'relationship_counts': {k: len(v) for k, v in jsp_relationships.items()},
                'sample_relationships': {k: v[:3] for k, v in jsp_relationships.items()}
            }
        }
        
    except Exception as e:
        return {"error": f"Failed to analyze Step04: {e}"}


def analyze_differentiation_capabilities(analysis_result: Dict) -> Dict:
    """Analyze what differentiation capabilities exist in Step04."""
    
    if 'error' in analysis_result:
        return analysis_result
    
    capabilities = {
        'path_based_classification': False,
        'attribute_based_classification': False,
        'relationship_based_classification': False,
        'functional_hints': [],
        'missing_capabilities': []
    }
    
    # Check attributes for classification hints
    attrs = analysis_result['attribute_analysis']['unique_attributes']
    
    functional_attrs = [
        'function', 'purpose', 'type', 'category', 'role',
        'is_fragment', 'is_component', 'is_menu', 'is_screen'
    ]
    
    classification_attrs = []
    for attr in attrs:
        if any(hint in attr.lower() for hint in functional_attrs):
            classification_attrs.append(attr)
    
    if classification_attrs:
        capabilities['attribute_based_classification'] = True
        capabilities['functional_hints'] = classification_attrs
    
    # Check if file paths provide classification
    path_patterns = analysis_result['attribute_analysis']['path_patterns']
    if path_patterns:
        capabilities['path_based_classification'] = True
    
    # Check relationships for classification
    rel_types = analysis_result['relationship_analysis']['jsp_relationship_types']
    classification_rels = ['includes', 'renders', 'fragments', 'components']
    
    if any(rel in ' '.join(rel_types).lower() for rel in classification_rels):
        capabilities['relationship_based_classification'] = True
    
    # Identify missing capabilities
    if not capabilities['attribute_based_classification']:
        capabilities['missing_capabilities'].append("No explicit JSP type/function attributes")
    
    if 'renders' not in rel_types:
        capabilities['missing_capabilities'].append("No 'renders' relationships for route->JSP mappings")
    
    if 'includes' not in rel_types:
        capabilities['missing_capabilities'].append("No 'includes' relationships for JSP fragments")
    
    return capabilities


def main() -> None:
    project = sys.argv[1] if len(sys.argv) > 1 else "ct-hr-storm"
    
    print(f"=== Step04 JSP Differentiation Analysis for {project} ===\n")
    
    analysis = analyze_step04_jsp_differentiation(project)
    
    if 'error' in analysis:
        print(f"Error: {analysis['error']}")
        return
    
    print(f"=== JSP ENTITY ATTRIBUTES ===")
    attrs = analysis['attribute_analysis']
    print(f"Total JSP entities: {analysis['total_jsp_entities']}")
    print(f"Unique attributes found: {len(attrs['unique_attributes'])}")
    
    print(f"\nMost common attributes:")
    for attr, count in sorted(attrs['attribute_frequency'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {attr}: {count} entities")
    
    print(f"\nAll available attributes:")
    for attr in attrs['unique_attributes']:
        print(f"  {attr}")
    
    print(f"\n=== SAMPLE JSP ENTITIES ===")
    for entity in attrs['sample_entities'][:3]:
        print(f"\nEntity: {entity['name']} (ID: {entity['id']})")
        for key, value in entity['attributes'].items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
    
    print(f"\n=== FUNCTIONAL CLASSIFICATION ===")
    for func_type, entities in attrs['functional_classifications'].items():
        print(f"{func_type.title()}: {len(entities)} entities")
    
    print(f"\n=== PATH PATTERNS ===")
    for path, entities in sorted(attrs['path_patterns'].items()):
        if len(entities) > 1:
            print(f"{path}: {len(entities)} entities")
    
    print(f"\n=== RELATIONSHIP ANALYSIS ===")
    rel_analysis = analysis['relationship_analysis']
    print(f"JSP-related relationship types: {rel_analysis['jsp_relationship_types']}")
    
    for rel_type, count in rel_analysis['relationship_counts'].items():
        print(f"  {rel_type}: {count} relationships")
    
    # Analyze differentiation capabilities
    capabilities = analyze_differentiation_capabilities(analysis)
    
    print(f"\n=== DIFFERENTIATION CAPABILITIES ===")
    print(f"Path-based classification: {capabilities['path_based_classification']}")
    print(f"Attribute-based classification: {capabilities['attribute_based_classification']}")
    print(f"Relationship-based classification: {capabilities['relationship_based_classification']}")
    
    if capabilities['functional_hints']:
        print(f"Functional hint attributes: {capabilities['functional_hints']}")
    
    if capabilities['missing_capabilities']:
        print(f"\nMissing capabilities:")
        for missing in capabilities['missing_capabilities']:
            print(f"  - {missing}")
    
    print(f"\n=== CONCLUSION ===")
    print(f"Step04 appears to {'DOES' if any(capabilities.values()) else 'DOES NOT'} provide JSP differentiation.")
    print(f"Primary classification method: {'Path-based' if capabilities['path_based_classification'] else 'Limited'}")
    
    # Save detailed analysis
    output_path = ROOT / "projects" / project / "output" / "step04_jsp_differentiation_analysis.json"
    
    result = {
        'project': project,
        'analysis': analysis,
        'capabilities': capabilities
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed analysis saved to: {output_path}")


if __name__ == "__main__":
    main()
