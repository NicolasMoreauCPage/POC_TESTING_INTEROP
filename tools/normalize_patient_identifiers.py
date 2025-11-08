#!/usr/bin/env python3
"""Normalize patient identifiers.

Assign missing patient_seq using application sequence 'patient'.
Populate identifier and external_id for patients lacking them using a stable deterministic pattern:
  PAT{patient_seq:08d} if patient_seq present after assignment else PATID{id:08d}
Mirror identifier to external_id only when external_id is null to avoid overwriting any existing external references.

Usage:
  PYTHONPATH=. python tools/normalize_patient_identifiers.py
"""
from sqlmodel import Session, select
from app.db import engine, get_next_sequence
from app.models import Patient


def normalize():
    updated = 0
    seq_assigned = 0
    with Session(engine) as session:
        patients = session.exec(select(Patient).order_by(Patient.id)).all()
        for p in patients:
            changed = False
            if p.patient_seq is None:
                p.patient_seq = get_next_sequence(session, "patient")
                seq_assigned += 1
                changed = True
            # Build proposed identifier value
            proposed = None
            if p.patient_seq is not None:
                proposed = f"PAT{p.patient_seq:08d}"
            else:
                proposed = f"PATID{p.id:08d}"
            if p.identifier is None:
                p.identifier = proposed
                changed = True
            if p.external_id is None:
                # Mirror identifier only if external_id empty
                p.external_id = p.identifier
                changed = True
            if changed:
                session.add(p)
                updated += 1
        session.commit()
    print(f"Patients processed={len(patients)} updated={updated} seq_assigned={seq_assigned}")


if __name__ == "__main__":
    normalize()
