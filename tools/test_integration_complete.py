"""
Test d'intégration: validation complète des 4 couches
Teste IHE PAM + HAPI + HL7 v2.5 base + Types de données complexes
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.pam_validation import validate_pam

# Message réaliste avec plusieurs problèmes sur différentes couches
test_message = """MSH|^~\\&|SendingApp|SendFac|ReceivingApp|RecvFac|20240101120000||ADT^A01^ADT_A01|MSG001|P|2.5
EVN|A01|20240101120000
PID|1||^123456^M10^HOSP||^^MIDDLE^JR||198099XX|M||||123 Rue^^Paris^^^^H||^^^^^BADEQUIP
PV1|1|X|^^^|||^"""

print("="*80)
print("TEST D'INTÉGRATION - VALIDATION COMPLÈTE (4 COUCHES)")
print("="*80)
print("\nMessage de test:")
print("-"*80)
print(test_message)
print("-"*80)

result = validate_pam(test_message, "inbound", "IHE_PAM_FR")

print(f"\nRésultat:")
print(f"  Valid: {result.is_valid}")
print(f"  Level: {result.level}")
print(f"  Event: {result.event}")
print(f"  Issues: {len(result.issues)}")

print(f"\nProblèmes détectés par couche:")
print("-"*80)

# Classifier les issues par couche
ihe_pam = []
hapi = []
hl7_base = []
datatypes = []

for issue in result.issues:
    code = issue.code
    # Classification basée sur les codes d'erreur
    if code.startswith("PV1_MISSING") or code.startswith("EVN_MISSING") or code.startswith("PID_MISSING"):
        ihe_pam.append(issue)
    elif "SEGMENT" in code or code.endswith("_REQUIRED") or code.endswith("_FORBIDDEN"):
        hapi.append(issue)
    elif code.startswith("MSH") or code.startswith("EVN_MISMATCH"):
        hl7_base.append(issue)
    elif "_CX_" in code or "_XPN_" in code or "_XAD_" in code or "_XTN_" in code or "_TS_" in code or code.startswith("PV1_2") or code.startswith("PV1_3") or code.startswith("PV1_7"):
        datatypes.append(issue)
    else:
        # Autre
        hl7_base.append(issue)

print(f"\n1. IHE PAM ({len(ihe_pam)} issues):")
for issue in ihe_pam:
    print(f"   [{issue.severity}] {issue.code}: {issue.message}")

print(f"\n2. HAPI Structures ({len(hapi)} issues):")
for issue in hapi:
    print(f"   [{issue.severity}] {issue.code}: {issue.message}")

print(f"\n3. HL7 v2.5 Base ({len(hl7_base)} issues):")
for issue in hl7_base:
    print(f"   [{issue.severity}] {issue.code}: {issue.message}")

print(f"\n4. Types de Données Complexes ({len(datatypes)} issues):")
for issue in datatypes:
    print(f"   [{issue.severity}] {issue.code}: {issue.message}")

print("\n" + "="*80)
print("RÉSUMÉ")
print("="*80)
print(f"Total issues: {len(result.issues)}")
print(f"  - Errors: {sum(1 for i in result.issues if i.severity == 'error')}")
print(f"  - Warnings: {sum(1 for i in result.issues if i.severity == 'warn')}")
print(f"  - Info: {sum(1 for i in result.issues if i.severity == 'info')}")
print(f"\nValidation finale: {'✓ PASS (warnings only)' if result.is_valid else '✗ FAIL (errors found)'}")
print(f"Niveau: {result.level}")
print("="*80)
