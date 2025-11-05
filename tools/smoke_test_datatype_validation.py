"""
Test de validation des types de données complexes HL7 v2.5
Teste les validations CX, XPN, XAD, XTN, TS, PL, XCN
"""
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.pam_validation import validate_pam

def test_scenario(title: str, msg: str, expected_issues: list = None):
    """Teste un scénario et affiche les résultats."""
    print(f"\n{'='*80}")
    print(f"Test: {title}")
    print(f"{'='*80}")
    
    result = validate_pam(msg, "inbound", "IHE_PAM_FR")
    
    print(f"Valid: {result.is_valid}, Level: {result.level}")
    print(f"Issues: {len(result.issues)}")
    
    for issue in result.issues:
        print(f"  [{issue.severity}] {issue.code}: {issue.message}")
    
    if expected_issues:
        found_codes = {i.code for i in result.issues}
        missing = set(expected_issues) - found_codes
        unexpected = found_codes - set(expected_issues)
        
        if missing:
            print(f"\n[!] Missing expected issues: {missing}")
        if unexpected:
            print(f"[!] Unexpected issues: {unexpected}")
        if not missing and not unexpected:
            print(f"\n[OK] All expected issues found")
    
    return result


# Test 1: CX (Extended Composite ID) invalide - ID manquant
test1 = """MSH|^~\\&|SENDING|FACILITY|RECEIVING|DEST|20240101120000||ADT^A01^ADT_A01|MSG123456|P|2.5
EVN|A01|20240101120000
PID|1||^1234567^M10^HOSP||DOE^JOHN||19800101
PV1|1|I|SERVICE^101^A|||DOC123^SMITH^JANE"""

# Test 2: XPN (Person Name) invalide - ni Family ni Given
test2 = """MSH|^~\\&|SENDING|FACILITY|RECEIVING|DEST|20240101120000||ADT^A01^ADT_A01|MSG123457|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^HOSP||^^MIDDLE||19800101
PV1|1|I|SERVICE^101^A|||DOC123^SMITH^JANE"""

# Test 3: XAD (Address) vide et XTN (Phone) invalide
test3 = """MSH|^~\\&|SENDING|FACILITY|RECEIVING|DEST|20240101120000||ADT^A01^ADT_A01|MSG123458|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^HOSP||DOE^JOHN||19800101||||^^^^^||^^^^^INVALIDTYPE
PV1|1|I|SERVICE^101^A|||DOC123^SMITH^JANE"""

# Test 4: TS (Timestamp) invalide - formats incorrects
test4 = """MSH|^~\\&|SENDING|FACILITY|RECEIVING|DEST|20240101120000||ADT^A01^ADT_A01|MSG123459|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^HOSP||DOE^JOHN||198013XX
PV1|1|I|SERVICE^101^A|||DOC123^SMITH^JANE||||||||||||||||||||||||||||||||||||||20241301000000"""

# Test 5: PV1 champs invalides - Patient Class et XCN incomplet
test5 = """MSH|^~\\&|SENDING|FACILITY|RECEIVING|DEST|20240101120000||ADT^A01^ADT_A01|MSG123460|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^HOSP||DOE^JOHN||19800101
PV1|1|X|SERVICE^101^A|||^"""

# Test 6: Message complet valide avec tous les types de données
test6 = """MSH|^~\\&|SENDING|FACILITY|RECEIVING|DEST|20240101120000||ADT^A01^ADT_A01|MSG123461|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^HOSP^PI||DOE^JOHN^MIDDLE^JR^DR||19800101|M||||||123 Main St^Apt 5^Paris^^75001^FRA^H~456 Oak Ave^^Lyon^^69001^FRA^B||(33)123456789^^PRN^PH~0601020304^^ORN^CP
PV1|1|I|SERVICE^101^A^HOSPITAL|||DOC123^SMITH^JANE^L^DR||||||||||||V123456^^^HOSP||||||||||||||||||||||||20240101100000"""

# Test 7: Répétitions multiples avec erreurs
test7 = """MSH|^~\\&|SENDING|FACILITY|RECEIVING|DEST|20240101120000||ADT^A01^ADT_A01|MSG123462|P|2.5
EVN|A01|20240101120000
PID|1||^BadID~123456^^^HOSP||DOE^JOHN~^^||19800101|||||||~InvalidPhone
PV1|1|I|SERVICE^101^A|||DOC123^SMITH^JANE"""


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTS DE VALIDATION DES TYPES DE DONNÉES COMPLEXES HL7 v2.5")
    print("="*80)
    
    # Test 1: CX invalide
    test_scenario(
        "Test 1: CX - ID manquant dans PID-3",
        test1,
        expected_issues=["PID3[0]_CX_ID_EMPTY"]
    )
    
    # Test 2: XPN invalide
    test_scenario(
        "Test 2: XPN - Ni Family ni Given Name dans PID-5",
        test2,
        expected_issues=["PID5[0]_XPN_INCOMPLETE"]
    )
    
    # Test 3: XAD et XTN invalides
    test_scenario(
        "Test 3: XAD vide et XTN vide dans PID-11/PID-13",
        test3,
        expected_issues=["PID11[0]_XAD_EMPTY", "PID13[0]_XTN_EMPTY"]
    )
    
    # Test 4: TS invalides
    test_scenario(
        "Test 4: Timestamps invalides - PID-7 format et PV1-44 mois",
        test4,
        expected_issues=["PID7_TS_FORMAT", "PV1_44_TS_MONTH_INVALID"]
    )
    
    # Test 5: PV1 champs invalides
    test_scenario(
        "Test 5: PV1 - Patient Class invalide (pas de XCN car ^seul pas vide)",
        test5,
        expected_issues=["PV1_2_INVALID"]
    )
    
    # Test 6: Message valide complet
    test_scenario(
        "Test 6: Message complet VALIDE avec tous les types de données",
        test6
    )
    
    # Test 7: Répétitions multiples avec erreurs
    test_scenario(
        "Test 7: Répétitions - erreurs CX, XPN dans répétitions",
        test7,
        expected_issues=["PID3[0]_CX_ID_EMPTY", "PID3[0]_CX_SCHEME_MISSING", "PID5[1]_XPN_INCOMPLETE"]
    )
    
    print("\n" + "="*80)
    print("Tests terminés")
    print("="*80)
