from sqlmodel import Session, select
from app.db import engine
from app.models_shared import MessageLog
import sys

needle = sys.argv[1] if len(sys.argv) > 1 else "1117924663"

with Session(engine) as s:
    rows = s.exec(
        select(MessageLog).where(
            (MessageLog.correlation_id == needle) | (MessageLog.payload.contains(needle))
        ).order_by(MessageLog.id.desc())
    ).all()

print(f"Found {len(rows)} messages matching {needle}\n")
for m in rows:
    print(f"id={m.id} type={m.message_type} status={m.status} kind={m.kind} direction={m.direction}")
    print(f"endpoint_id={m.endpoint_id} corr={m.correlation_id}")
    print("--- payload head ---")
    print((m.payload or '')[:500])
    print("--- ack head ---")
    print((m.ack_payload or '')[:1000])
    print("\n====\n")
