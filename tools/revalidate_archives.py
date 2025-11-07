#!/usr/bin/env python3
"""
Revalide les enchaînements (workflow IHE PAM) des messages ADT archivés
(dans MessageLog) avec les nouvelles règles en vigueur.

- Regroupe les messages par identifiant de venue (PV1-19) si présent,
  sinon par numéro de dossier (PID-18), sinon par identifiant patient (PID-3.1).
- Trie les messages par EVN-2 puis MSH-7 puis created_at
- Valide chaque groupe comme un scénario via app.services.scenario_validation.validate_scenario
- Génère un rapport synthétique sur la sortie standard et dans tools/revalidation_report.json

Exécution:
  .venv/bin/python3 tools/revalidate_archives.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

from sqlmodel import Session, select

from app.models_shared import MessageLog
from app.db import engine
from app.services.scenario_validation import validate_scenario
from app.services.mllp import parse_msh_fields
from app.services.transport_inbound import _parse_pid, _parse_pv1  # reuse tolerant parsers


def _extract_event_code(msg: str) -> str | None:
    lines = msg.split("\n")
    for line in lines:
        if line.startswith("MSH"):
            fields = line.split("|")
            if len(fields) > 9 and fields[8]:
                comps = fields[8].split("^")
                if len(comps) > 1:
                    return comps[1].strip()
        if line.startswith("EVN"):
            parts = line.split("|")
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
    return None


def _extract_ts(msg: str) -> datetime | None:
    # Prefer EVN-2, fallback to MSH-7; return datetime if parsable
    evn_ts = None
    msh_ts = None
    for line in msg.split("\n"):
        if line.startswith("EVN"):
            parts = line.split("|")
            if len(parts) > 2 and parts[2]:
                evn_ts = parts[2].strip()
                break
    try:
        if evn_ts:
            # keep only digits and try YYYYMMDDHHMMSS
            s = ''.join([c for c in evn_ts if c.isdigit()])
            for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d"):
                try:
                    return datetime.strptime(s[:len(fmt.replace('%',''))], fmt)
                except Exception:
                    continue
    except Exception:
        pass
    try:
        msh = parse_msh_fields(msg)
        msh_ts = msh.get("datetime") if msh else None
        if msh_ts:
            s = ''.join([c for c in msh_ts if c.isdigit()])
            for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d"):
                try:
                    return datetime.strptime(s[:len(fmt.replace('%',''))], fmt)
                except Exception:
                    continue
    except Exception:
        pass
    return None


def build_groups(session: Session) -> Dict[str, List[Tuple[datetime, int, str]]]:
    """Retourne un dict group_key -> [(sort_dt, log_id, message), ...]."""
    groups: Dict[str, List[Tuple[datetime, int, str]]] = defaultdict(list)
    logs = session.exec(
        select(MessageLog)
        .where(MessageLog.direction == "in")
        .where(MessageLog.kind == "MLLP")
        .where(MessageLog.message_type.like("ADT%"))
        .order_by(MessageLog.created_at.asc())
    ).all()

    for log in logs:
        msg = log.payload
        pid = _parse_pid(msg)
        pv1 = _parse_pv1(msg)
        # Group key preference: PV1-19, then PID-18, then PID-3.1
        key = None
        if pv1.get("visit_number"):
            key = f"VISIT:{pv1['visit_number'].split('^')[0]}"
        elif pid.get("account_number"):
            key = f"DOSSIER:{pid['account_number'].split('^')[0]}"
        elif pid.get("identifiers"):
            try:
                first_cx = pid["identifiers"][0][0]
                key = f"PAT:{first_cx.split('^')[0]}"
            except Exception:
                key = f"LOG:{log.id}"
        else:
            key = f"LOG:{log.id}"

        sort_dt = _extract_ts(msg) or log.created_at
        groups[key].append((sort_dt, log.id, msg))

    # sort each group chronologically
    for k, arr in groups.items():
        arr.sort(key=lambda t: (t[0], t[1]))

    return groups


def main() -> int:
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "groups": [],
        "summary": {"total_groups": 0, "valid": 0, "invalid": 0},
    }
    with Session(engine) as session:
        groups = build_groups(session)
        report["summary"]["total_groups"] = len(groups)
        for key, items in groups.items():
            messages_text = "\n".join(m for _, __, m in items)
            res = validate_scenario(messages_text, direction="inbound", profile="IHE_PAM_FR")
            report_group = {
                "group": key,
                "count": len(items),
                "is_valid": res.is_valid,
                "level": res.level,
                "workflow_issues": [
                    {"code": i.code, "message": i.message, "severity": i.severity}
                    for i in res.workflow_issues
                ],
                "coherence_issues": [
                    {"code": i.code, "message": i.message, "severity": i.severity}
                    for i in res.coherence_issues
                ],
            }
            if res.is_valid:
                report["summary"]["valid"] += 1
            else:
                report["summary"]["invalid"] += 1
            report["groups"].append(report_group)

    # Save JSON report
    out_path = "tools/revalidation_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Print a concise summary
    print("Revalidation des enchaînements - Rapport")
    print(f"Groupes: {report['summary']['total_groups']} | Valides: {report['summary']['valid']} | Invalides: {report['summary']['invalid']}")
    for g in report["groups"]:
        if not g["is_valid"]:
            print(f"- {g['group']} ({g['count']} msgs): niveau={g['level']} | workflow_issues={len(g['workflow_issues'])} | coherence_issues={len(g['coherence_issues'])}")
            for iss in g["workflow_issues"][:3]:
                print(f"    * [{iss['severity']}] {iss['code']}: {iss['message']}")
    print(f"\nRapport détaillé écrit dans {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
