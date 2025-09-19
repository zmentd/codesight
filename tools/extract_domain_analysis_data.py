#!/usr/bin/env python3
"""
Extract key data from Step02 and Step04 outputs for business domain analysis.

This script extracts:
1. JSP screens with menu/navigation context from Step02
2. Route-to-screen mappings from Step04
3. Screen-to-data relationships from Step04
4. Security patterns from Step04
5. Menu hierarchies and navigation patterns

Usage:
    python extract_domain_analysis_data.py [project_name]
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]


class DomainAnalysisExtractor:
    """Extract data needed for business domain analysis from Step02/Step04 outputs."""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.project_path = ROOT / "projects" / project_name
        self.step02_path = self.project_path / "output" / "step02_output.json"
        self.step04_path = self.project_path / "output" / "step04_output.json"
        
        # Data containers
        self.screens: Dict[str, Dict[str, Any]] = {}
        self.routes: Dict[str, Dict[str, Any]] = {}
        self.route_screen_mappings: List[Dict[str, Any]] = []
        self.screen_data_mappings: List[Dict[str, Any]] = []
        self.security_patterns: List[Dict[str, Any]] = []
        self.menu_hierarchies: List[Dict[str, Any]] = []
        self.architectural_subdomains: Set[str] = set()

    def load_step02_data(self) -> Optional[Dict[str, Any]]:
        """Load Step02 output data."""
        if not self.step02_path.exists():
            print(f"Step02 output not found: {self.step02_path}")
            return None
        
        try:
            with open(self.step02_path, 'r', encoding='utf-8') as f:
                data: Dict[str, Any] = json.load(f)
                return data
        except Exception as e:
            print(f"Error loading Step02 data: {e}")
            return None

    def load_step04_data(self) -> Optional[Dict[str, Any]]:
        """Load Step04 output data."""
        if not self.step04_path.exists():
            print(f"Step04 output not found: {self.step04_path}")
            return None
        
        try:
            with open(self.step04_path, 'r', encoding='utf-8') as f:
                data: Dict[str, Any] = json.load(f)
                return data
        except Exception as e:
            print(f"Error loading Step04 data: {e}")
            return None

    def extract_screens_from_step02(self, step02_data: Dict[str, Any]) -> None:
        """Extract JSP screens and their context from Step02."""
        try:
            source_inventory = step02_data.get('source_inventory', {})
            files = source_inventory.get('files', [])
            
            for file_item in files:
                if not isinstance(file_item, dict):
                    continue
                    
                details = file_item.get('details', {})
                if not isinstance(details, dict):
                    continue
                    
                # Look for JSP files
                if details.get('detail_type') == 'jsp':
                    file_path = file_item.get('path', '')
                    screen_id = f"jsp_{Path(file_path).stem}" if file_path else None
                    
                    if screen_id:
                        screen_info = {
                            'id': screen_id,
                            'file_path': file_path,
                            'name': Path(file_path).stem,
                            'title': None,
                            'menu_context': [],
                            'navigation_hints': [],
                            'security_tags': [],
                            'includes': [],
                            'forms': [],
                            'tables': []
                        }
                        
                        # Extract JSP details
                        jsp_tags = details.get('jsp_tags', [])
                        for tag in jsp_tags:
                            if isinstance(tag, dict):
                                tag_name = tag.get('tag_name', '')
                                tag_text = tag.get('full_text', '')
                                
                                # Look for title/header tags
                                if 'title' in tag_name.lower() or 'header' in tag_name.lower():
                                    title_content = tag.get('content', '') or tag_text
                                    if title_content and not screen_info['title']:
                                        screen_info['title'] = title_content[:100]
                                
                                # Look for security tags
                                if tag_name.startswith('sec:') or 'security' in tag_name.lower():
                                    screen_info['security_tags'].append({
                                        'tag': tag_name,
                                        'text': tag_text[:200]
                                    })
                                
                                # Look for include/navigation tags
                                if 'include' in tag_name.lower() or 'import' in tag_name.lower():
                                    include_path = tag.get('content', '') or tag_text
                                    if include_path:
                                        screen_info['includes'].append(include_path)
                        
                        # Extract menu context from file path
                        path_segments = Path(file_path).parts
                        if len(path_segments) > 1:
                            # Remove common prefixes and file extension
                            meaningful_segments = []
                            for segment in path_segments[:-1]:  # Exclude filename
                                if segment.lower() not in {'web-inf', 'jsp', 'pages', 'views', 'webapp'}:
                                    meaningful_segments.append(segment)
                            screen_info['menu_context'] = meaningful_segments
                        
                        # Extract pattern hits for business context
                        pattern_hits = details.get('pattern_hits', {})
                        if isinstance(pattern_hits, dict):
                            for pattern_type, hits in pattern_hits.items():
                                if hits and isinstance(hits, list):
                                    screen_info['navigation_hints'].extend([
                                        f"{pattern_type}: {hit}" for hit in hits[:3]
                                    ])
                        
                        self.screens[screen_id] = screen_info
        
        except Exception as e:
            print(f"Error extracting screens from Step02: {e}")

    def extract_entities_from_step04(self, step04_data: Dict[str, Any]) -> None:
        """Extract routes and other entities from Step04."""
        try:
            entities = step04_data.get('entities', [])
            
            for entity in entities:
                if not isinstance(entity, dict):
                    continue
                
                entity_type = entity.get('type')
                entity_id = entity.get('id')
                entity_name = entity.get('name', entity_id)
                attributes = entity.get('attributes', {})
                
                if entity_type == 'Route' and entity_id:
                    route_info = {
                        'id': entity_id,
                        'name': entity_name,
                        'path': attributes.get('path', ''),
                        'method': attributes.get('method', ''),
                        'action': attributes.get('action', ''),
                        'action_class': attributes.get('action_class', ''),
                        'result_jsp': attributes.get('result_jsp', ''),
                        'url_segments': [],
                        'subdomain_hints': []
                    }
                    
                    # Parse URL path for business context
                    path = route_info['path']
                    if path:
                        segments = [s for s in path.split('/') if s and s != '']
                        route_info['url_segments'] = segments
                        
                        # Extract potential subdomains from path
                        if segments:
                            # First segment often indicates business area
                            primary_segment = segments[0].lower()
                            route_info['subdomain_hints'].append(primary_segment)
                            
                            # Second segment might indicate function
                            if len(segments) > 1:
                                secondary_segment = segments[1].lower()
                                route_info['subdomain_hints'].append(f"{primary_segment}_{secondary_segment}")
                    
                    self.routes[entity_id] = route_info
                
                elif entity_type == 'JSP' and entity_id:
                    # Update screen info with Step04 details if we have it
                    if entity_id in self.screens:
                        self.screens[entity_id].update({
                            'step04_name': entity_name,
                            'step04_attributes': attributes
                        })
                    elif entity_id not in self.screens:
                        # Create minimal screen entry from Step04
                        self.screens[entity_id] = {
                            'id': entity_id,
                            'name': entity_name,
                            'file_path': attributes.get('file', ''),
                            'title': attributes.get('title', ''),
                            'menu_context': [],
                            'step04_attributes': attributes
                        }
        
        except Exception as e:
            print(f"Error extracting entities from Step04: {e}")

    def extract_relationships_from_step04(self, step04_data: Dict[str, Any]) -> None:
        """Extract key relationships from Step04."""
        try:
            relations = step04_data.get('relations', [])
            entities = {e.get('id'): e for e in step04_data.get('entities', []) if isinstance(e, dict)}
            
            for relation in relations:
                if not isinstance(relation, dict):
                    continue
                
                rel_type = relation.get('type')
                from_id = relation.get('from_id')
                to_id = relation.get('to_id')
                rationale = relation.get('rationale', '')
                evidence = relation.get('evidence', [])
                
                # Route -> Screen mappings (renders relationship)
                if rel_type == 'renders':
                    from_entity = entities.get(from_id, {})
                    to_entity = entities.get(to_id, {})
                    
                    if from_entity.get('type') == 'Route' and to_entity.get('type') == 'JSP':
                        mapping = {
                            'route_id': from_id,
                            'route_name': from_entity.get('name', ''),
                            'route_path': from_entity.get('attributes', {}).get('path', ''),
                            'screen_id': to_id,
                            'screen_name': to_entity.get('name', ''),
                            'screen_file': to_entity.get('attributes', {}).get('file', ''),
                            'rationale': rationale,
                            'evidence_count': len(evidence) if evidence else 0
                        }
                        self.route_screen_mappings.append(mapping)
                
                # Screen/Route -> Data mappings (CRUD relationships)
                elif rel_type in ['readsFrom', 'writesTo', 'deletesFrom']:
                    from_entity = entities.get(from_id, {})
                    to_entity = entities.get(to_id, {})
                    
                    if (from_entity.get('type') in ['Route', 'JSP', 'JavaMethod'] and
                        to_entity.get('type') == 'Table'):
                        
                        mapping = {
                            'source_id': from_id,
                            'source_type': from_entity.get('type'),
                            'source_name': from_entity.get('name', ''),
                            'operation': rel_type,
                            'table_id': to_id,
                            'table_name': to_entity.get('name', ''),
                            'rationale': rationale,
                            'evidence_count': len(evidence) if evidence else 0
                        }
                        self.screen_data_mappings.append(mapping)
                
                # Security relationships
                elif rel_type == 'securedBy':
                    from_entity = entities.get(from_id, {})
                    to_entity = entities.get(to_id, {})
                    
                    security_pattern = {
                        'secured_id': from_id,
                        'secured_type': from_entity.get('type'),
                        'secured_name': from_entity.get('name', ''),
                        'role_id': to_id,
                        'role_name': to_entity.get('name', ''),
                        'rationale': rationale,
                        'evidence_count': len(evidence) if evidence else 0
                    }
                    self.security_patterns.append(security_pattern)
        
        except Exception as e:
            print(f"Error extracting relationships from Step04: {e}")

    def analyze_menu_hierarchies(self) -> None:
        """Analyze potential menu hierarchies from screen paths and navigation."""
        try:
            # Group screens by menu context
            menu_groups = defaultdict(list)
            
            for screen_id, screen_info in self.screens.items():
                menu_context = screen_info.get('menu_context', [])
                
                if menu_context:
                    # Create hierarchical path
                    for i in range(len(menu_context)):
                        path = ' > '.join(menu_context[:i+1])
                        menu_groups[path].append({
                            'screen_id': screen_id,
                            'screen_name': screen_info.get('name', ''),
                            'full_path': screen_info.get('file_path', ''),
                            'level': i + 1
                        })
            
            # Convert to hierarchy list
            for menu_path, screens in menu_groups.items():
                if len(screens) > 1:  # Only include paths with multiple screens
                    hierarchy = {
                        'menu_path': menu_path,
                        'level': len(menu_path.split(' > ')),
                        'screen_count': len(screens),
                        'screens': screens
                    }
                    self.menu_hierarchies.append(hierarchy)
            
            # Sort by level and screen count
            self.menu_hierarchies.sort(key=lambda x: (x['level'], -x['screen_count']))
        
        except Exception as e:
            print(f"Error analyzing menu hierarchies: {e}")

    def extract_architectural_subdomains(self) -> None:
        """Extract architectural subdomain patterns from routes and screens."""
        try:
            # Collect subdomain hints from various sources
            subdomain_patterns: Dict[str, int] = defaultdict(int)
            
            # From route URL segments
            for route_info in self.routes.values():
                for hint in route_info.get('subdomain_hints', []):
                    subdomain_patterns[hint] += 1
            
            # From screen menu contexts
            for screen_info in self.screens.values():
                menu_context = screen_info.get('menu_context', [])
                for context in menu_context:
                    if context and context.lower() not in {'jsp', 'pages', 'views'}:
                        subdomain_patterns[context.lower()] += 1
            
            # Filter and store significant patterns
            significant_subdomains = {
                pattern: count for pattern, count in subdomain_patterns.items()
                if count >= 2 and len(pattern) > 2  # At least 2 occurrences and meaningful length
            }
            
            self.architectural_subdomains = set(significant_subdomains.keys())
        
        except Exception as e:
            print(f"Error extracting architectural subdomains: {e}")

    def generate_analysis_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        # Group screens by potential business domains
        domain_candidates = defaultdict(list)
        
        # Group by menu hierarchy
        for screen_id, screen_info in self.screens.items():
            menu_context = screen_info.get('menu_context', [])
            primary_context = menu_context[0] if menu_context else 'uncategorized'
            domain_candidates[f"menu_{primary_context}"].append(screen_id)
        
        # Group by route URL patterns
        route_domain_candidates = defaultdict(list)
        for route_id, route_info in self.routes.items():
            url_segments = route_info.get('url_segments', [])
            primary_segment = url_segments[0] if url_segments else 'uncategorized'
            route_domain_candidates[f"url_{primary_segment}"].append(route_id)
        
        # Security patterns by domain
        security_by_domain = defaultdict(list)
        for pattern in self.security_patterns:
            # Try to match to screen domains
            secured_id = pattern['secured_id']
            if secured_id in self.screens:
                screen_info = self.screens[secured_id]
                menu_context = screen_info.get('menu_context', [])
                primary_context = menu_context[0] if menu_context else 'uncategorized'
                security_by_domain[primary_context].append(pattern)
        
        # Data usage patterns by domain
        data_by_domain: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        for mapping in self.screen_data_mappings:
            source_id = mapping['source_id']
            table_name = mapping['table_name']
            operation = mapping['operation']
            
            # Try to associate with screen domain
            domain = 'uncategorized'
            if source_id in self.screens:
                screen_info = self.screens[source_id]
                menu_context = screen_info.get('menu_context', [])
                if menu_context:
                    domain = menu_context[0]
            
            data_by_domain[domain][operation].add(table_name)
        
        return {
            'project': self.project_name,
            'summary': {
                'total_screens': len(self.screens),
                'total_routes': len(self.routes),
                'route_screen_mappings': len(self.route_screen_mappings),
                'screen_data_mappings': len(self.screen_data_mappings),
                'security_patterns': len(self.security_patterns),
                'menu_hierarchies': len(self.menu_hierarchies),
                'architectural_subdomains': len(self.architectural_subdomains)
            },
            'screens': dict(list(self.screens.items())[:10]),  # Sample
            'routes': dict(list(self.routes.items())[:10]),    # Sample
            'route_screen_mappings': self.route_screen_mappings,
            'menu_hierarchies': self.menu_hierarchies,
            'architectural_subdomains': sorted(list(self.architectural_subdomains)),
            'domain_analysis': {
                'screen_domain_candidates': {k: len(v) for k, v in domain_candidates.items()},
                'route_domain_candidates': {k: len(v) for k, v in route_domain_candidates.items()},
                'security_by_domain': {k: len(v) for k, v in security_by_domain.items()},
                'data_usage_by_domain': {
                    domain: {op: len(tables) for op, tables in ops.items()}
                    for domain, ops in data_by_domain.items()
                }
            }
        }

    def run_extraction(self) -> Dict[str, Any]:
        """Run the complete extraction process."""
        print(f"Extracting domain analysis data for project: {self.project_name}")
        
        # Load data
        step02_data = self.load_step02_data()
        step04_data = self.load_step04_data()
        
        if not step02_data and not step04_data:
            raise ValueError("No Step02 or Step04 data available")
        
        # Extract data
        if step02_data:
            print("Extracting screens from Step02...")
            self.extract_screens_from_step02(step02_data)
        
        if step04_data:
            print("Extracting entities from Step04...")
            self.extract_entities_from_step04(step04_data)
            print("Extracting relationships from Step04...")
            self.extract_relationships_from_step04(step04_data)
        
        # Analyze patterns
        print("Analyzing menu hierarchies...")
        self.analyze_menu_hierarchies()
        print("Extracting architectural subdomains...")
        self.extract_architectural_subdomains()
        
        # Generate report
        print("Generating analysis report...")
        return self.generate_analysis_report()


def main() -> None:
    project = sys.argv[1] if len(sys.argv) > 1 else "ct-hr-storm"
    
    try:
        extractor = DomainAnalysisExtractor(project)
        report = extractor.run_extraction()
        
        # Write report
        output_path = ROOT / "projects" / project / "output" / "domain_analysis_data.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\nDomain analysis data written to: {output_path}")
        
        # Print summary
        summary = report['summary']
        print("\n=== SUMMARY ===")
        print(f"Screens found: {summary['total_screens']}")
        print(f"Routes found: {summary['total_routes']}")
        print(f"Route->Screen mappings: {summary['route_screen_mappings']}")
        print(f"Screen->Data mappings: {summary['screen_data_mappings']}")
        print(f"Security patterns: {summary['security_patterns']}")
        print(f"Menu hierarchies: {summary['menu_hierarchies']}")
        print(f"Architectural subdomains: {summary['architectural_subdomains']}")
        
        # Print domain candidates
        domain_analysis = report['domain_analysis']
        print("\n=== POTENTIAL BUSINESS DOMAINS ===")
        print("Screen-based domain candidates:")
        for domain, count in sorted(domain_analysis['screen_domain_candidates'].items()):
            print(f"  {domain}: {count} screens")
        
        print("\nRoute-based domain candidates:")
        for domain, count in sorted(domain_analysis['route_domain_candidates'].items()):
            print(f"  {domain}: {count} routes")
        
        print("\n=== ARCHITECTURAL SUBDOMAINS ===")
        for subdomain in sorted(report['architectural_subdomains']):
            print(f"  {subdomain}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
