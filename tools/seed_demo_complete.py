#!/usr/bin/env python3
"""Seed complet GHT DEMO: structure + identités + mouvements.

Crée un GHT DEMO avec:
  - Entité juridique + namespaces (IPP, NDA, VENUE)
  - Structure hiérarchique complète: EG → Poles → Services → UF → UH → CH → Lits
  - Patients avec IPP + identité (nom, prénom, date naissance, adresse)
  - Dossiers avec NDA
  - Venues avec numéro de venue
  - Mouvements IHE PAM réalistes (A01 admission, A02 transfert, A03 sortie, A11 annulation)

Usage:
    python tools/seed_demo_complete.py [--reset]
"""
import sys, argparse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.db import engine, init_db, get_next_sequence
from app.models import Patient, Dossier, Venue, Mouvement, DossierType, Sequence
from app.models_identifiers import Identifier, IdentifierType
from app.models_structure_fhir import GHTContext, EntiteJuridique, EntiteGeographique, IdentifierNamespace
from app.models_structure import Pole, Service, UniteFonctionnelle, UniteHebergement, Chambre, Lit
from app.models_structure import LocationPhysicalType, LocationServiceType

def _reset_db():
    from sqlmodel import SQLModel
    print("⚠️  Suppression complète de la base...")
    SQLModel.metadata.drop_all(engine)
    init_db()
    print("✓ Base réinitialisée")

def _get_or_create_ght(session: Session) -> GHTContext:
    ght = session.exec(select(GHTContext).where(GHTContext.code == "GHT-DEMO")).first()
    if not ght:
        ght = GHTContext(
            name="GHT DEMO Complet",
            code="GHT-DEMO",
            description="GHT de démonstration avec structure et identités complètes",
            oid_racine="1.2.250.1.213.1.1",
            fhir_server_url="http://localhost:8000/fhir",
            is_active=True
        )
        session.add(ght); session.commit(); session.refresh(ght)
        print("✓ GHT DEMO créé")
    else:
        print("✓ GHT DEMO existant")
    return ght

def _create_ej(session: Session, ght: GHTContext) -> EntiteJuridique:
    ej = session.exec(select(EntiteJuridique).where(EntiteJuridique.finess_ej == "750000001")).first()
    if not ej:
        ej = EntiteJuridique(
            name="CHU Démo Paris",
            short_name="CHU DEMO",
            finess_ej="750000001",
            siren="123456789",
            siret="12345678900001",
            address_line="1 Rue de l'Hôpital",
            postal_code="75001",
            city="Paris",
            ght_context_id=ght.id,
            is_active=True,
            strict_pam_fr=True
        )
        session.add(ej); session.commit(); session.refresh(ej)
        print("✓ Entité juridique créée")
    else:
        print("✓ EJ existante")
    return ej

def _create_namespaces(session: Session, ght: GHTContext, ej: EntiteJuridique):
    ns_specs = [
        {"name": "IPP CHU DEMO", "system": "urn:oid:1.2.250.1.213.1.1.1", "type": "IPP", "ej": True},
        {"name": "NDA CHU DEMO", "system": "urn:oid:1.2.250.1.213.1.1.2", "type": "NDA", "ej": True},
        {"name": "VENUE CHU DEMO", "system": "urn:oid:1.2.250.1.213.1.1.3", "type": "VENUE", "ej": False},
        {"name": "STRUCTURE GHT", "system": "STRUCT-GHT-DEMO", "type": "STRUCTURE", "ej": False},
    ]
    for spec in ns_specs:
        existing = session.exec(
            select(IdentifierNamespace).where(
                IdentifierNamespace.system == spec["system"],
                IdentifierNamespace.ght_context_id == ght.id
            )
        ).first()
        if not existing:
            ns = IdentifierNamespace(
                name=spec["name"],
                system=spec["system"],
                type=spec["type"],
                ght_context_id=ght.id,
                entite_juridique_id=ej.id if spec["ej"] else None,
                is_active=True
            )
            session.add(ns)
    session.commit()
    print("✓ Namespaces créés")

def _create_structure(session: Session, ej: EntiteJuridique):
    # EG
    eg = session.exec(select(EntiteGeographique).where(EntiteGeographique.identifier == "CHU-DEMO-SITE-CENTRAL")).first()
    if not eg:
        eg = EntiteGeographique(
            identifier="CHU-DEMO-SITE-CENTRAL",
            name="CHU Démo Site Central",
            short_name="DEMO-CENTRAL",
            finess="750000002",
            address_line1="1 Rue de l'Hôpital",
            address_postalcode="75001",
            address_city="Paris",
            category_sae="MCO",
            type="MCO",
            physical_type="si",
            entite_juridique_id=ej.id,
            is_active=True
        )
        session.add(eg); session.commit(); session.refresh(eg)
        print("✓ EG créée")
    else:
        print("✓ EG existante")
    
    # Poles
    pole_specs = [
        {"id": "POLE-MED", "name": "Pôle Médecine"},
        {"id": "POLE-CHIR", "name": "Pôle Chirurgie"},
    ]
    poles = {}
    for ps in pole_specs:
        p = session.exec(select(Pole).where(Pole.identifier == ps["id"])).first()
        if not p:
            p = Pole(identifier=ps["id"], name=ps["name"], physical_type=LocationPhysicalType.AREA, entite_geo_id=eg.id, is_virtual=False)
            session.add(p); session.commit(); session.refresh(p)
        poles[ps["id"]] = p
    print(f"✓ {len(poles)} Pôles créés")
    
    # Services
    service_specs = [
        {"id": "SVC-MED-CARDIO", "name": "Cardiologie", "pole": "POLE-MED", "type": LocationServiceType.MCO},
        {"id": "SVC-MED-PNEUMO", "name": "Pneumologie", "pole": "POLE-MED", "type": LocationServiceType.MCO},
        {"id": "SVC-CHIR-ORTHO", "name": "Chirurgie Orthopédique", "pole": "POLE-CHIR", "type": LocationServiceType.MCO},
    ]
    services = {}
    for ss in service_specs:
        s = session.exec(select(Service).where(Service.identifier == ss["id"])).first()
        if not s:
            s = Service(
                identifier=ss["id"], name=ss["name"], physical_type=LocationPhysicalType.SI,
                service_type=ss["type"], pole_id=poles[ss["pole"]].id, is_virtual=False
            )
            session.add(s); session.commit(); session.refresh(s)
        services[ss["id"]] = s
    print(f"✓ {len(services)} Services créés")
    
    # UF
    uf_specs = [
        {"id": "UF-CARDIO-H", "name": "UF Cardio Hospitalisation", "service": "SVC-MED-CARDIO"},
        {"id": "UF-PNEUMO-H", "name": "UF Pneumo Hospitalisation", "service": "SVC-MED-PNEUMO"},
        {"id": "UF-ORTHO-H", "name": "UF Ortho Hospitalisation", "service": "SVC-CHIR-ORTHO"},
    ]
    ufs = {}
    for us in uf_specs:
        u = session.exec(select(UniteFonctionnelle).where(UniteFonctionnelle.identifier == us["id"])).first()
        if not u:
            u = UniteFonctionnelle(
                identifier=us["id"], name=us["name"], physical_type=LocationPhysicalType.SI,
                service_id=services[us["service"]].id
            )
            session.add(u); session.commit(); session.refresh(u)
        ufs[us["id"]] = u
    print(f"✓ {len(ufs)} UF créées")
    
    # UH
    uh_specs = [
        {"id": "UH-CARDIO-1", "name": "UH Cardio Étage 1", "uf": "UF-CARDIO-H"},
        {"id": "UH-PNEUMO-2", "name": "UH Pneumo Étage 2", "uf": "UF-PNEUMO-H"},
        {"id": "UH-ORTHO-3", "name": "UH Ortho Étage 3", "uf": "UF-ORTHO-H"},
    ]
    uhs = {}
    for uh_s in uh_specs:
        uh = session.exec(select(UniteHebergement).where(UniteHebergement.identifier == uh_s["id"])).first()
        if not uh:
            uh = UniteHebergement(
                identifier=uh_s["id"], name=uh_s["name"], physical_type=LocationPhysicalType.WI,
                unite_fonctionnelle_id=ufs[uh_s["uf"]].id
            )
            session.add(uh); session.commit(); session.refresh(uh)
        uhs[uh_s["id"]] = uh
    print(f"✓ {len(uhs)} UH créées")
    
    # Chambres + Lits (2 chambres / UH, 2 lits / chambre)
    ch_count = 0
    lit_count = 0
    for uh_id, uh in uhs.items():
        for ch_num in [1, 2]:
            ch_id = f"{uh_id}-CH{ch_num}"
            ch = session.exec(select(Chambre).where(Chambre.identifier == ch_id)).first()
            if not ch:
                ch = Chambre(
                    identifier=ch_id, name=f"Chambre {ch_num}", physical_type=LocationPhysicalType.RO,
                    unite_hebergement_id=uh.id
                )
                session.add(ch); session.commit(); session.refresh(ch)
                ch_count += 1
            for lit_num in [1, 2]:
                lit_id = f"{ch_id}-LIT{lit_num}"
                lit = session.exec(select(Lit).where(Lit.identifier == lit_id)).first()
                if not lit:
                    lit = Lit(
                        identifier=lit_id, name=f"Lit {lit_num}", physical_type=LocationPhysicalType.BD,
                        operational_status="O", chambre_id=ch.id
                    )
                    session.add(lit); session.commit()
                    lit_count += 1
    print(f"✓ {ch_count} Chambres, {lit_count} Lits créés")
    return eg, poles, services, ufs, uhs

def _create_patients_and_movements(session: Session):
    # Charger GHT et namespaces
    ght = session.exec(select(GHTContext).where(GHTContext.code == "GHT-DEMO")).first()
    namespaces_list = session.exec(
        select(IdentifierNamespace).where(IdentifierNamespace.ght_context_id == ght.id)
    ).all()
    namespaces = {ns.type: ns for ns in namespaces_list}
    
    # Séquences
    for seq_name in ["dossier", "venue", "mouvement"]:
        if not session.get(Sequence, seq_name):
            session.add(Sequence(name=seq_name, value=0))
    session.commit()
    
    now = datetime.utcnow()
    patient_specs = [
        {"family": "MARTIN", "given": "Alice", "birth": "1980-05-12", "gender": "female", "city": "Paris", "postal": "75001"},
        {"family": "DUPONT", "given": "Bernard", "birth": "1975-08-22", "gender": "male", "city": "Lyon", "postal": "69001"},
        {"family": "BERNARD", "given": "Claire", "birth": "1990-02-15", "gender": "female", "city": "Marseille", "postal": "13001"},
    ]
    
    for idx, ps in enumerate(patient_specs, start=1):
        existing = session.exec(select(Patient).where(Patient.family == ps["family"])).first()
        if existing:
            continue
        
        patient = Patient(
            family=ps["family"], given=ps["given"], birth_date=ps["birth"], gender=ps["gender"],
            city=ps["city"], postal_code=ps["postal"], country="FR",
            identity_reliability_code="VALI", identity_reliability_date="2024-01-15", identity_reliability_source="CNI"
        )
        session.add(patient); session.commit(); session.refresh(patient)
        
        # Créer identifiant IPP pour le patient
        ipp_ns = namespaces.get("IPP")
        if ipp_ns:
            ipp = Identifier(
                value=f"IPP{idx:06d}",
                type=IdentifierType.IPP,
                system=ipp_ns.system,
                oid=ipp_ns.system.split(":")[-1],  # Extraire OID de l'URN
                patient_id=patient.id,
                status="active"
            )
            session.add(ipp)
        
        dossier = Dossier(
            dossier_seq=get_next_sequence(session, "dossier"),
            patient_id=patient.id, uf_responsabilite=f"UF-CARDIO-H",
            admit_time=now, dossier_type=DossierType.HOSPITALISE, reason="Admission démonstration"
        )
        session.add(dossier); session.commit(); session.refresh(dossier)
        
        # Créer identifiant NDA pour le dossier
        nda_ns = namespaces.get("NDA")
        if nda_ns:
            nda = Identifier(
                value=f"NDA{dossier.dossier_seq:08d}",
                type=IdentifierType.NDA,
                system=nda_ns.system,
                oid=nda_ns.system.split(":")[-1],
                dossier_id=dossier.id,
                status="active"
            )
            session.add(nda)
        
        venue = Venue(
            venue_seq=get_next_sequence(session, "venue"),
            dossier_id=dossier.id, uf_responsabilite=dossier.uf_responsabilite,
            start_time=now, code=f"CARDIO-V{idx}", label=f"Venue Cardio {idx}", operational_status="active"
        )
        session.add(venue); session.commit(); session.refresh(venue)
        
        # Créer identifiant VENUE (Visit Number)
        venue_ns = namespaces.get("VENUE")
        if venue_ns:
            venue_id = Identifier(
                value=f"VEN{venue.venue_seq:08d}",
                type=IdentifierType.VN,  # VN = Visit Number
                system=venue_ns.system,
                oid=venue_ns.system.split(":")[-1],
                venue_id=venue.id,
                status="active"
            )
            session.add(venue_id)
        
        # Mouvements IHE PAM: A01 admission → A02 transfert → A03 sortie
        movements = [
            ("Admission", "A01", f"UH-CARDIO-1-CH1-LIT1"),
            ("Transfert", "A02", f"UH-CARDIO-1-CH2-LIT1"),
            ("Sortie", "A03", f"UH-CARDIO-1-CH2-LIT1"),
        ]
        for m_idx, (mt, trigger, loc) in enumerate(movements, start=1):
            mouvement = Mouvement(
                mouvement_seq=get_next_sequence(session, "mouvement"),
                venue_id=venue.id, when=now + timedelta(hours=m_idx),
                location=loc, trigger_event=trigger, movement_type=mt
            )
            session.add(mouvement)
        session.commit()
    
    patient_count = len(session.exec(select(Patient)).all())
    print(f"✓ {patient_count} Patients + Dossiers + Venues + Mouvements créés")

def main():
    parser = argparse.ArgumentParser(description="Seed complet GHT DEMO")
    parser.add_argument("--reset", action="store_true", help="Réinitialiser la base avant seed")
    args = parser.parse_args()
    
    if args.reset:
        _reset_db()
    else:
        init_db()
    
    with Session(engine) as session:
        print("🚀 Seed GHT DEMO complet...\n")
        
        ght = _get_or_create_ght(session)
        ej = _create_ej(session, ght)
        _create_namespaces(session, ght, ej)
        _create_structure(session, ej)
        _create_patients_and_movements(session)
        
        print("\n✅ Seed complet terminé")
        print(f"   GHT: {ght.name} (code={ght.code})")
        print(f"   EJ: {ej.name} (FINESS={ej.finess_ej})")
        print(f"   Structure: EG → Poles → Services → UF → UH → CH → Lits")
        print(f"   Identités: Patients avec IPP, Dossiers avec NDA, Venues")
        print(f"   Mouvements: IHE PAM (A01/A02/A03)")

if __name__ == "__main__":
    main()
