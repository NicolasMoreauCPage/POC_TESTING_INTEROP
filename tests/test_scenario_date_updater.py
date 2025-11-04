"""
Tests pour la mise à jour automatique des dates dans les scénarios IHE.
"""
import pytest
from datetime import datetime, timedelta

from app.services.scenario_date_updater import (
    update_hl7_message_dates,
    analyze_message_dates,
    parse_hl7_datetime,
    format_hl7_datetime,
    calculate_relative_datetime,
)


def test_parse_hl7_datetime():
    """Teste le parsing de dates HL7."""
    # Date seule
    dt = parse_hl7_datetime("20221016")
    assert dt is not None
    assert dt.year == 2022
    assert dt.month == 10
    assert dt.day == 16
    
    # Date + heure
    dt = parse_hl7_datetime("20221016235900")
    assert dt is not None
    assert dt.hour == 23
    assert dt.minute == 59
    assert dt.second == 0
    
    # Avec millisecondes (ignorées)
    dt = parse_hl7_datetime("20221016235900.1234")
    assert dt is not None
    assert dt.second == 0
    
    # Avec timezone (ignorée)
    dt = parse_hl7_datetime("20221016235900+0100")
    assert dt is not None


def test_format_hl7_datetime():
    """Teste le formatage de dates en HL7."""
    dt = datetime(2022, 10, 16, 23, 59, 0)
    
    # Avec secondes
    assert format_hl7_datetime(dt, include_seconds=True) == "20221016235900"
    
    # Sans secondes
    assert format_hl7_datetime(dt, include_seconds=False) == "20221016"


def test_calculate_relative_datetime():
    """Teste le calcul de dates relatives."""
    now = datetime(2025, 11, 2, 12, 0, 0)
    
    # 2 jours avant
    past = calculate_relative_datetime(now, days_offset=-2)
    assert past == datetime(2025, 10, 31, 12, 0, 0)
    
    # 3 heures après
    future = calculate_relative_datetime(now, hours_offset=3)
    assert future == datetime(2025, 11, 2, 15, 0, 0)
    
    # Combinaison
    combined = calculate_relative_datetime(now, days_offset=1, hours_offset=-2, minutes_offset=30)
    assert combined == datetime(2025, 11, 3, 10, 30, 0)


def test_analyze_message_dates():
    """Teste l'analyse des dates dans un message."""
    message = """MSH|^~\\&|SRC|FAC|DST|FAC|20221016235900||ADT^A01|MSG123|P|2.5
PID|||123456||DUPONT^Jean||19800101|M
PV1||I|3620^3010^3010|||||||||||20221016120000"""
    
    analysis = analyze_message_dates(message)
    
    assert analysis['count'] == 2  # 2 dates récentes (pas la date de naissance)
    assert analysis['oldest'] == datetime(2022, 10, 16, 12, 0, 0)
    assert analysis['newest'] == datetime(2022, 10, 16, 23, 59, 0)
    assert analysis['span_days'] == 0


def test_update_hl7_message_dates_simple():
    """Teste la mise à jour basique des dates."""
    old_message = "MSH|^~\\&|SRC|FAC|DST|FAC|20221016235900||ADT^A01|MSG123|P|2.5"
    
    reference_time = datetime(2025, 11, 2, 14, 0, 0)
    updated = update_hl7_message_dates(old_message, reference_time)
    
    # Vérifier que la date a été mise à jour
    assert "20221016235900" not in updated
    assert "202511" in updated  # Novembre 2025
    
    # Analyser les dates mises à jour
    analysis = analyze_message_dates(updated)
    assert analysis['count'] == 1
    # La date devrait être proche de la référence (décalage appliqué)
    assert analysis['oldest'].year == 2025
    assert analysis['oldest'].month == 11


def test_update_hl7_message_dates_complete():
    """Teste la mise à jour sur un message complet."""
    old_message = """MSH|^~\\&|SRC|FAC|DST|FAC|20221016235900||ADT^A01|MSG123|P|2.5
PID|||123456||DUPONT^Jean||19800101|M
PV1||I|3620^3010^3010|||||||||||20221016120000
ZBE|31636^MOUVEMENT^1.2.250.1.213.1.1.1.4^ISO|20221016235900||INSERT|N||^^^^^^UF^^^3620||HMS"""
    
    reference_time = datetime(2025, 11, 2, 14, 30, 0)
    updated = update_hl7_message_dates(old_message, reference_time)
    
    # Vérifier que les anciennes dates ne sont plus présentes
    assert "20221016120000" not in updated
    assert "20221016235900" not in updated
    
    # Analyser les dates mises à jour
    analysis = analyze_message_dates(updated)
    assert analysis['count'] == 3  # MSH-7, PV1-44, ZBE-2
    
    # Toutes les dates devraient être en 2025
    for date_info in analysis['dates']:
        assert date_info['datetime'].year == 2025
        assert date_info['datetime'].month == 11
    
    # Vérifier que les délais relatifs sont préservés
    # (même si les dates absolues changent, l'écart entre elles reste le même)
    span_hours = (analysis['newest'] - analysis['oldest']).total_seconds() / 3600
    assert abs(span_hours - 11.98) < 0.1  # ~12 heures d'écart (23:59 - 12:00)


def test_update_preserves_message_structure():
    """Vérifie que la structure du message est préservée."""
    old_message = """MSH|^~\\&|SRC|FAC|DST|FAC|20221016235900||ADT^A01|MSG123|P|2.5
PID|||123456||DUPONT^Jean||19800101|M|||123 Main St||555-1234
PV1||I|3620^3010^3010|||||||||||20221016120000"""
    
    updated = update_hl7_message_dates(old_message)
    
    # Vérifier que les segments sont toujours là
    assert updated.startswith("MSH|")
    assert "PID|||123456||DUPONT^Jean" in updated
    assert "555-1234" in updated
    assert "PV1||I|3620^3010^3010" in updated
    
    # Vérifier le nombre de segments
    assert updated.count("\n") == old_message.count("\n")


def test_update_handles_birth_dates():
    """Vérifie que les dates de naissance ne sont pas modifiées (elles sont dans le passé lointain)."""
    message = "PID|||123456||DUPONT^Jean||19800101|M"
    
    reference_time = datetime(2025, 11, 2, 14, 0, 0)
    updated = update_hl7_message_dates(message, reference_time)
    
    # La date de naissance devrait être mise à jour aussi
    # car c'est la plus ancienne date trouvée
    # Mais pour les vraies dates de naissance, on pourrait ajouter
    # une logique pour les ignorer si < 1990 par exemple
    assert "1980" in updated  # Pour l'instant, on la garde


def test_update_dates_with_no_dates():
    """Teste un message sans dates."""
    message = "PID|||123456||DUPONT^Jean||"
    
    updated = update_hl7_message_dates(message)
    
    # Le message devrait rester inchangé
    assert updated == message


def test_dates_are_recent_after_update():
    """Vérifie que les dates mises à jour sont effectivement récentes."""
    old_message = "MSH|^~\\&|SRC|FAC|DST|FAC|20221016235900||ADT^A01|MSG123|P|2.5"
    
    # Mettre à jour avec le temps actuel
    updated = update_hl7_message_dates(old_message, datetime.utcnow())
    
    # Extraire et parser la date mise à jour
    analysis = analyze_message_dates(updated)
    assert analysis['count'] == 1
    
    updated_date = analysis['oldest']
    now = datetime.utcnow()
    
    # La date mise à jour devrait être très proche de maintenant
    # (différence de moins de 1 minute pour tenir compte du temps d'exécution)
    time_diff = abs((now - updated_date).total_seconds())
    assert time_diff < 60, f"Date mise à jour trop éloignée: {time_diff}s"


def test_multiple_messages_same_shift():
    """
    Vérifie que chaque message est mis à jour indépendamment.
    
    Note: Dans la version actuelle, chaque message est traité séparément.
    Tous sont mis à jour par rapport à la même référence, donc les délais
    relatifs ne sont PAS préservés entre messages différents.
    Si on veut préserver les délais relatifs, il faudrait traiter un
    scénario complet en une seule fois.
    """
    msg1 = "MSH|^~\\&|SRC|FAC|DST|FAC|20221016120000||ADT^A01|MSG1|P|2.5"
    msg2 = "MSH|^~\\&|SRC|FAC|DST|FAC|20221016150000||ADT^A02|MSG2|P|2.5"
    msg3 = "MSH|^~\\&|SRC|FAC|DST|FAC|20221016180000||ADT^A03|MSG3|P|2.5"
    
    reference_time = datetime(2025, 11, 2, 14, 0, 0)
    
    updated1 = update_hl7_message_dates(msg1, reference_time)
    updated2 = update_hl7_message_dates(msg2, reference_time)
    updated3 = update_hl7_message_dates(msg3, reference_time)
    
    # Extraire les dates
    date1 = analyze_message_dates(updated1)['oldest']
    date2 = analyze_message_dates(updated2)['oldest']
    date3 = analyze_message_dates(updated3)['oldest']
    
    # Chaque message est aligné sur la référence indépendamment
    # Donc toutes les dates devraient être égales à la référence
    assert date1 == reference_time
    assert date2 == reference_time
    assert date3 == reference_time
