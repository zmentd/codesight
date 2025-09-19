#!/usr/bin/env python3
"""
Analyze JSP detection in CodeSight vs actual file count.
"""

import json
import os
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]

def count_actual_jsp_files(project_root: str) -> int:
    """Count actual JSP files in project directory."""
    jsp_count = 0
    for root, dirs, files in os.walk(project_root):
        for file in files:
            if file.endswith('.jsp'):
                jsp_count += 1
    return jsp_count

def analyze_step02_jsp_detection(project: str) -> Dict:
    """Analyze what Step02 detected as JSP files."""
    step02_path = ROOT / "projects" / project / "output" / "step02_output.json"
    
    if not step02_path.exists():
        return {"error": f"Step02 output not found: {step02_path}"}
    
    try:
        with open(step02_path, 'r', encoding='utf-8') as f:
            step02_data = json.load(f)
        
        files = step02_data.get('files', [])
        jsp_files = [f for f in files if f.get('name', '').endswith('.jsp')]
        
        return {
            'total_files_detected': len(files),
            'jsp_files_detected': len(jsp_files),
            'sample_jsp_paths': [f.get('relative_path', '') for f in jsp_files[:10]]
        }
    except Exception as e:
        return {"error": f"Failed to read Step02 output: {e}"}

def analyze_step04_jsp_entities(project: str) -> Dict:
    """Analyze JSP entities in Step04 output."""
    step04_path = ROOT / "projects" / project / "output" / "step04_output.json"
    
    if not step04_path.exists():
        return {"error": f"Step04 output not found: {step04_path}"}
    
    try:
        with open(step04_path, 'r', encoding='utf-8') as f:
            step04_data = json.load(f)
        
        entities = step04_data.get('entities', [])
        jsp_entities = [e for e in entities if e.get('type') == 'JSP']
        
        # Count different path patterns
        jsp_paths = []
        web_paths = []  # /jsp/ prefix paths
        other_paths = []
        
        for jsp in jsp_entities:
            attrs = jsp.get('attributes', {})
            file_path = attrs.get('file_path') or attrs.get('file', '')
            
            if file_path:
                jsp_paths.append(file_path)
                if file_path.startswith('/jsp/'):
                    web_paths.append(file_path)
                else:
                    other_paths.append(file_path)
        
        return {
            'total_jsp_entities': len(jsp_entities),
            'with_file_paths': len(jsp_paths),
            'web_context_paths': len(web_paths),  # /jsp/ prefix
            'other_paths': len(other_paths),
            'sample_web_paths': web_paths[:5],
            'sample_other_paths': other_paths[:5]
        }
    except Exception as e:
        return {"error": f"Failed to read Step04 output: {e}"}

def main() -> None:
    project = "ct-hr-storm"
    project_root = f"d:\\Prj\\NBCU\\storm\\{project}"
    
    print(f"=== JSP Count Analysis for {project} ===\n")
    
    # Count actual files
    actual_count = count_actual_jsp_files(project_root)
    print(f"Actual JSP files in project: {actual_count}")
    
    # Analyze Step02 detection
    step02_analysis = analyze_step02_jsp_detection(project)
    print(f"\n=== Step02 Detection ===")
    if 'error' in step02_analysis:
        print(f"Error: {step02_analysis['error']}")
    else:
        print(f"Total files detected: {step02_analysis['total_files_detected']}")
        print(f"JSP files detected: {step02_analysis['jsp_files_detected']}")
        print(f"Sample JSP paths:")
        for path in step02_analysis['sample_jsp_paths']:
            print(f"  {path}")
    
    # Analyze Step04 entities
    step04_analysis = analyze_step04_jsp_entities(project)
    print(f"\n=== Step04 JSP Entities ===")
    if 'error' in step04_analysis:
        print(f"Error: {step04_analysis['error']}")
    else:
        print(f"JSP entities created: {step04_analysis['total_jsp_entities']}")
        print(f"With file paths: {step04_analysis['with_file_paths']}")
        print(f"Web context paths (/jsp/): {step04_analysis['web_context_paths']}")
        print(f"Other paths: {step04_analysis['other_paths']}")
        
        print(f"\nSample web context paths:")
        for path in step04_analysis['sample_web_paths']:
            print(f"  {path}")
        
        print(f"\nSample other paths:")
        for path in step04_analysis['sample_other_paths']:
            print(f"  {path}")
    
    print(f"\n=== ANALYSIS ===")
    print(f"Actual JSP files: {actual_count}")
    if 'jsp_files_detected' in step02_analysis:
        print(f"Step02 detected: {step02_analysis['jsp_files_detected']}")
    if 'total_jsp_entities' in step04_analysis:
        print(f"Step04 entities: {step04_analysis['total_jsp_entities']}")
        print(f"Step04 /jsp/ paths: {step04_analysis['web_context_paths']}")
    
    print(f"\n=== KEY FINDING ===")
    print(f"The analysis script only counts JSP entities with '/jsp/' prefix paths.")
    print(f"But actual JSP files are in WebContent and other directories.")
    print(f"Step04 creates entities with logical '/jsp/' paths, not physical file paths.")
    print(f"This means Step04 maps {step04_analysis.get('web_context_paths', 'N/A')} logical screens to business domains.")

if __name__ == "__main__":
    main()
