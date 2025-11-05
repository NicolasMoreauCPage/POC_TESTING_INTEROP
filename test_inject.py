"""Test direct d'injection de message"""
import asyncio
from app.db import engine
from sqlmodel import Session
from app.services.transport_inbound import on_message_inbound_async

async def test():
    payload = """MSH|^~\\&|TEST|TEST|TEST|TEST|20251105093000||ADT^A01|MSG003|P|2.5
PID|1||12345^^^TEST^MR||DUPONT^JEAN||19800101|M"""
    
    with Session(engine) as session:
        print(f"Testing with payload:\n{payload}\n")
        try:
            ack = await on_message_inbound_async(payload, session, None)
            print(f"ACK received:\n{ack}\n")
            session.commit()
            print("Session committed")
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
