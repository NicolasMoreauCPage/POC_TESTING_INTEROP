#!/usr/bin/env python3
"""Export outbound PAM (ADT) messages for all dossiers/venues/mouvements.

Usage:
  PYTHONPATH=. python tools/export_pam_outbound.py --out pam_export --limit 100

It will generate HL7 messages using existing pam.generate_pam_messages_for_dossier
and write them to numbered .hl7 files suitable for re-import tests.
"""
import argparse, os
from pathlib import Path
from sqlmodel import Session, select
from app.db import engine
from app.models import Dossier
from app.services.pam import generate_pam_messages_for_dossier

def export(out_dir: Path, limit: int | None):
    out_dir.mkdir(parents=True, exist_ok=True)
    with Session(engine) as session:
        dossiers = session.exec(select(Dossier).order_by(Dossier.id)).all()
        if limit:
            dossiers = dossiers[:limit]
        count = 0
        for dos in dossiers:
            msgs = generate_pam_messages_for_dossier(dos)
            for m in msgs:
                count += 1
                fname = out_dir / f"ADT_{count:05d}.hl7"
                fname.write_text(m, encoding="utf-8")
        print(f"Exporté {count} messages ADT vers {out_dir}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='pam_export', help='Répertoire de sortie')
    ap.add_argument('--limit', type=int, default=None, help='Limiter le nombre de dossiers traités')
    args = ap.parse_args()
    export(Path(args.out), args.limit)

if __name__ == '__main__':
    main()
