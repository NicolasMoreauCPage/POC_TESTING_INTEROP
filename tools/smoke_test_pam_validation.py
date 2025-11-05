import asyncio
import os
import json
from sqlmodel import Session, select

os.environ.setdefault("TESTING", "1")

from app.db_session_factory import session_factory
from app.models_shared import MessageLog, SystemEndpoint
from app.services.transport_inbound import on_message_inbound_async

# Test 1: A04 sans PV1 (PV1 requis pour A04 selon HAPI)
hl7_a04_no_pv1 = (
    "MSH|^~\\&|TEST|HOSP|POC|HOSP|20250101000000||ADT^A04|CTRL-1|P|2.5\r"
    "EVN|A04|20250101000000\r"
    "PID|1||12345^^^HOSP^PI||Doe^John||19800101|M\r"
)

# Test 2: A01 complet avec segments optionnels
hl7_a01_full = (
    "MSH|^~\\&|TEST|HOSP|POC|HOSP|20250101000000||ADT^A01|CTRL-2|P|2.5\r"
    "EVN|A01|20250101000000\r"
    "PID|1||12345^^^HOSP^PI||Doe^John||19800101|M|||123 Main St^^Paris^^75001^FRA^H\r"
    "PV1|1|I|ROOM1^BED1^FLOOR3||||||||||||||12345\r"
    "PV2||Commentaire patient\r"
    "ZBE|1|DATA\r"
)

# Test 3: A28 (identité) sans PV1 (PV1 optionnel pour A28)
hl7_a28 = (
    "MSH|^~\\&|TEST|HOSP|POC|HOSP|20250101000000||ADT^A28|CTRL-3|P|2.5\r"
    "EVN|A28|20250101000000\r"
    "PID|1||12345^^^HOSP^PI||Doe^Jane||19900101|F\r"
)

# Test 4: Message avec violations HL7 v2.5 base
hl7_bad_hl7 = (
    "MSH|^~\\&|TEST|HOSP|POC|HOSP|20250101000000||ADT^A01|CTRL-4|X|\r"  # MSH-11 invalide (X au lieu de P/D/T)
    "EVN|A99|20250101000000\r"  # EVN-1 != MSH-9 trigger (A99 vs A01)
    "PID|1||||Doe^John||19800101ABC|M\r"  # PID-3 vide, PID-5 absent, PID-7 format invalide
    "PV1|1|I|ROOM1\r"
)

tests = [
    ("A04 sans PV1", hl7_a04_no_pv1),
    ("A01 complet", hl7_a01_full),
    ("A28 identité", hl7_a28),
    ("HL7 v2.5 violations", hl7_bad_hl7),
]

with session_factory() as s:
    ep = s.exec(select(SystemEndpoint).where(SystemEndpoint.role.in_(["receiver","both"])) ).first()
    
    for name, hl7 in tests:
        print(f"\n=== Test: {name} ===")
        ack = asyncio.run(on_message_inbound_async(hl7, s, ep))
        s.commit()
        
        m = s.exec(select(MessageLog).order_by(MessageLog.id.desc())).first()
        print(f"Status: {m.status}, PAM: {m.pam_validation_status}")
        if m.pam_validation_issues:
            issues = json.loads(m.pam_validation_issues)
            print(f"  Issues count: {len(issues)}")
            for issue in issues:
                print(f"  [{issue['severity']}] {issue['code']}: {issue['message']}")
        else:
            print("  No validation issues recorded")
        print(f"ACK excerpt: {ack[:100].replace(chr(13), '|')}")
