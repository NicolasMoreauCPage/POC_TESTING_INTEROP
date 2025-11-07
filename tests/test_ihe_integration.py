"""Tests d'intégration des flux IHE PAM complets avec FHIR."""
import pytest
from datetime import datetime
from sqlmodel import Session, select

from app.models import Patient, Dossier, Venue, Mouvement
from app.models_endpoints import SystemEndpoint, MessageLog
from app.services.transport_inbound import on_message_inbound
from app.services.fhir import generate_fhir_bundle_for_dossier
from app.services.identifier_manager import create_identifier_from_hl7


def _create_test_message(trigger: str, identifiers: list, name: str = "TEST^TEST", location: str = "CARDIO^001") -> str:
    """Helper pour créer un message ADT de test."""
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    pid_3 = "~".join(identifiers)
    
    return (
        f"MSH|^~\\&|CPAGE|CPAGE|LOGICIEL|LOGICIEL|{now}||ADT^{trigger}^ADT_{trigger}|MSG{trigger}|P|2.5^FRA^2.1\r"
        f"EVN|{trigger}|{now}|||APPLI^IHE^\r"
        f"PID|||{pid_3}||{name}||19800101|M|||123 RUE^^VILLE^^12345||0123456789\r"
        f"PV1||I|{location}|||||||||||||||||1|||||||||||||||||||||||||{now}\r"
        f"ZBE|1|{now}||CREATE|N|{trigger}|^^^^^^001||001^001|||M\r"
    )


@pytest.mark.asyncio
async def test_ihe_pam_end_to_end(session: Session):
    """Test le flux complet : admission → mouvements → sortie avec génération FHIR."""
    
    # 1. Créer un endpoint de test
    ep = SystemEndpoint(name="TEST", kind="MLLP", role="receiver")
    session.add(ep)
    session.commit()
    session.refresh(ep)
    
    # 2. Admission (A01)
    msg = _create_test_message("A01", ["0123456789^^^HOPITAL"])
    ack = await on_message_inbound(msg, session, ep)
    assert "MSA|AA|" in ack
    
    # Vérifier création patient et dossier
    p = session.exec(select(Patient).where(Patient.external_id == "0123456789")).first()
    assert p is not None
    assert p.family == "TEST"
    assert p.given == "TEST"
    
    d = session.exec(select(Dossier).where(Dossier.patient_id == p.id)).first()
    assert d is not None
    
    # 3. Générer un Bundle FHIR initial
    bundle = generate_fhir_bundle_for_dossier(d)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"
    assert bundle["entry"][1]["resource"]["resourceType"] == "Encounter"
    assert bundle["entry"][1]["resource"]["status"] == "in-progress"
    
    # 4. Transfert (A02)
    msg = _create_test_message("A02", ["0123456789^^^HOPITAL"], location="CHIR^002")
    ack = await on_message_inbound(msg, session, ep)
    assert "MSA|AA|" in ack
    
    # Vérifier création mouvement (récupérer le dernier = transfer)
    mvts = session.exec(
        select(Mouvement)
        .join(Venue)
        .join(Dossier)
        .where(Dossier.id == d.id)
        .order_by(Mouvement.mouvement_seq.desc())
    ).all()
    assert len(mvts) == 2  # Admission + transfer
    mvt = mvts[0]  # Le plus récent = transfer
    assert mvt is not None
    assert mvt.location == "CHIR^002"
    
    # 5. Sortie (A03)
    msg = _create_test_message("A03", ["0123456789^^^HOPITAL"])
    ack = await on_message_inbound(msg, session, ep)
    assert "MSA|AA|" in ack
    
    # Vérifier mise à jour dossier
    session.refresh(d)
    assert d.discharge_time is not None
    
    # 6. Générer un Bundle FHIR final
    bundle = generate_fhir_bundle_for_dossier(d)
    assert bundle["entry"][1]["resource"]["status"] == "finished"
    assert "end" in bundle["entry"][1]["resource"]["period"]
    
    # 7. Vérifier logs
    logs = session.exec(
        select(MessageLog)
        .where(MessageLog.endpoint_id == ep.id)
        .order_by(MessageLog.created_at)
    ).all()
    assert len(logs) == 3
    assert all(l.status == "processed" for l in logs)
    assert [l.message_type for l in logs] == ["ADT^A01", "ADT^A02", "ADT^A03"]