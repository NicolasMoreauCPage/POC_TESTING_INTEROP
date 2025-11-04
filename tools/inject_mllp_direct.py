"""
Inject HL7 message directly via MLLP socket to test automatic emission.
"""
import asyncio
import sys
from pathlib import Path

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.mllp import send_mllp


async def main():
    # Sample A01 message
    hl7_message = """MSH|^~\\&|SEND_APP|SEND_FAC|RECV_APP|RECV_FAC|20251103080000||ADT^A01^ADT_A01|MSG12345|P|2.5
EVN|A01|20251103080000
PID|1||TESTPAT123^^^HOSP^PI||TESTFAM^TESTGIVEN||19850315|M
PV1|1|I|0001^001^01^HOSP||||^SMITH^JOHN^^^DR|||||||||||12345678|||||||||||||||||||||||||20251103080000"""

    print("📨 Sending A01 message via MLLP to 127.0.0.1:29000...")
    print(f"   Patient: TESTFAM TESTGIVEN (ID: TESTPAT123)")
    
    try:
        response = await send_mllp("127.0.0.1", 29000, hl7_message)
        print(f"✅ Message sent successfully!")
        print(f"   ACK: {response[:200] if response else 'No response'}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
