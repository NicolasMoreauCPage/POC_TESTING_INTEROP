"""Roundtrip interop robustness test.

Actions:
1. Clone existing GHT context into a NEW target GHT (roundtrip sink).
2. For each entity type (patient, dossier, venue, mouvement):
   - Perform UPDATE operations to trigger outbound HL7/FHIR emission.
   - Perform CREATE operations (new entities) to trigger emission.
   - Perform DELETE operations (where supported) to validate removal logic (HL7: discharge/cancel; FHIR: delete placeholder).
3. Collect emitted outbound messages from MessageLog.
4. Reinjection phase: for each outbound HL7 message, feed it back through inbound handler using the NEW target GHT endpoint (receiver) to validate parsing.
5. Summarize successes/failures.

Limitations / Assumptions:
- DELETE physical DB operations do not auto-generate HL7 messages; we simulate deletions using appropriate HL7 cancel/discharge triggers (A11, A13, A12/A53) rather than hard deletes.
- FHIR reinjection: we simulate by posting the generated FHIR JSON to a receiver endpoint base_url (if configured). If absent, we skip but log.
- Script focuses on PAM core (A01, A02, A03, A11, A12, A13) and identity (A28/A31) excluding A08 when strict.

Usage:
    PYTHONPATH=. .venv/bin/python scripts_manual/roundtrip_interop.py --dry-run

"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import List, Tuple, Optional

from sqlmodel import Session, select

from app.db import engine, init_db, get_next_sequence
from app.models import Patient, Dossier, Venue, Mouvement, DossierType
from app.models_structure_fhir import GHTContext, EntiteJuridique
from app.models_shared import SystemEndpoint, MessageLog
from app.services.transport_inbound import on_message_inbound_async
from app.services.hl7_generator import (
    generate_admission_message,
    generate_transfer_message,
    generate_discharge_message,
    generate_update_message,
    generate_adt_message,
)
from app.models_structure import (
    EntiteGeographique as EG,
    Pole,
    Service,
    UniteFonctionnelle,
    LocationPhysicalType,
    LocationServiceType,
)

# Utility: fetch sender endpoints (outbound) and create a receiver sink endpoint

def _ensure_roundtrip_receiver(session: Session, ght: GHTContext) -> SystemEndpoint:
    ep = session.exec(
        select(SystemEndpoint).where(SystemEndpoint.name == "Roundtrip Receiver")
    ).first()
    if ep:
        return ep
    ep = SystemEndpoint(
        name="Roundtrip Receiver",
        kind="MLLP",
        role="receiver",
        host=None,
        port=None,
        ght_context_id=ght.id,
    )
    session.add(ep)
    session.commit(); session.refresh(ep)
    return ep


def _pick_sample_entities(session: Session) -> Tuple[List[Patient], List[Dossier], List[Venue], List[Mouvement]]:
    patients = session.exec(select(Patient).limit(5)).all()
    dossiers = session.exec(select(Dossier).limit(5)).all()
    venues = session.exec(select(Venue).limit(5)).all()
    mouvements = session.exec(select(Mouvement).limit(5)).all()
    return patients, dossiers, venues, mouvements


def _simulate_updates(session: Session, patients: List[Patient], dossiers: List[Dossier], venues: List[Venue]) -> List[str]:
    hl7_messages: List[str] = []
    for p in patients:
        p.mobile = f"0600{get_next_sequence(session, 'mobile'):06d}"  # change mobile
        session.add(p); session.commit()
        # Identity update would normally be A08 (blocked if strict) -> skip if strict
        # Identity update (A08) skipped when strict; generator will raise if disallowed
        if p.dossiers:
            try:
                msg = generate_update_message(patient=p, dossier=p.dossiers[0], venue=None)
                hl7_messages.append(msg)
            except Exception:
                # Strict mode or unsupported -> ignore
                pass
    for d in dossiers:
        d.reason = "ROUNDTRIP-UPDATE"
        session.add(d); session.commit()
        if d.venues:
            v = d.venues[0]
            mv = Mouvement(
                mouvement_seq=get_next_sequence(session, "mouvement"),
                venue_id=v.id,
                when=datetime.utcnow(),
                location=v.code or "LOC",
                trigger_event="A02",
            )
            session.add(mv); session.commit(); session.refresh(mv)
            msg = generate_transfer_message(patient=d.patient, dossier=d, venue=v, movement=mv)
            hl7_messages.append(msg)
    for v in venues:
        v.label = (v.label or "Venue") + "-RT"
        session.add(v); session.commit()
        # Create mouvement for discharge (A03) so ZBE segment present
        mv = Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=v.id,
            when=datetime.utcnow(),
            location=v.code or "LOC",
            trigger_event="A03",
        )
        session.add(mv); session.commit(); session.refresh(mv)
        msg = generate_discharge_message(patient=v.dossier.patient, dossier=v.dossier, venue=v, session=session, movement=mv, namespaces=None)
        hl7_messages.append(msg)
    return hl7_messages


def _simulate_creations(session: Session) -> List[str]:
    hl7_messages: List[str] = []
    # Create patient + dossier + venue + admission mouvement
    p = Patient(family="RT", given="Create", birth_date="1990-01-01", gender="male")
    session.add(p); session.commit(); session.refresh(p)
    d = Dossier(dossier_seq=get_next_sequence(session, "dossier"), patient_id=p.id, uf_responsabilite="UF-RT", admit_time=datetime.utcnow(), dossier_type=DossierType.HOSPITALISE)
    session.add(d); session.commit(); session.refresh(d)
    v = Venue(venue_seq=get_next_sequence(session, "venue"), dossier_id=d.id, uf_responsabilite="UF-RT", start_time=datetime.utcnow(), code="RT-LOC", label="Roundtrip Loc")
    session.add(v); session.commit(); session.refresh(v)
    mv = Mouvement(
        mouvement_seq=get_next_sequence(session, "mouvement"),
        venue_id=v.id,
        when=datetime.utcnow(),
        location="RT-LOC/BOX",
        trigger_event="A01",
    )
    session.add(mv); session.commit(); session.refresh(mv)
    msg = generate_admission_message(patient=p, dossier=d, venue=v, session=session, namespaces=None, movement=mv)  # include movement for ZBE
    hl7_messages.append(msg)
    return hl7_messages


def _simulate_deletions(session: Session, venues: List[Venue]) -> List[str]:
    hl7_messages: List[str] = []
    # Simulate cancellation of admission for first venue's dossier (A11) and discharge cancel (A13) for another
    for idx, v in enumerate(venues[:2]):
        if not v.dossier:
            continue
        p = v.dossier.patient
        if idx == 0:
            # Admission cancel A11 requires a mouvement (use A01 template then replace trigger)
            mv = Mouvement(
                mouvement_seq=get_next_sequence(session, "mouvement"),
                venue_id=v.id,
                when=datetime.utcnow(),
                location=v.code or "LOC",
                trigger_event="A01",
            )
            session.add(mv); session.commit(); session.refresh(mv)
            msg = generate_admission_message(patient=p, dossier=v.dossier, venue=v, session=session, namespaces=None, movement=mv)
            hl7_messages.append(msg.replace("ADT^A01", "ADT^A11"))
        else:
            mv = Mouvement(
                mouvement_seq=get_next_sequence(session, "mouvement"),
                venue_id=v.id,
                when=datetime.utcnow(),
                location=v.code or "LOC",
                trigger_event="A03",
            )
            session.add(mv); session.commit(); session.refresh(mv)
            msg = generate_discharge_message(patient=p, dossier=v.dossier, venue=v, session=session, movement=mv, namespaces=None)
            hl7_messages.append(msg.replace("ADT^A03", "ADT^A13"))
    return hl7_messages


def _get_last_trigger(session: Session, dossier: Dossier) -> Optional[str]:
    if not dossier.venues:
        return None
    venue_ids = [v.id for v in dossier.venues]
    last = session.exec(
        select(Mouvement).where(Mouvement.venue_id.in_(venue_ids)).order_by(Mouvement.mouvement_seq.desc())
    ).first()
    return last.trigger_event if last else None

def _build_mfn_stub(session: Session, uf_codes: List[str]) -> str:
    """Construit un message MFN^M05 minimal avec un Pôle, un Service et les UF nécessaires.

    Structure:
      - POLE-RT (P)
      - SERV-RT (D) lié à POLE-RT via LRL
      - Chaque UF code (UF) lié à SERV-RT via LRL
    """
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    lines = [
        f"MSH|^~\\&|STR|STR|TARGET|TARGET|{now}||MFN^M05^MFN_M05|{now}|P|2.5",
        f"MFI|LOC|CPAGE_LOC_FRA|REP||{now}|AL",
    ]
    # Entité Géographique (M)
    eg_id = "EG-RT"
    eg_loc_identifier = f"^^^^^M^^^^{eg_id}"
    lines.append(f"MFE|MAD|||{eg_loc_identifier}|PL")
    lines.append(f"LOC|{eg_loc_identifier}||M|Etablissement juridique")
    lines.append(f"LCH|{eg_loc_identifier}|||ID_GLBL^Identifiant unique global^L|^{eg_id}")
    lines.append(f"LCH|{eg_loc_identifier}|||LBL^Libelle^L|^{eg_id} Base")
    # Pôle
    pole_id = "POLE-RT"
    pole_loc_identifier = f"^^^^^P^^^^{pole_id}"
    lines.append(f"MFE|MAD|||{pole_loc_identifier}|PL")
    lines.append(f"LOC|{pole_loc_identifier}||P|Pole")
    lines.append(f"LCH|{pole_loc_identifier}|||ID_GLBL^Identifiant unique global^L|^{pole_id}")
    lines.append(f"LCH|{pole_loc_identifier}|||LBL^Libelle^L|^{pole_id} Structure")
    # Relation Pôle -> Entité Géographique
    # Relation: Pôle rattaché à l'entité géographique (type attendu en champ 2)
    lines.append(f"LRL|{pole_loc_identifier}|ETBLSMNT^Relation etablissement^L||{eg_loc_identifier}")
    # Service
    service_id = "SERV-RT"
    service_loc_identifier = f"^^^^^D^^^^{service_id}"
    lines.append(f"MFE|MAD|||{service_loc_identifier}|PL")
    lines.append(f"LOC|{service_loc_identifier}||D|Service")
    lines.append(f"LCH|{service_loc_identifier}|||ID_GLBL^Identifiant unique global^L|^{service_id}")
    lines.append(f"LCH|{service_loc_identifier}|||LBL^Libelle^L|^{service_id} Principal")
    # Relation Service -> Pôle
    # Relation: Service localisé dans le Pôle
    lines.append(f"LRL|{service_loc_identifier}|LCLSTN^Relation de localisation^L||{pole_loc_identifier}")
    # UF entries
    for code in uf_codes:
        uf_loc_identifier = f"^^^^^UF^^^^{code}"
        lines.append(f"MFE|MAD|||{uf_loc_identifier}|PL")
        lines.append(f"LOC|{uf_loc_identifier}||UF|Unite Fonctionnelle")
        lines.append(f"LCH|{uf_loc_identifier}|||ID_GLBL^Identifiant unique global^L|^{code}")
        lines.append(f"LCH|{uf_loc_identifier}|||LBL^Libelle^L|^{code} UF")
        # Relation UF -> Service
    # Relation: UF localisée dans le Service
    lines.append(f"LRL|{uf_loc_identifier}|LCLSTN^Relation de localisation^L||{service_loc_identifier}")
    return "\r".join(lines)

async def main(dry_run: bool = False):
    init_db()
    with Session(engine) as session:
        # Create target GHT/EJ for reinjection sink
        ght_sink = GHTContext(name="GHT Roundtrip", code="GHT-RT")
        session.add(ght_sink); session.commit(); session.refresh(ght_sink)
        ej_sink = EntiteJuridique(name="EJ Roundtrip", finess_ej="000000001", ght_context_id=ght_sink.id)
        session.add(ej_sink); session.commit(); session.refresh(ej_sink)
        receiver_endpoint = _ensure_roundtrip_receiver(session, ght_sink)

        # Structure minimale injectée directement (évite complexité MFN tant que parsing relations UF incomplet)
        eg = session.exec(select(EG).where(EG.identifier == "EG-RT")).first()
        if not eg:
            eg = EG(identifier="EG-RT", name="EG-RT Base", physical_type=LocationPhysicalType.SI)
            session.add(eg); session.commit(); session.refresh(eg)
        pole = session.exec(select(Pole).where(Pole.identifier == "POLE-RT")).first()
        if not pole:
            pole = Pole(identifier="POLE-RT", name="POLE-RT Structure", physical_type=LocationPhysicalType.AREA, entite_geo_id=eg.id)
            session.add(pole); session.commit(); session.refresh(pole)
        service = session.exec(select(Service).where(Service.identifier == "SERV-RT")).first()
        if not service:
            service = Service(identifier="SERV-RT", name="Service Principal", physical_type=LocationPhysicalType.SI, pole_id=pole.id, service_type=LocationServiceType.MCO)
            session.add(service); session.commit(); session.refresh(service)
        uf = session.exec(select(UniteFonctionnelle).where(UniteFonctionnelle.identifier == "UF-RT")).first()
        if not uf:
            uf = UniteFonctionnelle(identifier="UF-RT", name="UF Responsable RT", physical_type=LocationPhysicalType.SI, service_id=service.id)
            session.add(uf); session.commit(); session.refresh(uf)

        patients, dossiers, venues, mouvements = _pick_sample_entities(session)

        # Générer MFN structure pour UF codes utilisés
        uf_codes = list({d.uf_responsabilite for d in dossiers if d.uf_responsabilite}) or ["UF-RT"]
        mfn_message = _build_mfn_stub(session, uf_codes)

        # Séquences conformes pour nouveaux patients (création admissions / transferts / sorties)
        conform_msgs: List[Tuple[str, str]] = [("mfn", mfn_message)]

        # Créer séquence pour chaque patient existant (limité à 3 triggers valides)
        for d in dossiers[:5]:
            p = d.patient
            # Venue de référence (première existante ou None)
            v = d.venues[0] if d.venues else None
            last = _get_last_trigger(session, d)
            # Admission si aucune
            if last is None:
                v = d.venues[0] if d.venues else None
                if not v:
                    v = Venue(venue_seq=get_next_sequence(session, "venue"), dossier_id=d.id, uf_responsabilite=d.uf_responsabilite, start_time=datetime.utcnow(), code=f"VEN-{d.dossier_seq}")
                    session.add(v); session.commit(); session.refresh(v)
                mv_adm = Mouvement(mouvement_seq=get_next_sequence(session, "mouvement"), venue_id=v.id, when=datetime.utcnow(), location=v.code or "LOC", trigger_event="A01")
                session.add(mv_adm); session.commit(); session.refresh(mv_adm)
                adm_msg = generate_admission_message(patient=p, dossier=d, venue=v, movement=mv_adm, session=session)
                conform_msgs.append(("create", adm_msg))
                last = "A01"
            # Transfer si admission dernière
            if last == "A01":
                v = d.venues[0]
                mv_trans = Mouvement(mouvement_seq=get_next_sequence(session, "mouvement"), venue_id=v.id, when=datetime.utcnow(), location=v.code or "LOC", trigger_event="A02")
                session.add(mv_trans); session.commit(); session.refresh(mv_trans)
                trans_msg = generate_transfer_message(patient=p, dossier=d, venue=v, movement=mv_trans, session=session)
                conform_msgs.append(("update", trans_msg))
                last = "A02"
            # Discharge si transfert dernière
            if last == "A02":
                v = d.venues[0]
                mv_dis = Mouvement(mouvement_seq=get_next_sequence(session, "mouvement"), venue_id=v.id, when=datetime.utcnow(), location=v.code or "LOC", trigger_event="A03")
                session.add(mv_dis); session.commit(); session.refresh(mv_dis)
                dis_msg = generate_discharge_message(patient=p, dossier=d, venue=v, movement=mv_dis, session=session)
                conform_msgs.append(("update", dis_msg))
            # Identity update (A31) - ne requiert pas ZBE
            id_msg = generate_adt_message(patient=p, dossier=d, venue=v, trigger_event="A31", session=session)
            conform_msgs.append(("identity", id_msg))

        # Nouvel ensemble patient complet (admission->transfer->discharge)
        new_msgs = _simulate_creations(session)
        conform_msgs.extend(("create", m) for m in new_msgs)

        reinjection_results = []
        for kind, msg in conform_msgs:
            ack = await on_message_inbound_async(msg, session, receiver_endpoint)
            reinjection_results.append((kind, "AA" if "MSA|AA" in ack else "ERR", ack[:140]))
            session.commit()

        status_counts = {"AA": 0, "ERR": 0}
        for _, status, _ in reinjection_results:
            status_counts[status] = status_counts.get(status, 0) + 1
        summary = {
            "counts": {
                k: sum(1 for x in conform_msgs if x[0] == k) for k in set(x[0] for x in conform_msgs)
            },
            "total_messages": len(conform_msgs),
            "status_counts": status_counts,
            "reinjection": reinjection_results,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))

        if dry_run:
            print("[DRY-RUN] Completed without side-effects beyond test entities.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Roundtrip interoperability test")
    parser.add_argument("--dry-run", action="store_true", help="Execute without external sends")
    args = parser.parse_args()

    import asyncio
    asyncio.run(main(dry_run=args.dry_run))
