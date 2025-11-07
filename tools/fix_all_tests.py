#!/usr/bin/env python3
"""
Script to fix all test files:
- Replace uf_responsabilite with uf_medicale (and uf_hebergement for HOSP/TEST codes that indicate hospitalization)
"""

import os
import re
from pathlib import Path

def fix_test_file(file_path):
    """Fix a single test file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Strategy: Simple replacement for test fixtures
    # uf_responsabilite="X" → uf_medicale="X", (and possibly uf_hebergement if it looks like hospitalization)
    
    def replace_uf_resp(match):
        indent = match.group(1)
        uf_value = match.group(2)
        # If it's a hospitalization UF (contains TEST, HOSP, MED, or is generic), add both
        # If it's HDJ or clearly outpatient, only medicale
        if "HDJ" in uf_value:
            return f'{indent}uf_medicale="{uf_value}",'
        else:
            # Default to hospitalization (both medicale and hebergement)
            return f'{indent}uf_medicale="{uf_value}",\n{indent}uf_hebergement="{uf_value}",'
    
    # Fix Dossier(...uf_responsabilite="X",...)
    content = re.sub(
        r'(\s+)uf_responsabilite="([^"]+)",',
        replace_uf_resp,
        content
    )
    
    # Fix Venue(...uf_responsabilite="X",...)
    # Already covered by above
    
    # Fix assertions: dossier.uf_responsabilite == "X" → dossier.uf_medicale == "X"
    content = re.sub(
        r'\.uf_responsabilite\s*==\s*"([^"]+)"',
        r'.uf_medicale == "\1"',
        content
    )
    
    # Fix f-strings and assertions with .uf_responsabilite
    content = re.sub(
        r'\.uf_responsabilite',
        r'.uf_medicale',
        content
    )
    
    # Fix assert statements checking for uf_ fields
    # test_multi_venue_data.py: assert all(v.uf_responsabilite == "HDJ-ONCO" for v in venues)
    # → assert all(v.uf_medicale == "HDJ-ONCO" for v in venues)
    # Already covered by above
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Fixed {file_path}")
        return True
    else:
        print(f"  No changes needed in {file_path}")
        return False

def main():
    tests_dir = Path("tests")
    if not tests_dir.exists():
        print("Error: tests/ directory not found")
        return
    
    fixed_count = 0
    for test_file in tests_dir.glob("**/*.py"):
        if test_file.is_file():
            if fix_test_file(test_file):
                fixed_count += 1
    
    print(f"\n✓ Fixed {fixed_count} test files")

if __name__ == "__main__":
    main()
