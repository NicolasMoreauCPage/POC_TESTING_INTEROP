#!/usr/bin/env python3
"""
Script maître d'initialisation complète de la base de données de démonstration

Ce script :
1. Crée les tables de la base de données
2. Initialise UN SEUL GHT avec tous ses paramètres
3. Ajoute les espaces de noms (namespaces)
4. Initialise les vocabulaires
5. Crée la structure hospitalière de test
6. Importe les scénarios d'interopérabilité
7. Injecte un jeu de données réaliste IHE PAM (patients, dossiers, venues, mouvements)
"""

from sqlmodel import Session, select, SQLModel
from app.db import engine
from app.models_structure_fhir import GHTContext, IdentifierNamespace
# Ajout des imports manquants
import argparse
import sys
import subprocess
from pathlib import Path
parent_dir = str(Path(__file__).resolve().parent.parent)
# Import des autres scripts
from app.vocabulary_init import init_vocabularies
from app.services.structure_seed import DEMO_STRUCTURE, ensure_demo_structure
from datetime import datetime, timedelta

# Import domain models and helpers for seeding
from app.models import Patient, Dossier, Venue, Mouvement
from app.db import get_session, get_next_sequence

# ---------------------------
# Helpers de seeding multi-venue
# ---------------------------
def _create_patient_and_dossier(session: Session, family: str, given: str, uf: str) -> tuple[Patient, Dossier]:
    pat_seq = get_next_sequence(session, "patient")
    patient = Patient(
        patient_seq=pat_seq,
        identifier=str(pat_seq),
        family=family,
        given=given,
        gender="other",
    )
    session.add(patient)
    session.flush()

    dossier = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=patient.id,
        uf_responsabilite=uf,
        admit_time=datetime.now(),
    )
    session.add(dossier)
    session.flush()
    return patient, dossier


def _seed_multi_venue_chemo(session: Session) -> None:
    """Crée un dossier HDJ Onco avec 3 venues, et pour chacune A01 puis A03."""
    _, dossier = _create_patient_and_dossier(session, family="CHEMO", given="Demo", uf="HDJ-ONCO")
    base_time = datetime.now()
    venues: list[Venue] = []
    for i in range(1, 4):
        v = Venue(
            venue_seq=get_next_sequence(session, "venue"),
            dossier_id=dossier.id,
            uf_responsabilite="HDJ-ONCO",
            start_time=base_time + timedelta(minutes=i * 60),
            code="HDJ-ONCO",
            label=f"Chimiothérapie - Séance {i}",
        )
        session.add(v)
        session.flush()
        venues.append(v)

    # A01 + A03 pour chaque venue
    for idx, v in enumerate(venues):
        admit_time = base_time + timedelta(minutes=idx * 60 + 0)
        discharge_time = base_time + timedelta(minutes=idx * 60 + 45)
        m1 = Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=v.id,
            type="ADT^A01",
            when=admit_time,
            location=f"HDJ-ONCO-{idx+1:02d}",
            movement_type="admission",
            trigger_event="A01",
        )
        m2 = Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=v.id,
            type="ADT^A03",
            when=discharge_time,
            location=f"HDJ-ONCO-{idx+1:02d}",
            movement_type="discharge",
            trigger_event="A03",
        )
        session.add(m1)
        session.add(m2)
    session.commit()


def _seed_patient_multiple_dossiers(session: Session) -> None:
    """Crée un patient unique avec plusieurs dossiers représentant des prises en charge distinctes
    au sein du même hôpital, chacun avec une ou plusieurs venues et mouvements cohérents.

    - Dossier 1: HDJ-ONCO (R) avec 2 venues (A01 -> A03 chacune)
    - Dossier 2: HDJ-PSY (R) avec 1 venue (A01 -> A03)
    - Dossier 3: HOSP-MED (I) avec 1 venue (A01 -> A03)
    """
    patient, _ = _create_patient_and_dossier(session, family="MULTI", given="DOSSIERS", uf="HDJ-ONCO")

    # Dossier 1: HDJ-ONCO avec 2 venues
    dossier1 = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=patient.id,
        uf_responsabilite="HDJ-ONCO",
        admit_time=datetime.now(),
    )
    session.add(dossier1)
    session.flush()

    # Dossier 2: HDJ-PSY avec 1 venue
    dossier2 = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=patient.id,
        uf_responsabilite="HDJ-PSY",
        admit_time=datetime.now(),
    )
    session.add(dossier2)
    session.flush()

    # Dossier 3: HOSP-MED (hospitalisation complète I)
    dossier3 = Dossier(
        dossier_seq=get_next_sequence(session, "dossier"),
        patient_id=patient.id,
        uf_responsabilite="HOSP-MED",
        admit_time=datetime.now(),
    )
    session.add(dossier3)
    session.flush()

    base_time = datetime.now()

    # Dossier 1: deux venues HDJ-ONCO
    venues1: list[Venue] = []
    for i in range(1, 3):
        v = Venue(
            venue_seq=get_next_sequence(session, "venue"),
            dossier_id=dossier1.id,
            uf_responsabilite="HDJ-ONCO",
            start_time=base_time + timedelta(minutes=i * 30),
            code="HDJ-ONCO",
            label=f"Chimiothérapie - Séance {i}",
        )
        session.add(v)
        session.flush()
        venues1.append(v)

    for idx, v in enumerate(venues1):
        admit_time = base_time + timedelta(minutes=idx * 30 + 0)
        discharge_time = base_time + timedelta(minutes=idx * 30 + 20)
        session.add(Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=v.id,
            type="ADT^A01",
            when=admit_time,
            location=f"HDJ-ONCO-{idx+1:02d}",
            movement_type="admission",
            trigger_event="A01",
        ))
        session.add(Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=v.id,
            type="ADT^A03",
            when=discharge_time,
            location=f"HDJ-ONCO-{idx+1:02d}",
            movement_type="discharge",
            trigger_event="A03",
        ))

    # Dossier 2: une venue HDJ-PSY
    vpsy = Venue(
        venue_seq=get_next_sequence(session, "venue"),
        dossier_id=dossier2.id,
        uf_responsabilite="HDJ-PSY",
        start_time=base_time + timedelta(hours=2),
        code="HDJ-PSY",
        label="HDJ Psychiatrie - Suivi",
    )
    session.add(vpsy)
    session.flush()
    session.add(Mouvement(
        mouvement_seq=get_next_sequence(session, "mouvement"),
        venue_id=vpsy.id,
        type="ADT^A01",
        when=base_time + timedelta(hours=2, minutes=0),
        location="HDJ-PSY-01",
        movement_type="admission",
        trigger_event="A01",
    ))
    session.add(Mouvement(
        mouvement_seq=get_next_sequence(session, "mouvement"),
        venue_id=vpsy.id,
        type="ADT^A03",
        when=base_time + timedelta(hours=2, minutes=40),
        location="HDJ-PSY-01",
        movement_type="discharge",
        trigger_event="A03",
    ))

    # Dossier 3: une venue HOSP-MED (I)
    vhosp = Venue(
        venue_seq=get_next_sequence(session, "venue"),
        dossier_id=dossier3.id,
        uf_responsabilite="HOSP-MED",
        start_time=base_time + timedelta(hours=6),
        code="HOSP-MED",
        label="Hospitalisation Médecine",
    )
    session.add(vhosp)
    session.flush()
    session.add(Mouvement(
        mouvement_seq=get_next_sequence(session, "mouvement"),
        venue_id=vhosp.id,
        type="ADT^A01",
        when=base_time + timedelta(hours=6, minutes=0),
        location="MED-101",
        movement_type="admission",
        trigger_event="A01",
    ))
    session.add(Mouvement(
        mouvement_seq=get_next_sequence(session, "mouvement"),
        venue_id=vhosp.id,
        type="ADT^A03",
        when=base_time + timedelta(hours=24),
        location="MED-101",
        movement_type="discharge",
        trigger_event="A03",
    ))

    session.commit()
def _seed_multi_venue_psy(session: Session) -> None:
    """Crée un dossier HDJ Psy avec 3 venues, et pour chacune A01 puis A03."""
    _, dossier = _create_patient_and_dossier(session, family="PSY", given="HDJ", uf="HDJ-PSY")
    base_time = datetime.now()
    labels = [
        "HDJ Psychiatrie - Evaluation",
        "HDJ Psychiatrie - Thérapie de groupe",
        "HDJ Psychiatrie - Suivi",
    ]
    venues: list[Venue] = []
    for i, label in enumerate(labels, start=1):
        v = Venue(
            venue_seq=get_next_sequence(session, "venue"),
            dossier_id=dossier.id,
            uf_responsabilite="HDJ-PSY",
            start_time=base_time + timedelta(minutes=i * 60),
            code="HDJ-PSY",
            label=label,
        )
        session.add(v)
        session.flush()
        venues.append(v)

    for idx, v in enumerate(venues):
        admit_time = base_time + timedelta(minutes=idx * 60 + 0)
        discharge_time = base_time + timedelta(minutes=idx * 60 + 30)
        m1 = Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=v.id,
            type="ADT^A01",
            when=admit_time,
            location=f"HDJ-PSY-{idx+1:02d}",
            movement_type="admission",
            trigger_event="A01",
        )
        m2 = Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=v.id,
            type="ADT^A03",
            when=discharge_time,
            location=f"HDJ-PSY-{idx+1:02d}",
            movement_type="discharge",
            trigger_event="A03",
        )
        session.add(m1)
        session.add(m2)
    session.commit()
def init_ght_and_namespaces(session: Session, reset: bool = False) -> GHTContext:
    # Initialise le GHT unique avec tous ses namespaces
    # Chercher le GHT existant
    ght = session.exec(
        select(GHTContext).where(GHTContext.code == "GHT-DEMO-INTEROP")
    ).first()
    if ght and not reset:
        print(f"✓ GHT existant trouvé: {ght.name} (id={ght.id})")
    else:
        if ght and reset:
            print(f"Suppression de l'ancien GHT (id={ght.id})...")
            session.delete(ght)
            session.commit()
        print("Création du GHT Démo Interop...")
        ght = GHTContext(
            name="GHT Démo Interop",
            code="GHT-DEMO-INTEROP",
            description="GHT de démonstration complet pour tests d'interopérabilité",
            oid_racine="1.2.250.1.213.1.1.1",
            fhir_server_url="http://localhost:8000/fhir",
            is_active=True
        )
        session.add(ght)
        session.commit()
        session.refresh(ght)
        print(f"✓ GHT créé (id={ght.id})")
    
    # Créer les espaces de noms
    namespaces_config = [
        {
            "name": "CPAGE",
            "description": "Identifiants CPAGE",
            "oid": "1.2.250.1.211.10.200.2",
            "system": "urn:oid:1.2.250.1.211.10.200.2",
            "type": "PI"
        },
        {
            "name": "IPP",
            "description": "Identifiant Patient Permanent",
            "oid": "1.2.250.1.213.1.1.1.1",
            "system": "urn:oid:1.2.250.1.213.1.1.1.1",
            "type": "IPP"
        },
        {
            "name": "NDA",
            "description": "Numéro de Dossier Administratif",
            "oid": "1.2.250.1.213.1.1.1.2",
            "system": "urn:oid:1.2.250.1.213.1.1.1.2",
            "type": "NDA"
        },
        {
            "name": "VENUE",
            "description": "Identifiant de venue/séjour",
            "oid": "1.2.250.1.213.1.1.1.3",
            "system": "urn:oid:1.2.250.1.213.1.1.1.3",
            "type": "VN"
        },
        {
            "name": "MOUVEMENT",
            "description": "Identifiant de mouvement patient (ZBE-1)",
            "oid": "1.2.250.1.213.1.1.1.4",
            "system": "urn:oid:1.2.250.1.213.1.1.1.4",
            "type": "MVT"
        },
        {
            "name": "FINESS",
            "description": "Numéro FINESS des établissements",
            "oid": "1.2.250.1.71.4.2.2",
            "system": "urn:oid:1.2.250.1.71.4.2.2",
            "type": "FINESS"
        }
    ]
    
    ns_count = 0
    for ns_config in namespaces_config:
        ns = session.exec(
            select(IdentifierNamespace).where(
                IdentifierNamespace.name == ns_config["name"],
                IdentifierNamespace.ght_context_id == ght.id
            )
        ).first()
        
        if not ns:
            print(f"  • Création namespace {ns_config['name']}...")
            ns = IdentifierNamespace(
                name=ns_config["name"],
                description=ns_config["description"],
                oid=ns_config["oid"],
                system=ns_config["system"],
                type=ns_config["type"],
                ght_context_id=ght.id,
                is_active=True
            )
            session.add(ns)
            ns_count += 1
        else:
            print(f"  ✓ Namespace {ns_config['name']} existe déjà")
    
    if ns_count > 0:
        session.commit()
        print(f"✓ {ns_count} nouveaux namespaces créés")
    
    return ght

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Supprime et recrée toute la base de données"
    )
    parser.add_argument(
        "--export-fhir",
        action="store_true",
        help="Exporte les Bundles FHIR lors de l'injection du jeu de données de démonstration"
    )
    # Les semis multi-venues font désormais partie du jeu standard (plus de flags requis)
    args = parser.parse_args()
    
    print("="*70)
    print("INITIALISATION COMPLÈTE DE LA BASE DE DONNÉES DE DÉMONSTRATION")
    print("="*70)
    
    # Étape 1: Créer/recréer les tables
    print("\n[1/5] Création des tables de la base de données...")
    if args.reset:
        print("  ⚠️  Mode RESET: Suppression de toutes les données existantes")
        SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    print("  ✓ Tables créées")
    
    with Session(engine) as session:
        # Étape 2: Créer le GHT et les namespaces
        print("\n[2/5] Initialisation du GHT et des namespaces...")
        ght = init_ght_and_namespaces(session, reset=args.reset)
        # Conserver l'identifiant avant la fermeture de la session pour éviter
        # DetachedInstanceError lors de l'affichage final
        ght_id = ght.id
        
        # Étape 3: Initialiser les vocabulaires
        print("\n[3/5] Initialisation des vocabulaires...")
        try:
            init_vocabularies(session)
            print("  ✓ Vocabulaires initialisés")
        except Exception as e:
            print(f"  ⚠️  Erreur lors de l'initialisation des vocabulaires: {e}")
        
        # Étape 4: Créer la structure hospitalière
        print("\n[4/5] Création de la structure hospitalière de test...")
        try:
            stats = ensure_demo_structure(session, ght, DEMO_STRUCTURE)
            print(f"  ✓ Structure créée:")
            for entity_type, count in stats['created'].items():
                if count > 0:
                    print(f"    • {entity_type}: {count} créé(s)")
        except Exception as e:
            print(f"  ⚠️  Erreur lors de la création de la structure: {e}")
    
    # Étape 5: Importer les scénarios d'interopérabilité
    print("\n[5/5] Import des scénarios d'interopérabilité...")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "tools.init_interop_scenarios"],
            capture_output=True,
            text=True,
            cwd=parent_dir
        )
        if result.returncode == 0:
            print("  ✓ Scénarios importés")
            # Afficher les 3 dernières lignes du résultat
            lines = result.stdout.strip().split('\n')
            for line in lines[-3:]:
                print(f"    {line}")
        else:
            print(f"  ⚠️  Erreur lors de l'import des scénarios")
            print(f"    {result.stderr}")
    except Exception as e:
        print(f"  ⚠️  Erreur lors de l'import des scénarios: {e}")
    
    # Injection des patients, dossiers, venues, mouvements de test réalistes
    print("\n[6/6] Injection des patients, dossiers, venues, mouvements de test...")
    try:
        cmd = [sys.executable, "tools/init_demo_movements.py"]
        if args.export_fhir:
            cmd.append("--export-fhir")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=parent_dir
        )
        if result.returncode == 0:
            print("  ✓ Jeu de données réaliste injecté (patients, dossiers, venues, mouvements IHE PAM)")
            # Afficher les 3 dernières lignes du résultat
            lines = result.stdout.strip().split('\n')
            for line in lines[-3:]:
                print(f"    {line}")
        else:
            print(f"  ⚠️  Erreur lors de l'injection des patients/mouvements")
            print(f"    {result.stderr}")
    except Exception as e:
        print(f"  ⚠️  Erreur lors de l'injection des patients/mouvements: {e}")

    # Récupérer les infos du GHT dans une nouvelle session pour l'affichage
    with Session(engine) as display_session:
        ght_display = display_session.exec(
            select(GHTContext).where(GHTContext.id == ght_id)
        ).first()
        
    # Étape standard: Seeding multi-venue + patient multi-dossiers (jeu de démo enrichi)
    print("\n[7/7] Ajout de jeux de données multi-venues et multi-dossiers (A01+A03 par venue)...")
    with Session(engine) as session:
        try:
            _seed_multi_venue_chemo(session)
            print("  ✓ Dossier HDJ Onco multi-venues ajouté")
        except Exception as e:
            print(f"  ⚠️  Erreur seeding chemo multi-venues: {e}")
        try:
            _seed_multi_venue_psy(session)
            print("  ✓ Dossier HDJ Psy multi-venues ajouté")
        except Exception as e:
            print(f"  ⚠️  Erreur seeding psy multi-venues: {e}")
        try:
            _seed_patient_multiple_dossiers(session)
            print("  ✓ Patient avec multiples dossiers/venues ajouté")
        except Exception as e:
            print(f"  ⚠️  Erreur seeding patient multi-dossiers: {e}")

        if ght_display:
            print("\n" + "="*70)
            print("✓ INITIALISATION TERMINÉE AVEC SUCCÈS")
            print("="*70)
            print(f"\nGHT configuré: {ght_display.name}")
            print(f"  • ID: {ght_display.id}")
            print(f"  • Code: {ght_display.code}")
            print(f"  • OID racine: {ght_display.oid_racine or 'Non défini'}")
            print(f"  • URL FHIR: {ght_display.fhir_server_url or 'Non défini'}")
            print(f"\nVous pouvez maintenant démarrer l'application:")
            print(f"  .venv/bin/python -m uvicorn app.app:app --reload")
            print()

if __name__ == "__main__":
    main()
