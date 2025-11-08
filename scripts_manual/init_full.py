#!/usr/bin/env python3
"""Initialisation complète de l'environnement local.

Étapes:
1. (Optionnel) --force-reset : supprime le fichier poc.db s'il existe
2. Création des tables via SQLModel (idempotent)
3. Application des migrations legacy (006, 007) si non présentes
4. (Optionnel) --with-vocab : initialise les vocabulaires (tools/init_vocabularies.py)
5. Seed de données: minimal par défaut (Patient+Dossier+Venue+Mouvement) ou riche avec --rich-seed

Flags:
    --force-reset   : recrée totalement la base
    --with-vocab    : lance l'initialisation des vocabulaires
    --rich-seed     : insère plusieurs patients/dossiers/venues/mouvements

Usage:
        python scripts_manual/init_full.py                         # init simple
        python scripts_manual/init_full.py --with-vocab            # init + vocabulaires
        python scripts_manual/init_full.py --rich-seed             # init + seed étendu
        python scripts_manual/init_full.py --force-reset --rich-seed --with-vocab

Le script est idempotent: le seed est ignoré s'il existe déjà des patients.
"""
from __future__ import annotations
import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.db import init_db, engine, get_next_sequence
from app.models import Patient, Dossier, Venue, Mouvement, DossierType, Sequence
from app.models_structure_fhir import GHTContext
from subprocess import CalledProcessError, run

DB_PATH = Path("poc.db")

# --- Migrations legacy (006, 007) ---
MIGRATION_CMDS = [
    ("006", "entite_juridique_id", "ALTER TABLE systemendpoint ADD COLUMN entite_juridique_id INTEGER REFERENCES entitejuridique(id);", "CREATE INDEX IF NOT EXISTS idx_systemendpoint_entite_juridique_id ON systemendpoint(entite_juridique_id);") ,
    ("007", "inbox_path", "ALTER TABLE systemendpoint ADD COLUMN inbox_path TEXT; ALTER TABLE systemendpoint ADD COLUMN outbox_path TEXT; ALTER TABLE systemendpoint ADD COLUMN archive_path TEXT; ALTER TABLE systemendpoint ADD COLUMN error_path TEXT; ALTER TABLE systemendpoint ADD COLUMN file_extensions TEXT;", None),
]


def apply_legacy_migrations():
    if not DB_PATH.exists():
        print("Base non créée encore (tables vont être créées). Migrations différées.")
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(systemendpoint)")
        cols = [r[1] for r in cursor.fetchall()]
        for code, marker_col, sql_up, sql_extra in MIGRATION_CMDS:
            if marker_col not in cols:
                print(f"→ Migration {code} en cours…")
                for stmt in sql_up.split(";"):
                    s = stmt.strip()
                    if s:
                        cursor.execute(s)
                if sql_extra:
                    for stmt in sql_extra.split(";"):
                        s = stmt.strip()
                        if s:
                            cursor.execute(s)
                print(f"✓ Migration {code} appliquée")
            else:
                print(f"✓ Migration {code} déjà appliquée")
        conn.commit()
    finally:
        conn.close()


def seed_minimal():
    with Session(engine) as session:
        patient_count = session.exec(select(Patient).limit(1)).first()
        if patient_count:
            print("Seed ignoré (données déjà présentes).")
            return
        # Séquences (optionnel) - juste pour montrer l'utilisation
        for seq_name in ["dossier", "venue", "mouvement"]:
            if not session.get(Sequence, seq_name):
                session.add(Sequence(name=seq_name, value=0))
        session.commit()

        # Patient
        patient = Patient(
            family="DURAND",
            given="Alice",
            birth_date="1985-04-12",
            gender="female",
            city="Paris",
            postal_code="75001",
            country="FR",
            identity_reliability_code="VALI",
            identity_reliability_date="2024-01-15",
            identity_reliability_source="CNI",
        )
        session.add(patient)
        session.commit()
        session.refresh(patient)

        # Dossier
        dossier = Dossier(
            dossier_seq=get_next_sequence(session, "dossier"),
            patient_id=patient.id,
            uf_responsabilite="UF-100",
            admit_time=datetime.utcnow(),
            dossier_type=DossierType.HOSPITALISE,
            reason="Admission initiale",
        )
        session.add(dossier)
        session.commit()
        session.refresh(dossier)

        # Venue
        venue = Venue(
            venue_seq=get_next_sequence(session, "venue"),
            dossier_id=dossier.id,
            uf_responsabilite="UF-100",
            start_time=datetime.utcnow(),
            code="CHIR-A",
            label="Chirurgie A",
            operational_status="active",
        )
        session.add(venue)
        session.commit()
        session.refresh(venue)

        # Mouvement
        mouvement = Mouvement(
            mouvement_seq=get_next_sequence(session, "mouvement"),
            venue_id=venue.id,
            when=datetime.utcnow(),
            location="CHIR-A/SALLE-1",
            trigger_event="A01",
            movement_type="Admission",
        )
        session.add(mouvement)
        session.commit()

        print("✓ Seed minimal inséré (Patient + Dossier + Venue + Mouvement).")


def seed_rich():
    """Seed plus riche multi-patients/multi-venues/mouvements.

    Génère:
      - 5 patients
      - Pour chaque patient: 1 dossier
      - Pour chaque dossier: 2 venues
      - Pour chaque venue: 3 mouvements (A01 admission, A02 transfert, A03 sortie virtuelle)
    """
    with Session(engine) as session:
        existing = session.exec(select(Patient).limit(1)).first()
        if existing:
            print("Seed riche ignoré (données déjà présentes).")
            return

        # Séquences initiales
        for seq_name in ["dossier", "venue", "mouvement"]:
            if not session.get(Sequence, seq_name):
                session.add(Sequence(name=seq_name, value=0))
        session.commit()

        now = datetime.utcnow()
        for i in range(1, 6):
            patient = Patient(
                family=f"PATIENT-{i}",
                given="Test",
                birth_date="1990-01-01",
                gender="female" if i % 2 == 0 else "male",
                city="Paris",
                postal_code="7500" + str(i),
                country="FR",
                identity_reliability_code="VALI",
                identity_reliability_date="2024-01-15",
                identity_reliability_source="CNI",
            )
            session.add(patient)
            session.commit()
            session.refresh(patient)

            dossier = Dossier(
                dossier_seq=i,
                patient_id=patient.id,
                uf_responsabilite=f"UF-{100+i}",
                admit_time=now,
                dossier_type=DossierType.HOSPITALISE,
                reason="Admission automatique seed riche",
            )
            session.add(dossier)
            session.commit()
            session.refresh(dossier)

            for v in range(1, 3):
                venue = Venue(
                    venue_seq=(i - 1) * 2 + v,
                    dossier_id=dossier.id,
                    uf_responsabilite=dossier.uf_responsabilite,
                    start_time=now,
                    code=f"LOC-{i}-{v}",
                    label=f"Location {i}-{v}",
                    operational_status="active",
                )
                session.add(venue)
                session.commit()
                session.refresh(venue)

                # Mouvements
                mouvements_specs = [
                    ("Admission", "A01"),
                    ("Transfert", "A02"),
                    ("Sortie", "A03"),
                ]
                for m_idx, (mt_label, trigger) in enumerate(mouvements_specs, start=1):
                    mouvement = Mouvement(
                        mouvement_seq=((i - 1) * 6) + ((v - 1) * 3) + m_idx,
                        venue_id=venue.id,
                        when=now,
                        location=venue.code + f"/SALLE-{m_idx}",
                        trigger_event=trigger,
                        movement_type=mt_label,
                    )
                    session.add(mouvement)
                session.commit()

        print("✓ Seed riche inséré (5 patients / 5 dossiers / 10 venues / 30 mouvements).")


def seed_demo_scenarios():
    """Scénarios complexes de mouvements pour un GHT DEMO.

    Crée un GHT 'GHT DEMO' si absent puis insère 3 patients avec des séquences
    de mouvements illustrant des cas métier: transferts multiples, annulation,
    transferts multiples, annulation (A11) et sortie (A03) sans utiliser A08 (non supporté PAM FR).
    """
    from sqlmodel import select
    with Session(engine) as session:
        # GHT DEMO
        ght = session.exec(select(GHTContext).where(GHTContext.code == "GHT-DEMO")).first()
        if not ght:
            ght = GHTContext(name="GHT DEMO", code="GHT-DEMO", description="Contexte de démonstration")
            session.add(ght)
            session.commit()
            session.refresh(ght)
            print("✓ GHT DEMO créé")
        else:
            print("✓ GHT DEMO déjà présent")

        # Ne pas dupliquer les patients si déjà scénarisés
        existing_demo = session.exec(select(Patient).where(Patient.family.like("SCENARIO-%")).limit(1)).first()
        if existing_demo:
            print("Scénarios DEMO ignorés (déjà présents).")
            return

        # Assurer les séquences
        for seq_name in ["dossier", "venue", "mouvement"]:
            if not session.get(Sequence, seq_name):
                session.add(Sequence(name=seq_name, value=0))
        session.commit()

        from app.db import get_next_sequence
        now = datetime.utcnow()

        scenario_defs = [
            {
                "patient_family": "SCENARIO-TRANSFERTS",
                "flows": [
                    ("Admission", "A01"),
                    ("Transfert", "A02"),
                    ("Transfert", "A02"),
                    ("Sortie", "A03"),
                ],
            },
            {
                "patient_family": "SCENARIO-ANNULATION",
                "flows": [
                    ("Admission", "A01"),
                    ("Annulation admission", "A11"),
                    ("Nouvelle admission", "A01"),
                    ("Transfert", "A02"),
                    ("Sortie", "A03"),
                ],
            },
            {
                "patient_family": "SCENARIO-TRANSFERT-MULTI",
                "flows": [
                    ("Admission", "A01"),
                    ("Transfert", "A02"),
                    ("Transfert secondaire", "A02"),
                    ("Transfert tertiaire", "A02"),
                    ("Sortie", "A03"),
                ],
            },
        ]

        for scen_idx, scen in enumerate(scenario_defs, start=1):
            patient = Patient(
                family=scen["patient_family"],
                given="Demo",
                birth_date="1980-01-01",
                gender="other",
                city="DemoVille",
                postal_code="00000",
                country="FR",
                identity_reliability_code="VALI",
                identity_reliability_date="2024-01-15",
                identity_reliability_source="CNI",
            )
            session.add(patient)
            session.commit()
            session.refresh(patient)

            dossier_seq = get_next_sequence(session, "dossier")
            dossier = Dossier(
                dossier_seq=dossier_seq,
                patient_id=patient.id,
                uf_responsabilite=f"UF-DEMO-{scen_idx}",
                admit_time=now,
                dossier_type=DossierType.HOSPITALISE,
                reason="Scenario démo",
            )
            session.add(dossier)
            session.commit()
            session.refresh(dossier)

            # Créer 2 venues pour permettre transferts
            venues = []
            for v_num in [1, 2]:
                venue_seq = get_next_sequence(session, "venue")
                venue = Venue(
                    venue_seq=venue_seq,
                    dossier_id=dossier.id,
                    uf_responsabilite=dossier.uf_responsabilite,
                    start_time=now,
                    code=f"DEMO-{scen_idx}-{v_num}",
                    label=f"Unité Démo {scen_idx}-{v_num}",
                    operational_status="active",
                )
                session.add(venue)
                session.commit()
                session.refresh(venue)
                venues.append(venue)

            current_venue_index = 0
            for flow_idx, (movement_type, trigger) in enumerate(scen["flows"], start=1):
                # Changer de venue sur A02 (transfert)
                if trigger == "A02":
                    current_venue_index = 1 - current_venue_index  # toggle between 0 and 1
                venue = venues[current_venue_index]
                mouvement_seq = get_next_sequence(session, "mouvement")
                mouvement = Mouvement(
                    mouvement_seq=mouvement_seq,
                    venue_id=venue.id,
                    when=now,
                    location=f"{venue.code}/BOX-{flow_idx}",
                    trigger_event=trigger,
                    movement_type=movement_type,
                )
                session.add(mouvement)
                session.commit()

        print("✓ Scénarios complexes DEMO insérés (3 patients scénarisés).")


def main():
    parser = argparse.ArgumentParser(description="Initialisation complète locale")
    parser.add_argument("--force-reset", action="store_true", help="Supprime poc.db avant recréation")
    parser.add_argument("--with-vocab", action="store_true", help="Initialise les vocabulaires")
    parser.add_argument("--rich-seed", action="store_true", help="Insère un jeu de données plus riche (multi) au lieu du seed minimal")
    parser.add_argument("--demo-scenarios", action="store_true", help="Insère scénarios complexes de mouvements liés à un GHT DEMO")
    args = parser.parse_args()

    if args.force_reset and DB_PATH.exists():
        print("→ Suppression ancienne base poc.db")
        DB_PATH.unlink()

    print("→ Création des tables (idempotent)…")
    init_db()

    print("→ Application migrations legacy…")
    apply_legacy_migrations()

    if args.rich_seed:
        print("→ Seed riche…")
        seed_rich()
    else:
        print("→ Seed minimal…")
        seed_minimal()

    if args.demo_scenarios:
        print("→ Scénarios complexes GHT DEMO…")
        seed_demo_scenarios()

    if args.with_vocab:
        print("→ Initialisation des vocabulaires…")
        try:
            import sys
            # Utiliser l'interpréteur courant pour éviter FileNotFoundError (python peut ne pas être dans PATH)
            result = run([sys.executable, "tools/init_vocabularies.py"], check=True)
            print("✓ Vocabulaires initialisés")
        except CalledProcessError as e:
            print(f"✗ Échec init vocabulaires: retour code {e.returncode}")
        except FileNotFoundError as e:
            print(f"✗ Interpréteur introuvable pour init vocab: {e}")

    print("\n✅ Initialisation complète terminée.")

if __name__ == "__main__":
    main()
