"""
Test de validation des transitions IHE PAM dans le flux de messages.
Vérifie que les transitions invalides sont rejetées avec ACK AE et message explicite.
"""
import pytest
from datetime import date, datetime
from sqlmodel import Session
from app.models import Patient, Dossier, Venue, Mouvement
from app.services.transport_inbound import on_message_inbound
from app.db import get_next_sequence
import pytest
from sqlmodel import Session, select
from app.models import Patient, Dossier, Venue, Mouvement
from app.services.transport_inbound import on_message_inbound_async
from app.db import get_next_sequence


@pytest.mark.asyncio
async def test_reject_invalid_transition_absence_from_external(session: Session):
    """
    Test: rejeter A03 (absence temporaire) depuis A04 (consultation externe).
    
    Selon IHE PAM, A03 est autorisé seulement depuis Hospitalisation (I/R),
    pas depuis consultation externe (O/E).
    """
    # Créer un patient
    patient_seq = get_next_sequence(session, "patient")
    patient = Patient(
        patient_seq=patient_seq,
        identifier=str(patient_seq),
        family="Test",
        given="Invalid",
        gender="male"
    )
    session.add(patient)
    session.flush()    # Créer un dossier et une venue en consultation externe (A04)
    dossier = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=patient.id,
        uf_medicale="TEST",

        uf_hebergement="TEST",
        admit_time=datetime.now()
    )
    session.add(dossier)
    session.flush()
    
    venue = Venue(
        venue_seq=get_next_sequence(session, "venue"),
        dossier_id=dossier.id,
        uf_medicale="TEST",

        uf_hebergement="TEST",
        start_time=datetime.now(),
        code="CONS",
        label="Consultation externe"
    )
    session.add(venue)
    session.flush()
    
    # Mouvement initial A04 (consultation externe)
    mouvement = Mouvement(
        venue_id=venue.id,
        mouvement_seq=get_next_sequence(session, "mouvement"),
        movement_type="admission externe",
        trigger_event="A04",
        when=datetime.now(),
        location="CONS-01"
    )
    session.add(mouvement)
    session.commit()
    
    # Construire un message A03 (absence temporaire) - invalide depuis A04
    msg_a03 = f"""MSH|^~\\&|SEND|FAC|RECV|FAC|20251103120000||ADT^A03^ADT_A03|MSG001|P|2.5
EVN|A03|20251103120000
PID|1||{patient.patient_seq}^^^IPP||Test^Invalid||19800101|M
PV1|1|O|CONS-01||||||||||||||||{venue.venue_seq}"""
    
    # Tenter d'envoyer le message
    ack = await on_message_inbound_async(msg_a03, session, None)
    
    # Vérifier que le message a été rejeté avec AE
    assert "MSA|AE" in ack, f"Expected AE (Application Error), got: {ack}"
    assert "Transition IHE invalide" in ack or "A04 -> A03" in ack, \
        f"Expected explicit transition error message, got: {ack}"
    
    # Vérifier qu'aucun nouveau mouvement n'a été créé
    mouvements = session.exec(select(Mouvement).where(Mouvement.venue_id == venue.id)).all()
    assert len(mouvements) == 1, "Le mouvement A03 invalide ne devrait pas avoir été enregistré"


@pytest.mark.asyncio
async def test_accept_valid_transition_absence_from_hospitalization(session: Session):
    """
    Test: accepter A03 (absence temporaire) depuis A01 (admission).
    
    Selon IHE PAM, A03 est autorisé depuis Hospitalisation (A01).
    """
    # Créer un patient
    patient_seq = get_next_sequence(session, "patient")
    patient = Patient(
        patient_seq=patient_seq,
        identifier=str(patient_seq),
        family="Test",
        given="Valid",
        gender="male"
    )
    session.add(patient)
    session.flush()
    
    # Créer un dossier et une venue en hospitalisation (A01)
    dossier = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=patient.id,
        uf_medicale="TEST",

        uf_hebergement="TEST",
        admit_time=datetime.now()
    )
    session.add(dossier)
    session.flush()
    
    venue = Venue(
        venue_seq=get_next_sequence(session, "venue"),
        dossier_id=dossier.id,
        uf_medicale="TEST",

        uf_hebergement="TEST",
        start_time=datetime.now(),
        code="HOSP",
        label="Hospitalisation"
    )
    session.add(venue)
    session.flush()
    
    # Mouvement initial A01 (hospitalisation)
    mouvement = Mouvement(
        venue_id=venue.id,
        mouvement_seq=get_next_sequence(session, "mouvement"),
        movement_type="admission",
        trigger_event="A01",
        when=datetime.now(),
        location="MED-101"
    )
    session.add(mouvement)
    session.commit()
    
    # Construire un message A03 (absence temporaire) - valide depuis A01
    msg_a03 = f"""MSH|^~\\&|SEND|FAC|RECV|FAC|20251103120000||ADT^A03^ADT_A03|MSG002|P|2.5
EVN|A03|20251103120000
PID|1||{patient.patient_seq}^^^IPP||Test^Valid||19800101|M
PV1|1|I|MED-101||||||||||||||||{venue.venue_seq}"""
    
    # Tenter d'envoyer le message
    ack = await on_message_inbound_async(msg_a03, session, None)
    
    # Vérifier que le message a été accepté avec AA
    assert "MSA|AA" in ack, f"Expected AA (Application Accept), got: {ack}"
    
    # Vérifier qu'un nouveau mouvement A03 a bien été créé
    session.expire_all()  # Refresh to see changes from handler
    mouvements = session.exec(
        select(Mouvement)
        .where(Mouvement.venue_id == venue.id)
        .order_by(Mouvement.mouvement_seq)
    ).all()
    assert len(mouvements) == 2, "Le mouvement A03 valide devrait avoir été enregistré"
    assert mouvements[1].trigger_event == "A03", f"Expected A03, got {mouvements[1].trigger_event}"


@pytest.mark.asyncio
async def test_reject_invalid_a22_without_a21(session: Session):
    """
    Test: rejeter A22 (retour d'absence) sans A03/A21 préalable.
    
    Selon IHE PAM, A22 ne peut venir QUE depuis "Absence temporaire" (A03/A21).
    """
    # Créer un patient
    patient_seq = get_next_sequence(session, "patient")
    patient = Patient(
        patient_seq=patient_seq,
        identifier=str(patient_seq),
        family="Test",
        given="Cancel",
        gender="male"
    )
    session.add(patient)
    session.flush()
    
    # Créer un dossier et une venue en hospitalisation (A01)
    dossier = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=patient.id,
        uf_medicale="TEST",

        uf_hebergement="TEST",
        admit_time=datetime.now()
    )
    session.add(dossier)
    session.flush()
    
    venue = Venue(
        venue_seq=get_next_sequence(session, "venue"),
        dossier_id=dossier.id,
        uf_medicale="TEST",

        uf_hebergement="TEST",
        start_time=datetime.now(),
        code="HOSP",
        label="Hospitalisation"
    )
    session.add(venue)
    session.flush()
    
    # Mouvement initial A01 (hospitalisation) - PAS d'absence
    mouvement = Mouvement(
        venue_id=venue.id,
        mouvement_seq=get_next_sequence(session, "mouvement"),
        movement_type="admission",
        trigger_event="A01",
        when=datetime.now(),
        location="MED-101"
    )
    session.add(mouvement)
    session.commit()
    
    # Construire un message A22 (retour d'absence) - invalide depuis A01
    msg_a22 = f"""MSH|^~\\&|SEND|FAC|RECV|FAC|20251103120000||ADT^A22^ADT_A22|MSG003|P|2.5
EVN|A22|20251103120000
PID|1||{patient.patient_seq}^^^IPP||Test^InvalidReturn||19800101|M
PV1|1|I|MED-101||||||||||||||||{venue.venue_seq}"""
    
    # Tenter d'envoyer le message
    ack = await on_message_inbound_async(msg_a22, session, None)
    
    # Vérifier que le message a été rejeté avec AE
    assert "MSA|AE" in ack, f"Expected AE (Application Error), got: {ack}"
    assert "Transition IHE invalide" in ack or "A01 -> A22" in ack, \
        f"Expected explicit transition error message, got: {ack}"
    
    # Vérifier qu'aucun mouvement A22 n'a été créé
    mouvements = session.exec(select(Mouvement).where(Mouvement.venue_id == venue.id)).all()
    assert len(mouvements) == 1, "Le mouvement A22 invalide ne devrait pas avoir été enregistré"
