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
    # location: e.g. "CARDIO^001" → code_service, code_uf
    loc_parts = location.split("^")
    code_service = loc_parts[0] if len(loc_parts) > 0 else "CARDIO"
    code_uf = loc_parts[1] if len(loc_parts) > 1 else "001"
    # ZBE-7: ^^^^^^UF^^^CODE_UF (10e composant)
    zbe_7 = "^^^^^^UF^^^" + code_uf
    zbe = f"ZBE|1|{now}||UPDATE|N|{trigger}|{zbe_7}| |HMS"
    return (
        f"MSH|^~\\&|CPAGE|CPAGE|LOGICIEL|LOGICIEL|{now}||ADT^{trigger}^ADT_{trigger}|MSG{trigger}|P|2.5^FRA^2.1\r"
        f"EVN|{trigger}|{now}|||APPLI^IHE^\r"
        f"PID|||{pid_3}||{name}||19800101|M|||123 RUE^^VILLE^^12345||0123456789\r"
        f"PV1||I|{location}|||||||||||||||||1|||||||||||||||||||||||||{now}\r"
        f"{zbe}\r"
    )


@pytest.mark.asyncio
async def test_ihe_pam_end_to_end(session: Session):
    # Créer la hiérarchie EG/Pôle/Service avec les bons identifiants
    from app.models_structure_fhir import EntiteGeographique
    from app.models_structure import Pole, Service, LocationStatus, LocationMode, LocationPhysicalType, LocationServiceType

    from sqlmodel import select
    EG_ID = "EG_TESTIHE"
    POLE_ID = "POLE_TESTIHE"
    SRV_ID = "SRV_TESTIHE"
    UF_CODE = "001"

    eg = session.exec(select(EntiteGeographique).where(EntiteGeographique.identifier == EG_ID)).first()
    if not eg:
        eg = EntiteGeographique(identifier=EG_ID, name="EG Test", finess="123456789")
        session.add(eg)
        session.commit()
        session.refresh(eg)

    pole = session.exec(select(Pole).where(Pole.identifier == POLE_ID)).first()
    if not pole:
        pole = Pole(identifier=POLE_ID, name="Pôle Test", entite_geo_id=eg.id, status=LocationStatus.ACTIVE, mode=LocationMode.INSTANCE, physical_type=LocationPhysicalType.SI)
        session.add(pole)
        session.commit()
        session.refresh(pole)

    service = session.exec(select(Service).where(Service.identifier == SRV_ID)).first()
    if not service:
        service = Service(identifier=SRV_ID, name="Service Test", pole_id=pole.id, service_type=LocationServiceType.MCO, status=LocationStatus.ACTIVE, mode=LocationMode.INSTANCE, physical_type=LocationPhysicalType.SI)
        session.add(service)
        session.commit()
        session.refresh(service)

    # Importer l’UF 001 via un message MFN^M05 (structure HL7)
    mfn_msg = (
        f"MSH|^~\\&|CPAGE|CPAGE|LOGICIEL|LOGICIEL|20251107173000||MFN^M05|MSG0001|P|2.5^FRA^2.1\r"
        f"MFI|UF|UPD|20251107173000|20251107173000|NE\r"
        f"MFE|MAD|001|20251107173000|A\r"
        f"ZFU|001|UF Test|{SRV_ID}|Service Test|{POLE_ID}|Pôle Test|{EG_ID}|EG Test|active|MCO|SI|FR\r"
    )
    from app.services.transport_inbound import on_message_inbound
    await on_message_inbound(mfn_msg, session, None)
    """Test le flux complet : admission → mouvements → sortie avec génération FHIR."""
    

    # 0. Injecter la hiérarchie structurelle minimale attendue (EG > Pôle > Service > UF)
    from app.models_structure_fhir import EntiteGeographique
    from app.models_structure import Pole, Service, UniteFonctionnelle, LocationStatus, LocationMode, LocationPhysicalType, LocationServiceType

    eg = EntiteGeographique(identifier="EG001", name="EG Test", finess="123456789")
    session.add(eg)
    session.commit()
    session.refresh(eg)

    pole = Pole(identifier="POLE001", name="Pôle Test", entite_geo_id=eg.id, status=LocationStatus.ACTIVE, mode=LocationMode.INSTANCE, physical_type=LocationPhysicalType.SI)
    session.add(pole)
    session.commit()
    session.refresh(pole)

    service = Service(identifier="SRV001", name="Service Test", pole_id=pole.id, service_type=LocationServiceType.MCO, status=LocationStatus.ACTIVE, mode=LocationMode.INSTANCE, physical_type=LocationPhysicalType.SI)
    session.add(service)
    session.commit()
    session.refresh(service)

    uf = UniteFonctionnelle(identifier="UF001", name="UF Test", service_id=service.id, status=LocationStatus.ACTIVE, mode=LocationMode.INSTANCE, physical_type=LocationPhysicalType.SI)
    session.add(uf)
    session.commit()
    session.refresh(uf)

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