#!/usr/bin/env python3
"""
Initialisation réaliste de patients, dossiers, venues et mouvements couvrant des cas IHE PAM,
sans collisions de séquences et avec identifiants CPAGE/NDA/VENUE.

- 5 patients/dossiers, chacun avec une séquence de mouvements variés (A01, A02, A03, A04, A05, A11, A13, A21, A22, A31, A38, A40)
- Données inspirées des profils IHE France (admissions, mutations, sorties, absences, annulations, fusions)

Usage :
    python tools/init_demo_movements.py [--reset] [--export-fhir]
"""
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
from sqlmodel import Session, SQLModel, select
from app.db import engine, get_next_sequence
from app.models import Patient, Dossier, Venue, Mouvement
from app.models_identifiers import Identifier, IdentifierType
from app.models_structure_fhir import IdentifierNamespace
from app.services.fhir import generate_fhir_bundle_for_dossier


def _load_namespaces(session: Session) -> dict:
    """Retourne un dict name -> (system, oid) pour CPAGE, NDA, VENUE, IPP, MOUVEMENT si présents.
    Fallback vers valeurs par défaut si manquants.
    """
    wanted = {"CPAGE": None, "NDA": None, "VENUE": None, "IPP": None, "MOUVEMENT": None}
    rows = session.exec(select(IdentifierNamespace).where(IdentifierNamespace.name.in_(wanted.keys()))).all()
    ns_map: dict[str, tuple[str, str | None]] = {}
    for ns in rows:
        ns_map[ns.name] = (ns.system, ns.oid)
    # defaults if missing
    ns_map.setdefault("CPAGE", ("urn:oid:1.2.250.1.211.10.200.2", "1.2.250.1.211.10.200.2"))
    ns_map.setdefault("NDA", ("urn:oid:1.2.250.1.213.1.1.1.2", "1.2.250.1.213.1.1.1.2"))
    ns_map.setdefault("VENUE", ("urn:oid:1.2.250.1.213.1.1.1.3", "1.2.250.1.213.1.1.1.3"))
    ns_map.setdefault("IPP", ("urn:oid:1.2.250.1.213.1.1.1.1", "1.2.250.1.213.1.1.1.1"))
    ns_map.setdefault("MOUVEMENT", ("urn:oid:1.2.250.1.213.1.1.1.4", "1.2.250.1.213.1.1.1.4"))
    return ns_map


def _add_identifier(session: Session, *, value: str, type_: IdentifierType, system: str, oid: str | None,
                    patient: Patient | None = None, dossier: Dossier | None = None,
                    venue: Venue | None = None, mouvement: Mouvement | None = None) -> Identifier:
    ident = Identifier(
        value=value,
        type=type_,
        system=system,
        oid=oid,
        patient_id=patient.id if patient else None,
        dossier_id=dossier.id if dossier else None,
        venue_id=venue.id if venue else None,
        mouvement_id=mouvement.id if mouvement else None,
        status="active",
    )
    session.add(ident)
    return ident


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Supprime et recrée les tables avant l'injection")
    parser.add_argument("--export-fhir", action="store_true", help="Exporte des Bundles FHIR (Patient+Encounter) des dossiers créés")
    args = parser.parse_args()

    # Réinitialisation optionnelle
    if args.reset:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)

    out_dir = Path("tools/output/fhir_demo_bundles")
    out_dir.mkdir(parents=True, exist_ok=True)

    with Session(engine) as session:
        ns = _load_namespaces(session)
        base_date = datetime(2025, 11, 3, 8, 0)

        created_dossiers: list[Dossier] = []
        patients: list[Patient] = []
        # Création de 5 patients dynamiques (séquences sûres)
        demo_patients = [
            dict(family="Martin", given="Sophie", gender="female", birth_date="1980-04-12",
                 address="12 rue des Lilas", city="Lyon", state="Auvergne-Rhône-Alpes", postal_code="69003", country="FRA",
                 phone="0478123456", mobile="0612345678", work_phone="0423456789", email="sophie.martin@example.com",
                 birth_address="Clinique de la Croix", birth_city="Lyon", birth_state="Auvergne-Rhône-Alpes", birth_postal_code="69003", birth_country="FRA",
                 identity_reliability_code="VALI", identity_reliability_date="2025-11-01", identity_reliability_source="CNI",
                 nir="2800412345678", marital_status="M", mothers_maiden_name="Durand", nationality="FRA", primary_care_provider="Dr. Petit"),
            dict(family="Durand", given="Pierre", gender="male", birth_date="1975-09-23",
                 address="5 avenue de la République", city="Villeurbanne", state="Auvergne-Rhône-Alpes", postal_code="69100", country="FRA",
                 phone="0478234567", mobile="0623456789", work_phone="0434567890", email="pierre.durand@example.com",
                 birth_address="Hôpital Edouard Herriot", birth_city="Lyon", birth_state="Auvergne-Rhône-Alpes", birth_postal_code="69003", birth_country="FRA",
                 identity_reliability_code="PROV", identity_reliability_date="2025-10-30", identity_reliability_source="Déclaration patient",
                 nir="1750932456789", marital_status="S", mothers_maiden_name="Lefevre", nationality="FRA", primary_care_provider="Dr. Bernard"),
            dict(family="Nguyen", given="Thi Mai", gender="female", birth_date="1992-01-15",
                 address="8 rue du 8 Mai 1945", city="Bron", state="Auvergne-Rhône-Alpes", postal_code="69500", country="FRA",
                 phone="0478345678", mobile="0634567890", work_phone="0445678901", email="thi.mai.nguyen@example.com",
                 birth_address="Hôpital Femme Mère Enfant", birth_city="Bron", birth_state="Auvergne-Rhône-Alpes", birth_postal_code="69500", birth_country="FRA",
                 identity_reliability_code="DOUTE", identity_reliability_date="2025-10-28", identity_reliability_source="Aucun document",
                 nir="2920115345678", marital_status="D", mothers_maiden_name="Pham", nationality="VNM", primary_care_provider="Dr. Nguyen"),
            dict(family="Bernard", given="Luc", gender="male", birth_date="1968-07-30",
                 address="22 chemin des Acacias", city="Caluire", state="Auvergne-Rhône-Alpes", postal_code="69300", country="FRA",
                 phone="0478456789", mobile="0645678901", work_phone="0456789012", email="luc.bernard@example.com",
                 birth_address="Clinique du Parc", birth_city="Caluire", birth_state="Auvergne-Rhône-Alpes", birth_postal_code="69300", birth_country="FRA",
                 identity_reliability_code="VIDE", identity_reliability_date="2025-10-25", identity_reliability_source="Non renseigné",
                 nir="1680730456789", marital_status="W", mothers_maiden_name="Martin", nationality="FRA", primary_care_provider="Dr. Leroy"),
            dict(family="Moreau", given="Julie", gender="female", birth_date="2001-12-05",
                 address="3 place Bellecour", city="Lyon", state="Auvergne-Rhône-Alpes", postal_code="69002", country="FRA",
                 phone="0478567890", mobile="0656789012", work_phone="0467890123", email="julie.moreau@example.com",
                 birth_address="Hôpital de la Croix-Rousse", birth_city="Lyon", birth_state="Auvergne-Rhône-Alpes", birth_postal_code="69004", birth_country="FRA",
                 identity_reliability_code="FICTI", identity_reliability_date="2025-10-20", identity_reliability_source="Test",
                 nir="2011256789012", marital_status="U", mothers_maiden_name="Dubois", nationality="FRA", primary_care_provider="Dr. Morel"),
        ]

        for pdata in demo_patients:
            pseq = get_next_sequence(session, "patient")
            patient = Patient(patient_seq=pseq, identifier=str(pseq), **pdata)
            session.add(patient)
            session.flush()
            patients.append(patient)
            # Identifier CPAGE (PI)
            cpage_system, cpage_oid = ns["CPAGE"]
            _add_identifier(session, value=str(pseq), type_=IdentifierType.PI, system=cpage_system, oid=cpage_oid, patient=patient)
            # Identifier IPP (distinct, formaté)
            ipp_system, ipp_oid = ns["IPP"]
            _add_identifier(session, value=f"IPP{pseq:08d}", type_=IdentifierType.IPP, system=ipp_system, oid=ipp_oid, patient=patient)

        session.flush()

        # Dossiers et venues
        for idx, patient in enumerate(patients):
            dseq = get_next_sequence(session, "dossier")
            dossier = Dossier(
                dossier_seq=dseq,
                patient_id=patient.id,
                uf_responsabilite="UF-CHIR",
                admit_time=base_date + timedelta(hours=idx),
            )
            session.add(dossier)
            session.flush()
            created_dossiers.append(dossier)
            # Identifier NDA pour le dossier (format réaliste)
            nda_system, nda_oid = ns["NDA"]
            _add_identifier(session, value=f"NDA{dseq:010d}", type_=IdentifierType.NDA, system=nda_system, oid=nda_oid, dossier=dossier)

            vseq = get_next_sequence(session, "venue")
            venue = Venue(
                venue_seq=vseq,
                dossier_id=dossier.id,
                uf_responsabilite="UF-CHIR",
                start_time=base_date + timedelta(hours=idx),
                code="HOSP",
                label="Chirurgie",
            )
            session.add(venue)
            session.flush()
            # Identifier VENUE (VN) formaté
            venue_system, venue_oid = ns["VENUE"]
            _add_identifier(session, value=f"VEN{vseq:010d}", type_=IdentifierType.VN, system=venue_system, oid=venue_oid, venue=venue)

            mouvements: list[Mouvement] = []
            # Séquences variées selon le patient
            if idx == 0:
                # Admission complète, mutation, sortie
                mouvements = [
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="admission",
                        when=base_date + timedelta(hours=idx), location="CHIR-101", note="Admission hospitalisée"
                    ),
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="mutation",
                        when=base_date + timedelta(hours=idx + 2), from_location="CHIR-101", to_location="CHIR-201", location="CHIR-201", note="Mutation de chambre"
                    ),
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="sortie",
                        when=base_date + timedelta(hours=idx + 6), location="CHIR-201", note="Sortie définitive"
                    ),
                ]
            elif idx == 1:
                # Préadmission, admission, annulation admission
                mouvements = [
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="préadmission",
                        when=base_date + timedelta(hours=idx), location="CHIR-ACC", note="Préadmission"
                    ),
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="admission",
                        when=base_date + timedelta(hours=idx + 1), location="CHIR-102", note="Admission hospitalisée"
                    ),
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="annulation admission",
                        when=base_date + timedelta(hours=idx + 2), location="CHIR-102", note="Annulation admission"
                    ),
                ]
            elif idx == 2:
                # Admission hospitalisée, absence temporaire (A03), retour (A22), sortie
                # Conforme IHE PAM : A03 seulement depuis Hospitalisation (I/R)
                mouvements = [
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="admission",
                        when=base_date + timedelta(hours=idx), location="MED-201", note="Admission hospitalisée"
                    ),
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="absence provisoire",
                        when=base_date + timedelta(hours=idx + 1), location="MED-201", note="Absence temporaire (A03) depuis hospitalisation"
                    ),
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="retour d'absence",
                        when=base_date + timedelta(hours=idx + 2), location="MED-201", note="Retour d'absence (A22)"
                    ),
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="sortie",
                        when=base_date + timedelta(hours=idx + 4), location="MED-201", note="Sortie définitive"
                    ),
                ]
            elif idx == 3:
                # Admission, annulation sortie, sortie
                mouvements = [
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="admission",
                        when=base_date + timedelta(hours=idx), location="MED-301", note="Admission hospitalisée"
                    ),
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="annulation sortie",
                        when=base_date + timedelta(hours=idx + 2), location="MED-301", note="Annulation sortie"
                    ),
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="sortie",
                        when=base_date + timedelta(hours=idx + 4), location="MED-301", note="Sortie définitive"
                    ),
                ]
            elif idx == 4:
                # Fusion patient, mise à jour info
                mouvements = [
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="fusion patient",
                        when=base_date + timedelta(hours=idx), location="ADMIN", note="Fusion patient (A40)"
                    ),
                    Mouvement(
                        venue_id=venue.id, mouvement_seq=get_next_sequence(session, "mouvement"),
                        movement_type="mise à jour identité",
                        when=base_date + timedelta(hours=idx + 1), location="ADMIN", note="Mise à jour identité (A31)"
                    ),
                ]
            session.add_all(mouvements)
            # Identifiants MOUVEMENT (MVT) pour chaque mouvement
            session.flush()
            mvt_system, mvt_oid = ns["MOUVEMENT"]
            for m in mouvements:
                _add_identifier(
                    session,
                    value=f"MVT{m.mouvement_seq:010d}",
                    type_=IdentifierType.MVT,
                    system=mvt_system,
                    oid=mvt_oid,
                    mouvement=m,
                )

        session.commit()

        print("✓ Jeu de données réaliste injecté (patients, dossiers, venues, mouvements IHE PAM)")

        # Export FHIR optionnel
        if args.export_fhir:
            exported = 0
            for d in created_dossiers:
                # refresh to ensure relationships are available
                session.refresh(d)
                _ = d.patient  # ensure lazy load
                _ = d.venues
                bundle = generate_fhir_bundle_for_dossier(d, session=session)
                out_file = out_dir / f"bundle-dossier-{d.dossier_seq}.json"
                with out_file.open("w", encoding="utf-8") as f:
                    json.dump(bundle, f, ensure_ascii=False, indent=2)
                exported += 1
            print(f"✓ Bundles FHIR exportés: {exported} fichier(s) dans {out_dir}")


if __name__ == "__main__":
    main()
