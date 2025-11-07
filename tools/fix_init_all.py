#!/usr/bin/env python3
"""
Script to fix tools/init_all.py:
- Replace all uf_responsabilite with 3 separate fields
- HDJ (hospital de jour) = outpatient A04 → uf_medicale only
- HOSP = inpatient A01 → uf_medicale + uf_hebergement
"""

import re

def fix_init_all():
    file_path = "tools/init_all.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix Dossier instantiations: uf_responsabilite="X" → uf_medicale="X", uf_hebergement="X" (if HOSP) or just uf_medicale (if HDJ)
    # Pattern: Dossier(...uf_responsabilite="SOMETHING",...)
    def replace_dossier_uf(match):
        indent = match.group(1)
        uf_value = match.group(2)
        # Determine if it's hospitalization or outpatient
        if "HOSP" in uf_value:
            # Hospitalization: both medicale and hebergement
            return f'{indent}uf_medicale="{uf_value}",\n{indent}uf_hebergement="{uf_value}",'
        else:
            # Outpatient (HDJ): only medicale
            return f'{indent}uf_medicale="{uf_value}",'
    
    content = re.sub(
        r'(\s+)uf_responsabilite="([^"]+)",',
        replace_dossier_uf,
        content
    )
    
    # Fix Venue instantiations: same logic
    # Already covered by above regex
    
    # Fix Mouvement instantiations: remove uf_responsabilite, determine uf_medicale/uf_hebergement based on context
    # For A01 with HOSP: add uf_hebergement
    # For A01/A04 with HDJ: only uf_medicale
    
    # Pattern: Mouvement(...uf_responsabilite="X",...uf_medicale="Y",...)
    # Need to be smart: if it's A01 and location contains "HDJ" → only medicale
    # if it's A01 and location contains "MED" or "HOSP" → medicale + hebergement
    
    def replace_mouvement_uf(match):
        full_match = match.group(0)
        lines = full_match.split('\n')
        new_lines = []
        
        uf_resp_value = None
        uf_medicale_value = None
        location_value = None
        trigger_value = None
        
        # Parse existing values
        for line in lines:
            if 'uf_responsabilite=' in line:
                m = re.search(r'uf_responsabilite="([^"]+)"', line)
                if m:
                    uf_resp_value = m.group(1)
                continue  # Skip this line
            if 'uf_medicale=' in line:
                m = re.search(r'uf_medicale="([^"]+)"', line)
                if m:
                    uf_medicale_value = m.group(1)
            if 'location=' in line:
                m = re.search(r'location="([^"]+)"', line)
                if m:
                    location_value = m.group(1)
            if 'trigger_event=' in line:
                m = re.search(r'trigger_event="([^"]+)"', line)
                if m:
                    trigger_value = m.group(1)
            new_lines.append(line)
        
        # Determine if we need uf_hebergement
        add_hebergement = False
        if location_value and trigger_value in ('A01',):
            # Check if it's hospitalization (not HDJ)
            if 'MED' in location_value or 'HOSP' in location_value:
                add_hebergement = True
                # Extract UF from location (first part before dash)
                hebergement_uf = location_value.split('-')[0]
        
        # Reconstruct
        result_lines = []
        for line in lines:
            if 'uf_responsabilite=' in line:
                # Replace with uf_medicale if not already present
                if not any('uf_medicale=' in l for l in lines):
                    indent = len(line) - len(line.lstrip())
                    result_lines.append(' ' * indent + f'uf_medicale="{uf_resp_value}",')
                if add_hebergement and uf_resp_value:
                    indent = len(line) - len(line.lstrip())
                    result_lines.append(' ' * indent + f'uf_hebergement="{uf_resp_value}",')
                continue
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    # Simpler approach: use line-by-line replacement
    lines = content.split('\n')
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a Mouvement uf_responsabilite line
        if 'uf_responsabilite=' in line and i > 0:
            # Look back to see if we're in a Mouvement context
            context = '\n'.join(lines[max(0, i-15):i])
            if 'Mouvement(' in context:
                # Extract the UF value
                match = re.search(r'uf_responsabilite="([^"]+)"', line)
                if match:
                    uf_value = match.group(1)
                    indent = len(line) - len(line.lstrip())
                    
                    # Check if this is hospitalization or outpatient
                    # Look for location in nearby lines
                    location_line = None
                    for j in range(max(0, i-10), min(len(lines), i+5)):
                        if 'location=' in lines[j]:
                            location_line = lines[j]
                            break
                    
                    is_hospitalization = False
                    if location_line:
                        if 'MED-' in location_line or 'HOSP-' in location_line:
                            is_hospitalization = True
                    
                    # Replace the line
                    if is_hospitalization:
                        # Add both medicale and hebergement
                        new_lines.append(' ' * indent + f'uf_medicale="{uf_value}",')
                        new_lines.append(' ' * indent + f'uf_hebergement="{uf_value}",')
                    else:
                        # Only medicale
                        new_lines.append(' ' * indent + f'uf_medicale="{uf_value}",')
                    
                    i += 1
                    continue
        
        new_lines.append(line)
        i += 1
    
    content = '\n'.join(new_lines)
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Fixed {file_path}")

if __name__ == "__main__":
    fix_init_all()
