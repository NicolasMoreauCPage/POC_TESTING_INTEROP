# app/services/transport_inbound.py
from datetime import datetime
from app.models_endpoints import MessageLog
from app.services.mllp import parse_msh_fields, build_ack

async def on_message_inbound(msg: str, session, endpoint) -> str:
    """
    Reçoit un message HL7 v2 (déjà défrémé), journalise et retourne un ACK.
    - msg: message HL7 v2 brut (texte)
    - session: Session SQLModel (context manager fourni par session_factory)
    - endpoint: SystemEndpoint
    """
    try:
        f = parse_msh_fields(msg)
        ctrl_id = f.get("control_id", "")
        # Validation minimale : on exige un MSH valide avec control_id
        if not f.get("msg_type"):
            ack_code, text = "AE", "Missing/invalid MSH-9"
        else:
            ack_code, text = ("AA", "Message received") if ctrl_id else ("AE", "Missing MSH-10")

        ack = build_ack(msg, ack_code=ack_code, text=text)

        log = MessageLog(
            direction="in",
            kind="MLLP",
            endpoint_id=endpoint.id,
            correlation_id=ctrl_id or "",
            status="ack_ok" if ack_code == "AA" else "ack_error",
            payload=msg,
            ack_payload=ack,
            created_at=datetime.utcnow(),
        )
        session.add(log)
        session.commit()
        return ack

    except Exception as e:
        # En cas de pépin, tente un ACK AE générique en dernier recours
        ack = build_ack("MSH|^~\\&||||||||||P|2.5", ack_code="AE", text=str(e)[:80])
        try:
            log = MessageLog(
                direction="in", kind="MLLP", endpoint_id=endpoint.id,
                correlation_id="", status="ack_error",
                payload=msg, ack_payload=ack, created_at=datetime.utcnow()
            )
            session.add(log); session.commit()
        except Exception:
            pass
        return ack
