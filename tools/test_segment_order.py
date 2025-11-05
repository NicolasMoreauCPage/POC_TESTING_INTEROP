"""
Test de validation de l'ordre des segments selon structures HAPI
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.pam_validation import validate_pam

print("="*80)
print("TEST VALIDATION ORDRE DES SEGMENTS")
print("="*80)

# Test 1: Message avec ordre correct (ADT A01)
test1_correct = """MSH|^~\\&|SendApp|SendFac|RecvApp|RecvFac|20240101120000||ADT^A01^ADT_A01|MSG001|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^HOSP||DOE^JOHN||19800101
PV1|1|I|WARD^101^A|||DOC123^SMITH^JANE
PV2|1|||||||||||||||||||||||||||||||||||||||||20240101
ZBE|MOVEMENT|UF001|SERVICE001"""

print("\nTest 1: Ordre CORRECT (MSH, EVN, PID, PV1, PV2, ZBE)")
print("-"*80)
result1 = validate_pam(test1_correct, "inbound", "IHE_PAM_FR")
order_issues = [i for i in result1.issues if "ORDER" in i.code]
if order_issues:
    print(f"Issues d'ordre trouvées: {len(order_issues)}")
    for issue in order_issues:
        print(f"  [{issue.severity}] {issue.code}: {issue.message}")
else:
    print("Aucun problème d'ordre détecté (OK)")

# Test 2: Message avec PV1 et PID inversés (INCORRECT)
test2_wrong = """MSH|^~\\&|SendApp|SendFac|RecvApp|RecvFac|20240101120000||ADT^A01^ADT_A01|MSG002|P|2.5
EVN|A01|20240101120000
PV1|1|I|WARD^101^A|||DOC123^SMITH^JANE
PID|1||123456^^^HOSP||DOE^JOHN||19800101
PV2|1|||||||||||||||||||||||||||||||||||||||||20240101
ZBE|MOVEMENT|UF001|SERVICE001"""

print("\nTest 2: Ordre INCORRECT (MSH, EVN, PV1, PID - PID devrait être avant PV1)")
print("-"*80)
result2 = validate_pam(test2_wrong, "inbound", "IHE_PAM_FR")
order_issues2 = [i for i in result2.issues if "ORDER" in i.code]
if order_issues2:
    print(f"Issues d'ordre trouvées: {len(order_issues2)} (attendu)")
    for issue in order_issues2:
        print(f"  [{issue.severity}] {issue.code}: {issue.message}")
else:
    print("Aucun problème d'ordre détecté (INCORRECT - devrait détecter une erreur!)")

# Test 3: Message avec ZBE avant PV1 (INCORRECT)
test3_wrong = """MSH|^~\\&|SendApp|SendFac|RecvApp|RecvFac|20240101120000||ADT^A01^ADT_A01|MSG003|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^HOSP||DOE^JOHN||19800101
ZBE|MOVEMENT|UF001|SERVICE001
PV1|1|I|WARD^101^A|||DOC123^SMITH^JANE
PV2|1|||||||||||||||||||||||||||||||||||||||||20240101"""

print("\nTest 3: Ordre INCORRECT (MSH, EVN, PID, ZBE, PV1, PV2 - ZBE devrait être après PV2)")
print("-"*80)
result3 = validate_pam(test3_wrong, "inbound", "IHE_PAM_FR")
order_issues3 = [i for i in result3.issues if "ORDER" in i.code]
if order_issues3:
    print(f"Issues d'ordre trouvées: {len(order_issues3)} (attendu)")
    for issue in order_issues3:
        print(f"  [{issue.severity}] {issue.code}: {issue.message}")
else:
    print("Aucun problème d'ordre détecté (INCORRECT - devrait détecter une erreur!)")

# Test 4: Message A28 (identity) avec ordre correct
test4_correct = """MSH|^~\\&|SendApp|SendFac|RecvApp|RecvFac|20240101120000||ADT^A28^ADT_A28|MSG004|P|2.5
EVN|A28|20240101120000
PID|1||123456^^^HOSP||DOE^JOHN||19800101
PD1|||||||||||||||||||||20240101
NK1|1|DOE^JANE|SPO|123 Main St||||||||||||||||||||||||||||||||||
ZPA|INFO1|INFO2"""

print("\nTest 4: A28 ordre CORRECT (MSH, EVN, PID, PD1, NK1, ZPA)")
print("-"*80)
result4 = validate_pam(test4_correct, "inbound", "IHE_PAM_FR")
order_issues4 = [i for i in result4.issues if "ORDER" in i.code]
if order_issues4:
    print(f"Issues d'ordre trouvées: {len(order_issues4)}")
    for issue in order_issues4:
        print(f"  [{issue.severity}] {issue.code}: {issue.message}")
else:
    print("Aucun problème d'ordre détecté (OK)")

print("\n" + "="*80)
print("RÉSUMÉ")
print("="*80)
print(f"Test 1 (ordre correct): {len([i for i in result1.issues if 'ORDER' in i.code])} issues ordre (attendu: 0)")
print(f"Test 2 (PID/PV1 inversés): {len([i for i in result2.issues if 'ORDER' in i.code])} issues ordre (attendu: >0)")
print(f"Test 3 (ZBE mal placé): {len([i for i in result3.issues if 'ORDER' in i.code])} issues ordre (attendu: >0)")
print(f"Test 4 (A28 correct): {len([i for i in result4.issues if 'ORDER' in i.code])} issues ordre (attendu: 0)")
print("="*80)
