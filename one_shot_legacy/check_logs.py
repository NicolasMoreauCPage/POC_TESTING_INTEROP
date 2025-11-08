"""Vérifier les derniers logs"""
from sqlmodel import Session, select
from app.db import engine
from app.models_endpoints import MessageLog

with Session(engine) as s:
    logs = list(s.exec(select(MessageLog).order_by(MessageLog.id.desc()).limit(5)).all())
    
    print(f"=== Derniers {len(logs)} logs ===\n")
    for log in logs:
        print(f"Log {log.id}:")
        print(f"  Type: {log.message_type}")
        print(f"  Status: {log.status}")
        print(f"  Direction: {log.direction}")
        if log.ack_payload:
            print(f"  ACK: {log.ack_payload[:300]}")
        print()
