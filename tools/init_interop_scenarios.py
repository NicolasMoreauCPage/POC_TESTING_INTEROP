#!/usr/bin/env python
"""
Initialise les scénarios d'interopération (IHE PAM / HL7) à partir
des gabarits fournis dans Doc/interfaces.integration_src.

Usage:
    python tools/init_interop_scenarios.py \
        --base Doc/interfaces.integration_src/interfaces.integration/src/main/resources/data
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime

from sqlmodel import Session, SQLModel, select

from app.db import engine
import app.models  # noqa: F401
import app.models_identifiers  # noqa: F401
import app.models_structure  # noqa: F401
import app.models_structure_fhir  # noqa: F401
from app.models import Dossier, Patient, Venue
from app.models_scenarios import InteropScenario, ScenarioBinding
from app.models_structure_fhir import GHTContext
from app.services.scenario_loader import discover_hl7_files, load_hl7_files


def ensure_schema() -> None:
    SQLModel.metadata.create_all(engine)


def get_or_create_demo_ght(session: Session) -> GHTContext:
    ght = session.exec(select(GHTContext).where(GHTContext.code == "GHT-DEMO-INTEROP")).first()
    if ght:
        return ght

    ght = GHTContext(
        name="GHT Démo Interop",
        code="GHT-DEMO-INTEROP",
        description="Contexte synthétique pour les scénarios d'interopération importés.",
        is_active=True,
    )
    session.add(ght)
    session.commit()
    session.refresh(ght)
    return ght


def ensure_demo_dataset(session: Session, ght: GHTContext) -> int:
    """Crée des patients/dossiers de démonstration liés à chaque scénario importé."""
    created = 0
    scenarios = session.exec(select(InteropScenario).order_by(InteropScenario.id)).all()
    # Suppression : l'injection de patients/dossiers/venues de démonstration est désormais assurée par init_demo_movements.py
    # Cette fonction ne crée plus de données obsolètes.

    if created:
        session.commit()
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialise les scénarios d'interop dans la base de données.")
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("Doc/interfaces.integration_src/interfaces.integration/src/main/resources/data"),
        help="Répertoire racine contenant les fichiers HL7 à importer.",
    )
    parser.add_argument(
        "--pattern",
        action="append",
        help="Patron glob supplémentaire (relatif à --base). Peut être spécifié plusieurs fois.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Nombre maximum de fichiers à importer (debug).",
    )

    args = parser.parse_args()
    base_dir: Path = args.base

    if not base_dir.exists():
        print(f"[!] Le répertoire {base_dir} est introuvable.", file=sys.stderr)
        return 1

    ensure_schema()

    hl7_files = discover_hl7_files(base_dir, args.pattern)
    if args.limit:
        hl7_files = hl7_files[: args.limit]

    if not hl7_files:
        print("[!] Aucun fichier HL7 trouvé – rien à importer.")
        return 0

    with Session(engine) as session:
        ght = get_or_create_demo_ght(session)

        count = load_hl7_files(
            session,
            base_dir,
            hl7_files,
            default_category=None,
            ght_context_id=ght.id,
            tag_prefix="demo",
        )

        created_bindings = ensure_demo_dataset(session, ght)
        scenarios_total = len(session.exec(select(InteropScenario)).all())
        print(f"[+] {count} scénarios importés/mis à jour ({scenarios_total} au total).")
        print(f"[+] Contexte GHT utilisé : {ght.name} (id={ght.id}).")
        if created_bindings:
            print(f"[+] {created_bindings} patients/dossiers de démonstration créés.")
        else:
            print("[=] Aucun nouveau dossier de démonstration (toutes les associations existaient déjà).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
