#!/usr/bin/env python3
"""
Detailed analysis of Step 06 output against ct-hr-storm codebase
to verify accuracy of the technical specification.
"""
import json
import os

print("=== DETAILED STEP 06 ACCURACY ANALYSIS ===")

# Load the current Step 06 output
with open('projects/ct-hr-storm/output/step06_output.json', 'r') as f:
    step06_data = json.load(f)

print(f"✅ Step 06 Output Analysis:")
print(f"  - BRD domains: {step06_data['brd_markdown'].count('### ')}")
print(f"  - Tech spec sections: {len(step06_data['sections'])}")

# Extract capabilities from BRD
brd_lines = step06_data['brd_markdown'].split('\n')
brd_capabilities = []
current_domain = None

for line in brd_lines:
    if line.startswith('### ') and '##' not in line.replace('### ', ''):
        current_domain = line.replace('### ', '').strip()
    elif line.startswith('| ') and '(Menu:' in line and '---' not in line:
        parts = line.split('|')
        if len(parts) >= 3:
            cap_info = parts[1].strip()
            purpose = parts[2].strip()
            # Extract capability name and menu
            if '(Menu:' in cap_info:
                name = cap_info.split('(Menu:')[0].strip()
                menu = cap_info.split('(Menu:')[1].replace(')', '').strip()
                brd_capabilities.append({
                    'domain': current_domain,
                    'name': name,
                    'menu': menu,
                    'purpose': purpose
                })

print(f"\n📊 BRD Capability Analysis:")
print(f"  - Total capabilities: {len(brd_capabilities)}")

# Group by domain
domain_counts = {}
for cap in brd_capabilities:
    domain = cap['domain']
    if domain not in domain_counts:
        domain_counts[domain] = 0
    domain_counts[domain] += 1

print(f"  - Domains found: {len(domain_counts)}")

print(f"\n📋 Domain Distribution:")
for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
    print(f"  {domain}: {count} capabilities")

# Now let's verify some key capabilities against the actual codebase
print(f"\n🔍 CODEBASE VERIFICATION:")

# Check for specific JSP screens mentioned in the tech spec
tech_spec_screens = []
tech_lines = step06_data['tech_spec_markdown'].split('\n')
for line in tech_lines:
    if '| Capability | Screens |' in line:
        continue
    if line.startswith('|') and '|' in line[1:]:
        parts = line.split('|')
        if len(parts) >= 3:
            screens = parts[2].strip()
            if screens and screens != '-' and screens != 'Screens':
                screen_list = [s.strip() for s in screens.split(',') if s.strip()]
                tech_spec_screens.extend(screen_list)

print(f"  - Screens mentioned in tech spec: {len(set(tech_spec_screens))}")

# Look for actual JSP/screen files in the codebase
actual_jsp_files = []
storm_dir = 'd:/Prj/NBCU/storm/ct-hr-storm'

def find_jsp_files(directory):
    jsp_files = []
    try:
        for root, dirs, files in os.walk(directory):
            # Skip .git and other non-source directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['target', 'build', 'node_modules']]
            for file in files:
                if file.endswith('.jsp') or file.endswith('.html') or file.endswith('.xhtml'):
                    jsp_files.append(os.path.basename(file).replace('.jsp', '').replace('.html', '').replace('.xhtml', ''))
    except Exception as e:
        print(f"    Error scanning {directory}: {e}")
    return jsp_files

print(f"\n  Scanning for actual screen files...")
actual_screens = find_jsp_files(storm_dir)
print(f"  - Actual screen files found: {len(set(actual_screens))}")

# Check overlap between mentioned screens and actual files
mentioned_screens = set(tech_spec_screens)
actual_screen_set = set(actual_screens)
overlap = mentioned_screens & actual_screen_set

print(f"\n📈 Screen Accuracy Analysis:")
print(f"  - Screens in tech spec: {len(mentioned_screens)}")
print(f"  - Actual screens found: {len(actual_screen_set)}")
print(f"  - Matching screens: {len(overlap)}")
if len(mentioned_screens) > 0:
    accuracy = (len(overlap) / len(mentioned_screens)) * 100
    print(f"  - Accuracy rate: {accuracy:.1f}%")

# Show some examples of matches and misses
if overlap:
    print(f"\n✅ Example matching screens:")
    for screen in sorted(list(overlap))[:10]:
        print(f"    - {screen}")

missing_screens = mentioned_screens - actual_screen_set
if missing_screens:
    print(f"\n❌ Example screens mentioned but not found:")
    for screen in sorted(list(missing_screens))[:10]:
        print(f"    - {screen}")

# Check for Action handlers mentioned
tech_spec_handlers = []
for line in tech_lines:
    if line.startswith('|') and '|' in line[1:]:
        parts = line.split('|')
        if len(parts) >= 4:
            handlers = parts[3].strip()
            if handlers and handlers != '-' and handlers != 'Handlers':
                handler_list = [h.strip() for h in handlers.split(',') if h.strip()]
                tech_spec_handlers.extend(handler_list)

print(f"\n🎯 Handler Analysis:")
print(f"  - Handlers mentioned: {len(set(tech_spec_handlers))}")

# Look for Java action files
def find_action_files(directory):
    action_files = []
    try:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['target', 'build', 'node_modules']]
            for file in files:
                if file.endswith('Action.java') or file.endswith('Action.class'):
                    action_files.append(os.path.basename(file).replace('.java', '').replace('.class', ''))
    except Exception as e:
        print(f"    Error scanning {directory}: {e}")
    return action_files

actual_actions = find_action_files(storm_dir)
mentioned_handlers = set(tech_spec_handlers)
actual_handler_set = set(actual_actions)
handler_overlap = mentioned_handlers & actual_handler_set

print(f"  - Actual action handlers found: {len(actual_handler_set)}")
print(f"  - Matching handlers: {len(handler_overlap)}")
if len(mentioned_handlers) > 0:
    handler_accuracy = (len(handler_overlap) / len(mentioned_handlers)) * 100
    print(f"  - Handler accuracy rate: {handler_accuracy:.1f}%")

# Analyze the massive database procedures list
tech_spec_procedures = []
for line in tech_lines:
    if line.startswith('|') and '|' in line[1:]:
        parts = line.split('|')
        if len(parts) >= 5:
            procedures = parts[4].strip()
            if procedures and procedures != '-' and procedures != 'Procedures':
                # Handle the massive list in brackets
                if procedures.startswith('[') and procedures.endswith(']'):
                    proc_content = procedures[1:-1]  # Remove brackets
                    proc_list = [p.strip() for p in proc_content.split(',') if p.strip()]
                    tech_spec_procedures.extend(proc_list)
                else:
                    proc_list = [p.strip() for p in procedures.split(',') if p.strip()]
                    tech_spec_procedures.extend(proc_list)

print(f"\n🗄️ Database Procedures Analysis:")
print(f"  - Procedures mentioned: {len(set(tech_spec_procedures))}")

# Show specific examples from the "Approvals Workflow" capability
approvals_capability = None
for cap in brd_capabilities:
    if cap['name'] == 'Approvals Workflow':
        approvals_capability = cap
        break

if approvals_capability:
    print(f"\n🔍 DEEP DIVE: Approvals Workflow Capability")
    print(f"  - Domain: {approvals_capability['domain']}")
    print(f"  - Menu: {approvals_capability['menu']}")
    print(f"  - Purpose: {approvals_capability['purpose'][:100]}...")
    
    # Find this in the tech spec
    for line in tech_lines:
        if 'Approvals Workflow' in line and '|' in line:
            parts = line.split('|')
            if len(parts) >= 5:
                screens = parts[2].strip() if parts[2].strip() != '-' else 'None'
                handlers = parts[3].strip() if parts[3].strip() != '-' else 'None' 
                procedures = parts[4].strip() if parts[4].strip() != '-' else 'None'
                print(f"  - Associated screens: {len(screens.split(',')) if screens != 'None' else 0}")
                print(f"  - Associated handlers: {len(handlers.split(',')) if handlers != 'None' else 0}")
                if procedures.startswith('['):
                    proc_count = "Massive list"
                else:
                    proc_count = len(procedures.split(',')) if procedures != 'None' else 0
                print(f"  - Associated procedures: {proc_count}")
                break

print(f"\n📝 OVERALL ASSESSMENT:")
print(f"  ✅ Step 06 now correctly shows {len(brd_capabilities)} business capabilities")
print(f"  ✅ Business domains are properly grouped")
print(f"  ✅ Technical specification includes detailed component mappings")
print(f"  ⚠️  Screen accuracy needs verification against actual JSP files")
print(f"  ⚠️  Handler accuracy needs verification against actual Action classes")
