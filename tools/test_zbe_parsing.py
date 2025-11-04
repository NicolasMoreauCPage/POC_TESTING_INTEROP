#!/usr/bin/env python3
"""
Test parsing du segment ZBE pour tous les types de messages IHE PAM
"""
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from app.db import engine, Session
from app.models import Patient, Dossier, Venue, Mouvement
from sqlmodel import select, delete


def build_test_message(trigger: str, patient_id: str, movement_seq: int) -> str:
    """Construit un message HL7 de test avec segment ZBE"""
    now = datetime.now()
    msh_timestamp = now.strftime("%Y%m%d%H%M%S")
    movement_timestamp = now.strftime("%Y%m%d%H%M%S")
    
    # Déterminer l'action ZBE-4 selon le trigger
    if trigger in ["A11", "A12", "A13", "A23", "A38", "A52", "A53", "A55"]:
        action_type = "CANCEL"
    elif trigger in ["A06", "A07", "A31"]:
        action_type = "UPDATE"
    else:
        action_type = "INSERT"
    
    # Segment ZBE complet
    zbe_segment = (
        f"ZBE|"  # ZBE-0
        f"{movement_seq}^MOVEMENT^1.2.250.1.213.1.1.9^ISO|"  # ZBE-1: Movement ID
        f"{movement_timestamp}|"  # ZBE-2: Movement datetime
        f"|"  # ZBE-3: empty
        f"{action_type}|"  # ZBE-4: INSERT/UPDATE/CANCEL
        f"N|"  # ZBE-5: Cancel indicator
        f"{trigger}|"  # ZBE-6: Original event (for cancellations)
        f"^^^^^^UF^^^CARDIO|"  # ZBE-7: UF responsabilité (code en position 10)
        f"|"  # ZBE-8: empty
        f"HMS"  # ZBE-9: Processing mode
    )
    
    message = (
        f"MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|{msh_timestamp}||ADT^{trigger}|MSG{movement_seq}|P|2.5|||AL|NE|FRA\r"
        f"EVN|{trigger}|{msh_timestamp}\r"
        f"PID|1||{patient_id}^^^HOSPITAL^PI||DOE^JOHN||19800101|M\r"
        f"PV1|1|I|3N^301^01^HOSPITAL^^^^CARDIO|||123456^DR^SMITH|||CARDIO|||||||654321^^^HOSPITAL^VN|||||||||||||||||HOSPITAL||||{msh_timestamp}\r"
        f"{zbe_segment}"
    )
    return message


async def test_zbe_parsing():
    """Test le parsing ZBE pour différents types de messages"""
    from app.services.mllp import parse_msh_fields
    from app.services.pam import _parse_zbe_segment
    
    print("\n" + "="*80)
    print("TEST: Parsing segment ZBE pour messages IHE PAM")
    print("="*80)
    
    test_cases = [
        ("A01", "Admission"),
        ("A02", "Transfer"),
        ("A03", "Discharge"),
        ("A11", "Cancel admission"),
        ("A21", "Leave of absence"),
        ("A54", "Change doctor"),
    ]
    
    for trigger, description in test_cases:
        print(f"\n{'─'*80}")
        print(f"Test: {trigger} - {description}")
        print(f"{'─'*80}")
        
        message = build_test_message(trigger, f"PAT{trigger}", 1000 + int(trigger[1:]))
        
        # Parser MSH
        msh = parse_msh_fields(message)
        print(f"MSH parsed: trigger={msh.get('trigger')}, timestamp={msh.get('timestamp')}")
        
        # Parser ZBE
        zbe = _parse_zbe_segment(message)
        if zbe:
            print(f"✅ ZBE parsed successfully:")
            print(f"   - movement_id: {zbe.get('movement_id')}")
            print(f"   - movement_datetime: {zbe.get('movement_datetime')}")
            print(f"   - action_type: {zbe.get('action_type')}")
            print(f"   - cancel_flag: {zbe.get('cancel_flag')}")
            print(f"   - origin_event: {zbe.get('origin_event')}")
            print(f"   - uf_responsable: {zbe.get('uf_responsable')}")
            print(f"   - mode_traitement: {zbe.get('mode_traitement')}")
        else:
            print(f"❌ ZBE parsing failed!")
    
    print(f"\n{'='*80}\n")


async def test_complete_zbe_structure():
    """Test la structure complète du segment ZBE"""
    from app.services.pam import _parse_zbe_segment
    
    print("\n" + "="*80)
    print("TEST: Structure complète segment ZBE")
    print("="*80)
    
    # Message A01 avec ZBE complet
    message = build_test_message("A01", "TEST_ZBE_001", 5000)
    
    print(f"\nMessage complet:")
    for line in message.split("\r"):
        print(f"  {line}")
    
    # Parser ZBE
    zbe = _parse_zbe_segment(message)
    
    print(f"\n{'─'*80}")
    print("Données ZBE extraites:")
    print(f"{'─'*80}")
    
    if zbe:
        for key, value in zbe.items():
            if value:
                print(f"  ✅ {key:20s} : {value}")
            else:
                print(f"  ⚠️  {key:20s} : (vide)")
    
    # Vérifier que ZBE-2 peut être parsé en datetime
    if zbe and zbe.get("movement_datetime"):
        try:
            dt_str = zbe["movement_datetime"]
            dt = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            print(f"\n✅ ZBE-2 datetime parsed: {dt}")
            print(f"   Format: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"\n❌ ZBE-2 datetime parse failed: {e}")
    
    # Vérifier que l'UF a bien été extrait de ZBE-7-10
    if zbe and zbe.get("uf_responsable"):
        print(f"\n✅ ZBE-7 UF extracted: {zbe['uf_responsable']}")
        print(f"   Expected: CARDIO")
        if zbe['uf_responsable'] == "CARDIO":
            print(f"   ✅ MATCH!")
        else:
            print(f"   ❌ MISMATCH!")
    
    print(f"\n{'='*80}\n")


async def main():
    # Test 1: Parser ZBE pour différents triggers
    await test_zbe_parsing()
    
    # Test 2: Structure complète du ZBE
    await test_complete_zbe_structure()


if __name__ == "__main__":
    asyncio.run(main())
