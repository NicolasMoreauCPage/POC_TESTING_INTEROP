#!/usr/bin/env python3
"""Génère une structure hospitalière de démonstration pour un contexte GHT."""

from __future__ import annotations

import argparse
from typing import Optional

from sqlmodel import Session, SQLModel, select

from app.db import engine
from app.models_structure_fhir import GHTContext
from app.services.structure_seed import DEMO_STRUCTURE, ensure_demo_structure


def _ensure_context(session: Session, *, context_id: Optional[int], context_code: str) -> GHTContext:
    if context_id is not None:
        context = session.get(GHTContext, context_id)
        if not context:
            raise SystemExit(f"[!] Aucun contexte GHT avec l'identifiant {context_id}.")
        return context

    context = session.exec(select(GHTContext).where(GHTContext.code == context_code)).first()
    if context:
        return context

    context = GHTContext(
        name="GHT Démo Interop",
        code=context_code,
        description="Contexte généré automatiquement pour les tests de structure.",
        is_active=True,
    )
    session.add(context)
    session.commit()
    session.refresh(context)
    print(f"[+] Contexte GHT créé (id={context.id}, code={context.code}).")
    return context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--context-id",
        type=int,
        default=None,
        help="Identifiant numérique du contexte GHT à alimenter.",
    )
    parser.add_argument(
        "--context-code",
        type=str,
        default="GHT-DEMO-INTEROP",
        help="Code du contexte GHT à créer/mettre à jour si --context-id n'est pas fourni.",
    )
    args = parser.parse_args()

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        context = _ensure_context(session, context_id=args.context_id, context_code=args.context_code)
        stats = ensure_demo_structure(session, context, DEMO_STRUCTURE)

    def _format(counter) -> str:
        return ", ".join(f"{name}:{count}" for name, count in counter.items() if count) or "0"

    print("[+] Structure de démonstration générée.")
    print(f"    Créations: {_format(stats['created'])}")
    print(f"    Mises à jour: {_format(stats['updated'])}")


if __name__ == "__main__":
    main()
