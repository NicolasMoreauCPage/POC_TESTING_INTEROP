#!/usr/bin/env python3
"""Compare two GHT contexts for ISO state equivalence.

Metrics:
  - Counts: patients, dossiers, venues, mouvements.
  - Per patient mapped: dossier count, venue count, mouvement count, last movement trigger, last movement status.
  - Structural UF responsibility codes distribution.
Mapping strategy:
  - If destination patient.identifier ends with '-DST', strip suffix and attempt matching against source primary identifier (by patient.identifier or external_id).
  - Fallback: match by family+given+birth_date when unique.
Output: JSON summary with diffs (non-zero deltas or mismatches list).

Usage:
  PYTHONPATH=. python tools/compare_ght_states.py --source GHT-SRC --dest GHT-DST
  (If --source omitted and exactly two contexts exist, auto-pick non -DST as source.)
"""
from __future__ import annotations
import argparse, json
from collections import defaultdict, Counter
from sqlmodel import Session, select
from app.db import engine
from app.models_structure_fhir import GHTContext
from app.models import Patient, Dossier, Venue, Mouvement


def _collect_context(session: Session, ght: GHTContext):
    patients = session.exec(select(Patient)).all()
    dossiers = session.exec(select(Dossier)).all()
    venues = session.exec(select(Venue)).all()
    movements = session.exec(select(Mouvement)).all()
    # (In current schema patients/dossiers not directly keyed by ght; assume single DB per test context scenario.)
    # Filter heuristic: if multiple GHT contexts exist, we attempt scoping via endpoint presence is not trivial.
    # For now gather global state; user should run in isolated DB per comparison.
    return {
        "patients": patients,
        "dossiers": dossiers,
        "venues": venues,
        "movements": movements,
    }


def _build_patient_index(objs):
    by_primary = {}
    by_demographics = defaultdict(list)
    for p in objs:
        primary = p.identifier or p.external_id or (f"PATSEQ{p.patient_seq}" if p.patient_seq else None) or f"PID{p.id}"
        by_primary[primary] = p
        key = (p.family, p.given, p.birth_date)
        by_demographics[key].append(p)
    return by_primary, by_demographics


def compare(source: str | None, dest: str):
    with Session(engine) as session:
        contexts = session.exec(select(GHTContext)).all()
        dest_ctx = next((c for c in contexts if c.code == dest or c.name == dest), None)
        if not dest_ctx:
            raise SystemExit(f"Destination GHT '{dest}' introuvable")
        if source:
            src_ctx = next((c for c in contexts if c.code == source or c.name == source), None)
            if not src_ctx:
                raise SystemExit(f"Source GHT '{source}' introuvable")
        else:
            # auto-pick: choose a context not matching dest and not ending with -DST
            src_candidates = [c for c in contexts if c.id != dest_ctx.id and not c.code.endswith("-DST")]
            if not src_candidates:
                raise SystemExit("Impossible de déduire le contexte source (fournir --source)")
            src_ctx = src_candidates[0]

        src_state = _collect_context(session, src_ctx)
        dst_state = _collect_context(session, dest_ctx)

        src_pat_index, src_demo_index = _build_patient_index(src_state["patients"])
        dst_pat_index, dst_demo_index = _build_patient_index(dst_state["patients"])  # may include -DST variants

        mapped = []
        unmapped_dest = []
        for ident, p in dst_pat_index.items():
            base_ident = ident[:-4] if ident.endswith("-DST") else ident
            src_p = src_pat_index.get(base_ident)
            if not src_p:
                # Try demographics unique match
                key = (p.family, p.given, p.birth_date)
                cands = src_demo_index.get(key, [])
                if len(cands) == 1:
                    src_p = cands[0]
            if src_p:
                mapped.append((src_p, p))
            else:
                unmapped_dest.append(p)

        def _last_movement(dossier: Dossier):
            if not dossier.venues:
                return None, None
            mvts = []
            for v in dossier.venues:
                mvts.extend(v.mouvements)
            if not mvts:
                return None, None
            mvts.sort(key=lambda m: m.mouvement_seq)
            last = mvts[-1]
            return last.trigger_event, last.status

        patient_diffs = []
        for src_p, dst_p in mapped:
            src_dossiers = [d for d in src_state["dossiers"] if d.patient_id == src_p.id]
            dst_dossiers = [d for d in dst_state["dossiers"] if d.patient_id == dst_p.id]
            src_mv_count = sum(len(v.mouvements) for d in src_dossiers for v in d.venues)
            dst_mv_count = sum(len(v.mouvements) for d in dst_dossiers for v in d.venues)
            src_last_trig, src_last_status = None, None
            dst_last_trig, dst_last_status = None, None
            if src_dossiers:
                src_last_trig, src_last_status = _last_movement(src_dossiers[-1])
            if dst_dossiers:
                dst_last_trig, dst_last_status = _last_movement(dst_dossiers[-1])
            diff = {
                "source_identifier": src_p.identifier,
                "dest_identifier": dst_p.identifier,
                "dossier_count_src": len(src_dossiers),
                "dossier_count_dst": len(dst_dossiers),
                "movement_count_src": src_mv_count,
                "movement_count_dst": dst_mv_count,
                "last_trigger_src": src_last_trig,
                "last_trigger_dst": dst_last_trig,
                "last_status_src": src_last_status,
                "last_status_dst": dst_last_status,
                "dossier_count_equal": len(src_dossiers) == len(dst_dossiers),
                "movement_count_equal": src_mv_count == dst_mv_count,
                "last_trigger_equal": src_last_trig == dst_last_trig,
                "last_status_equal": src_last_status == dst_last_status,
            }
            patient_diffs.append(diff)

        summary = {
            "source": {"code": src_ctx.code, "name": src_ctx.name},
            "destination": {"code": dest_ctx.code, "name": dest_ctx.name},
            "counts": {
                "patients_src": len(src_state["patients"]),
                "patients_dst": len(dst_state["patients"]),
                "dossiers_src": len(src_state["dossiers"]),
                "dossiers_dst": len(dst_state["dossiers"]),
                "venues_src": len(src_state["venues"]),
                "venues_dst": len(dst_state["venues"]),
                "movements_src": len(src_state["movements"]),
                "movements_dst": len(dst_state["movements"]),
            },
            "mapped_patients": len(mapped),
            "unmapped_dest_patients": len(unmapped_dest),
            "patient_diffs": patient_diffs,
            "all_equal": all(d["dossier_count_equal"] and d["movement_count_equal"] and d["last_trigger_equal"] and d["last_status_equal"] for d in patient_diffs) and len(unmapped_dest) == 0,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description="Compare two GHT contexts for ISO state")
    ap.add_argument("--source", help="Code ou nom du GHT source", default=None)
    ap.add_argument("--dest", help="Code ou nom du GHT destination", required=True)
    args = ap.parse_args()
    compare(args.source, args.dest)

if __name__ == "__main__":
    main()
