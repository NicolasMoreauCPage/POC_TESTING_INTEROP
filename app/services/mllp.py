import asyncio
import logging
import os
from typing import Callable, Awaitable
from datetime import datetime
from sqlmodel import Session
from app.models_endpoints import SystemEndpoint

logger = logging.getLogger("mllp")
TRACE = os.getenv("MLLP_TRACE", "0") in ("1", "true", "True")

START_BLOCK = b"\x0b"  # VT
END_BLOCK = b"\x1c"    # FS
CARRIAGE_RETURN = b"\x0d"


def frame_hl7(message: str) -> bytes:
    return START_BLOCK + message.encode("utf-8") + END_BLOCK + CARRIAGE_RETURN

def deframe_hl7(stream: bytes) -> list[str]:
    msgs = []
    buf = memoryview(stream)
    while True:
        start = bytes(buf).find(START_BLOCK)
        if start < 0:
            break
        end = bytes(buf).find(END_BLOCK, start + 1)
        if end < 0:
            break
        payload = bytes(buf)[start + 1 : end]
        msg = payload.decode("utf-8", errors="replace")
        cr = bytes(buf).find(CARRIAGE_RETURN, end + 1)
        buf = buf[cr + 1:] if cr >= 0 else buf[end + 1:]
        msgs.append(msg)
    return msgs

def parse_msh_fields(message: str) -> dict:
    lines = message.split("\r")
    msh = next((l for l in lines if l.startswith("MSH")), "MSH|^~\\&|||||||||||||")
    parts = msh.split("|")
    enc = parts[1] if len(parts) > 1 and parts[1] else "^~\\&"
    msg_type = parts[8] if len(parts) > 8 else ""
    comp = msg_type.split("^")
    trigger = comp[1] if len(comp) >= 2 else ""
    return {
        "enc": enc,
        "sending_app": parts[2] if len(parts) > 2 else "",
        "sending_facility": parts[3] if len(parts) > 3 else "",
        "receiving_app": parts[4] if len(parts) > 4 else "",
        "receiving_facility": parts[5] if len(parts) > 5 else "",
        "datetime": parts[6] if len(parts) > 6 else "",
        "msg_type": msg_type,
        "trigger": trigger,
        "control_id": parts[9] if len(parts) > 9 else "",
        "processing_id": parts[10] if len(parts) > 10 else "P",
        "version": parts[11] if len(parts) > 11 else "2.5",
    }

def build_ack(original: str, ack_code: str = "AA", text: str = "") -> str:
    f = parse_msh_fields(original)
    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    msh9 = f"ACK^{f['trigger']}" if f["trigger"] else "ACK"
    msh = (
        "MSH|{enc}|{send_app}|{send_fac}|{recv_app}|{recv_fac}|{ts}||{msh9}|ACK{ts}|{proc}|{ver}"
        .format(
            enc=f["enc"],
            send_app=f["receiving_app"],
            send_fac=f["receiving_facility"],
            recv_app=f["sending_app"],
            recv_fac=f["sending_facility"],
            ts=now,
            msh9=msh9,
            proc=f["processing_id"],
            ver=f["version"],
        )
    )
    msa = f"MSA|{ack_code}|{f['control_id']}|{text or ''}"
    segs = [msh, msa]
    if ack_code in ("AE", "AR"):
        segs.append(f"ERR|||207^{text or 'Application error'}^HL70357|E")
    return "\r".join(segs) + "\r"

def _hexdump(b: bytes, width: int = 16) -> str:
    lines = []
    for i in range(0, len(b), width):
        chunk = b[i:i+width]
        hexs = " ".join(f"{x:02x}" for x in chunk)
        text = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        lines.append(f"{i:04x}  {hexs:<{width*3}}  {text}")
    return "\n".join(lines)

async def start_mllp_server(
    host: str, port: int,
    on_message: Callable[[str, Session, SystemEndpoint], Awaitable[str]],
    endpoint: SystemEndpoint,
    session_factory: Callable[[], Session]
):
    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info("peername")
        logger.info(f"[MLLP] Connect {peer} -> {host}:{port} ({endpoint.name})")
        try:
            data = await reader.read(65536)
            logger.info(f"[MLLP] RX {len(data)} bytes from {peer} on {host}:{port}")
            if TRACE:
                logger.debug("[MLLP] RX HEX:\n" + _hexdump(data))

            messages = deframe_hl7(data)
            if not messages:
                # Rien de framé MLLP → renvoyer un AE générique pour tracer la liaison
                logger.warning(f"[MLLP] No MLLP frame from {peer} on {host}:{port}")
                ack = build_ack("MSH|^~\\&||||||||||P|2.5", "AE", "No MLLP frame")
                writer.write(frame_hl7(ack))
                await writer.drain()
            else:
                for idx, msg in enumerate(messages, 1):
                    f = parse_msh_fields(msg)
                    ctrl = f.get("control_id")
                    logger.info(f"[MLLP] Frame {idx}/{len(messages)} MSH-10={ctrl or '∅'} MSH-9={f.get('msg_type')}")
                    with session_factory() as s:
                        try:
                            ack = await on_message(msg, s, endpoint)
                            writer.write(frame_hl7(ack))
                            await writer.drain()
                            if TRACE:
                                logger.debug("[MLLP] TX ACK:\n" + ack.replace("\r", "\\r\n"))
                        except Exception as e:
                            logger.exception(f"[MLLP] Error processing frame {idx}: {e}")
                            ack = build_ack(msg, ack_code="AE", text=str(e)[:80])
                            writer.write(frame_hl7(ack))
                            await writer.drain()
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.info(f"[MLLP] Disconnect {peer} from {host}:{port}")

    try:
        server = await asyncio.start_server(handle, host=host, port=port)
        sockname = server.sockets[0].getsockname() if server.sockets else (host, port)
        logger.info(f"✅ MLLP {endpoint.name} listening on {sockname[0]}:{sockname[1]}")
        return server
    except OSError as e:
        logger.error(f"❌ Cannot bind MLLP {endpoint.name} on {host}:{port} — {e}")
        raise

async def send_mllp(host: str, port: int, message: str, timeout: float = 10.0) -> str:
    reader, writer = await asyncio.open_connection(host, port)
    writer.write(frame_hl7(message))
    await writer.drain()
    data = await asyncio.wait_for(reader.read(65536), timeout=timeout)
    writer.close()


async def stop_mllp_server(server: asyncio.base_events.Server) -> None:
    """Ferme proprement le serveur asyncio.start_server."""
    if server is None:
        return
    server.close()
    await server.wait_closed()