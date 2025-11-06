"""Test de validation de scénarios IHE PAM.

Ce script teste la validation de scénarios complets avec plusieurs messages
pour vérifier :
- La validation structurelle de chaque message
- Les transitions de workflow
- La cohérence des identifiants patient/dossier
- La chronologie des événements
"""

from app.services.scenario_validation import validate_scenario

# Scénario 1: Parcours complet valide (pré-admission → admission → transfert → sortie)
SCENARIO_VALID = """MSH|^~\\&|SRC_APP|SRC_FAC|RECV_APP|RECV_FAC|20240101100000||ADT^A05^ADT_A05|MSG001|P|2.5
EVN|A05|20240101100000
PID|1||PAT123456^^^HOSP||DUPONT^JEAN^PAUL||19800115|M|||123 Rue de la Paix^^PARIS^^75001^FR|||||||123456789
PV1|1|P|PREMED^PRE^1||||DOC123^MARTIN^SOPHIE^DR|||||||||||VIS789^^^HOSP|||||||||||||||||||||||||20240105

MSH|^~\\&|SRC_APP|SRC_FAC|RECV_APP|RECV_FAC|20240105090000||ADT^A01^ADT_A01|MSG002|P|2.5
EVN|A01|20240105090000
PID|1||PAT123456^^^HOSP||DUPONT^JEAN^PAUL||19800115|M|||123 Rue de la Paix^^PARIS^^75001^FR|||||||123456789
PV1|1|I|CARDIO^101^A^^^^Building A|28|||DOC123^MARTIN^SOPHIE^DR|||CARDIO||||||||VIS789^^^HOSP|||||||||||||||||||||||||20240105090000

MSH|^~\\&|SRC_APP|SRC_FAC|RECV_APP|RECV_FAC|20240107140000||ADT^A02^ADT_A02|MSG003|P|2.5
EVN|A02|20240107140000
PID|1||PAT123456^^^HOSP||DUPONT^JEAN^PAUL||19800115|M|||123 Rue de la Paix^^PARIS^^75001^FR|||||||123456789
PV1|1|I|NEURO^201^B^^^^Building B|28|||DOC456^DURAND^PIERRE^DR|||NEURO||||||||VIS789^^^HOSP|||||||||||||||||||||||||20240107140000

MSH|^~\\&|SRC_APP|SRC_FAC|RECV_APP|RECV_FAC|20240110160000||ADT^A03^ADT_A03|MSG004|P|2.5
EVN|A03|20240110160000
PID|1||PAT123456^^^HOSP||DUPONT^JEAN^PAUL||19800115|M|||123 Rue de la Paix^^PARIS^^75001^FR|||||||123456789
PV1|1|I|NEURO^201^B^^^^Building B|28|||DOC456^DURAND^PIERRE^DR|||NEURO||||||||VIS789^^^HOSP|||||||||||||||||||||||||20240110160000"""

# Scénario 2: Workflow invalide (commence par A02 au lieu d'un événement initial)
SCENARIO_INVALID_WORKFLOW = """MSH|^~\\&|SRC_APP|SRC_FAC|RECV_APP|RECV_FAC|20240101100000||ADT^A02^ADT_A02|MSG001|P|2.5
EVN|A02|20240101100000
PID|1||PAT123456^^^HOSP||DUPONT^JEAN||19800115|M
PV1|1|I|CARDIO^101^A|||||||||||||||||VIS789^^^HOSP"""

# Scénario 3: Transition invalide (A05 → A03, impossible car pas d'hospitalisation)
SCENARIO_INVALID_TRANSITION = """MSH|^~\\&|SRC_APP|SRC_FAC|RECV_APP|RECV_FAC|20240101100000||ADT^A05^ADT_A05|MSG001|P|2.5
EVN|A05|20240101100000
PID|1||PAT123456^^^HOSP||DUPONT^JEAN||19800115|M
PV1|1|P|PREMED^PRE^1||||||||||||||||VIS789^^^HOSP

MSH|^~\\&|SRC_APP|SRC_FAC|RECV_APP|RECV_FAC|20240102100000||ADT^A03^ADT_A03|MSG002|P|2.5
EVN|A03|20240102100000
PID|1||PAT123456^^^HOSP||DUPONT^JEAN||19800115|M
PV1|1|P|PREMED^PRE^1||||||||||||||||VIS789^^^HOSP"""

# Scénario 4: Patients différents (incohérence)
SCENARIO_DIFFERENT_PATIENTS = """MSH|^~\\&|SRC_APP|SRC_FAC|RECV_APP|RECV_FAC|20240101100000||ADT^A01^ADT_A01|MSG001|P|2.5
EVN|A01|20240101100000
PID|1||PAT111^^^HOSP||DUPONT^JEAN||19800115|M
PV1|1|I|CARDIO^101^A||||||||||||||||VIS789^^^HOSP

MSH|^~\\&|SRC_APP|SRC_FAC|RECV_APP|RECV_FAC|20240102100000||ADT^A02^ADT_A02|MSG002|P|2.5
EVN|A02|20240102100000
PID|1||PAT222^^^HOSP||MARTIN^SOPHIE||19900201|F
PV1|1|I|NEURO^201^B||||||||||||||||VIS789^^^HOSP"""

# Scénario 5: Chronologie inversée (timestamps désordonnés)
SCENARIO_BAD_CHRONOLOGY = """MSH|^~\\&|SRC_APP|SRC_FAC|RECV_APP|RECV_FAC|20240105100000||ADT^A01^ADT_A01|MSG001|P|2.5
EVN|A01|20240105100000
PID|1||PAT123456^^^HOSP||DUPONT^JEAN||19800115|M
PV1|1|I|CARDIO^101^A||||||||||||||||VIS789^^^HOSP

MSH|^~\\&|SRC_APP|SRC_FAC|RECV_APP|RECV_FAC|20240101100000||ADT^A02^ADT_A02|MSG002|P|2.5
EVN|A02|20240101100000
PID|1||PAT123456^^^HOSP||DUPONT^JEAN||19800115|M
PV1|1|I|NEURO^201^B||||||||||||||||VIS789^^^HOSP"""


def print_result(name: str, result):
    """Affiche les résultats de validation d'un scénario."""
    print(f"\n{'='*80}")
    print(f"Scénario: {name}")
    print(f"{'='*80}")
    print(f"Statut: {result.level.upper()} ({'✓ Valide' if result.is_valid else '✗ Invalide'})")
    print(f"Messages: {result.total_messages} total, {result.valid_messages} valide(s)")
    print(f"Issues totales: {result.total_issues}")
    
    if result.workflow_issues:
        print(f"\n⚠️  Issues de workflow ({len(result.workflow_issues)}):")
        for issue in result.workflow_issues:
            print(f"  [{issue.severity.upper()}] {issue.code}: {issue.message}")
    
    if result.coherence_issues:
        print(f"\n⚠️  Issues de cohérence ({len(result.coherence_issues)}):")
        for issue in result.coherence_issues:
            print(f"  [{issue.severity.upper()}] {issue.code}: {issue.message}")
    
    print(f"\n📋 Détail des messages:")
    for msg in result.messages:
        status = "✓" if msg.validation.is_valid else "✗"
        print(f"  {status} Message #{msg.message_number}: {msg.event_code} "
              f"(Patient: {msg.patient_id or 'N/A'}, Dossier: {msg.visit_id or 'N/A'})")
        if not msg.validation.is_valid:
            for issue in msg.validation.issues[:3]:  # Afficher max 3 issues par message
                print(f"      • [{issue.severity}] {issue.code}: {issue.message}")
            if len(msg.validation.issues) > 3:
                print(f"      ... et {len(msg.validation.issues) - 3} autres issues")


def main():
    """Exécute les tests de validation de scénarios."""
    print("="*80)
    print("TEST DE VALIDATION DE SCÉNARIOS IHE PAM")
    print("="*80)
    
    # Test 1: Scénario valide
    result1 = validate_scenario(SCENARIO_VALID, direction="inbound", profile="IHE_PAM_FR")
    print_result("Parcours complet valide (A05->A01->A02->A03)", result1)
    assert result1.is_valid, "Le scénario valide devrait être accepté"
    assert result1.level == "ok" or result1.level == "warn", "Le niveau devrait être OK ou WARN"
    assert result1.total_messages == 4, "4 messages attendus"
    print("✅ Test 1 réussi: Scénario valide accepté")
    
    # Test 2: Workflow invalide (événement initial incorrect)
    result2 = validate_scenario(SCENARIO_INVALID_WORKFLOW, direction="inbound", profile="IHE_PAM_FR")
    print_result("Workflow invalide (commence par A02)", result2)
    assert not result2.is_valid, "Le workflow invalide devrait être rejeté"
    assert any("INVALID_INITIAL" in issue.code for issue in result2.workflow_issues), \
        "Une erreur d'événement initial invalide devrait être détectée"
    print("✅ Test 2 réussi: Workflow invalide détecté")
    
    # Test 3: Transition invalide
    result3 = validate_scenario(SCENARIO_INVALID_TRANSITION, direction="inbound", profile="IHE_PAM_FR")
    print_result("Transition invalide (A05->A03)", result3)
    assert not result3.is_valid, "La transition invalide devrait être rejetée"
    assert any("INVALID_TRANSITION" in issue.code for issue in result3.workflow_issues), \
        "Une erreur de transition invalide devrait être détectée"
    print("✅ Test 3 réussi: Transition invalide détectée")
    
    # Test 4: Patients différents
    result4 = validate_scenario(SCENARIO_DIFFERENT_PATIENTS, direction="inbound", profile="IHE_PAM_FR")
    print_result("Patients différents (incohérence)", result4)
    assert not result4.is_valid, "L'incohérence patient devrait être détectée"
    assert any("MULTIPLE_PATIENTS" in issue.code for issue in result4.coherence_issues), \
        "Une erreur de patients multiples devrait être détectée"
    print("✅ Test 4 réussi: Incohérence patient détectée")
    
    # Test 5: Chronologie inversée
    result5 = validate_scenario(SCENARIO_BAD_CHRONOLOGY, direction="inbound", profile="IHE_PAM_FR")
    print_result("Chronologie inversée", result5)
    assert any("TIMESTAMP_ORDER" in issue.code for issue in result5.coherence_issues), \
        "Une erreur de chronologie devrait être détectée"
    print("✅ Test 5 réussi: Chronologie inversée détectée")
    
    print(f"\n{'='*80}")
    print("✅ TOUS LES TESTS SONT RÉUSSIS!")
    print("="*80)
    print("\n📝 Pour tester dans l'interface web:")
    print("   1. Démarrer FastAPI: uvicorn app.app:app --reload")
    print("   2. Ouvrir: http://127.0.0.1:8000/validation")
    print("   3. Cliquer sur l'onglet 'Scénario (workflow)'")
    print("   4. Coller l'un des scénarios ci-dessus")
    print("   5. Cliquer sur 'Valider le scénario'")


if __name__ == "__main__":
    main()
