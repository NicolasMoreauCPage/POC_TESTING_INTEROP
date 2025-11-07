#!/usr/bin/env python3
"""
Final cleanup: Replace all remaining uf_responsabilite references
"""
import re
from pathlib import Path

files_to_fix = [
    "app/services/z99_handler.py",
    "app/services/hl7_parser.py",
    "app/services/pam.py",
    "app/services/hl7_generator.py",
    "app/services/transport_inbound.py",
    "app/form_config.py",
]

for file_path in files_to_fix:
    path = Path(file_path)
    if not path.exists():
        print(f"⚠ Skipping {file_path} (not found)")
        continue
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replace attribute access: entity.uf_responsabilite → entity.uf_medicale (or conditional logic)
    # For getters: use uf_medicale or uf_hebergement as fallback
    content = re.sub(
        r'\.uf_responsabilite(\s|\)|\,|$)',
        r'.uf_medicale\1',
        content
    )
    
    # Replace dict key access: data["uf_responsabilite"] → data.get("uf_medicale") or data.get("uf_hebergement")
    # Simpler: just replace the key
    content = re.sub(
        r'"uf_responsabilite"',
        r'"uf_medicale"',
        content
    )
    content = re.sub(
        r"'uf_responsabilite'",
        r"'uf_medicale'",
        content
    )
    
    # Replace assignment: uf_responsabilite= → uf_medicale= (and possibly add uf_hebergement=)
    # This is more complex, but for forms, just replace
    content = re.sub(
        r'uf_responsabilite=',
        r'uf_medicale=',
        content
    )
    
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Fixed {file_path}")
    else:
        print(f"  No changes in {file_path}")

print("\n✓ Cleanup complete")
