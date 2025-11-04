from sqlmodel import select


def test_chemo_sessions_have_a01_a03_in_order(session, dossier_chemo_with_sessions_recurring):
    data = dossier_chemo_with_sessions_recurring
    venues = data["venues"]

    from app.models import Mouvement

    for v in venues:
        mouvements = session.exec(
            select(Mouvement).where(Mouvement.venue_id == v.id).order_by(Mouvement.mouvement_seq)
        ).all()
        assert len(mouvements) == 2, "Chaque venue doit avoir deux mouvements (A01 puis A03)"
        assert mouvements[0].trigger_event == "A01"
        assert mouvements[1].trigger_event == "A03"


def test_psy_day_hospital_has_a01_a03_in_order(session, dossier_psy_day_hospital_recurring):
    data = dossier_psy_day_hospital_recurring
    venues = data["venues"]

    from app.models import Mouvement

    for v in venues:
        mouvements = session.exec(
            select(Mouvement).where(Mouvement.venue_id == v.id).order_by(Mouvement.mouvement_seq)
        ).all()
        assert len(mouvements) == 2
        assert mouvements[0].trigger_event == "A01"
        assert mouvements[1].trigger_event == "A03"
