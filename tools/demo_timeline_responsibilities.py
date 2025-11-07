#!/usr/bin/env python3
"""
Script de démonstration pour tester la timeline des responsabilités.
Crée un patient avec plusieurs mouvements montrant différents changements d'UF.
"""
import asyncio
from datetime import datetime
from sqlmodel import Session, select

from app.db import engine
from app.models import Patient, Dossier, Venue, Mouvement
from app.services.transport_inbound import on_message_inbound
from app.models_endpoints import SystemEndpoint


def create_test_messages():
    """Crée une série de messages HL7 avec différentes natures ZBE-9.
    
    Utilise les UF réelles du GHT Demo :
    - URGA : UF Accueil Urgences
    - CARD-HC : UF Cardiologie Hospitalisation
    - CARD-SI : UF Cardiologie Soins Intensifs
    - MAT-SC : UF Maternité Suites de Couches
    """
    base_date = datetime.utcnow()
    
    messages = [
        # A01 - Admission aux Urgences avec nature M (médicale)
        f"""MSH|^~\\&|SRC|FAC|DST|FAC|{base_date.strftime('%Y%m%d%H%M%S')}||ADT^A01^ADT_A01|MSG001|P|2.5^FRA^2.1
EVN|A01|{base_date.strftime('%Y%m%d%H%M%S')}
PID|||TIMELINE001^^^FAC^PI||DEMO^Timeline||19850315|M
PV1||I|CHU-DEMO-UH-URG-ZO^CHU-DEMO-CH-URG-01^CHU-DEMO-LIT-URG-0101|||||||||||||||VN001|||||||||||||||||||||{base_date.strftime('%Y%m%d%H%M%S')}
ZBE|1|{base_date.strftime('%Y%m%d%H%M%S')}||CREATE|N|A01|^^^^^^URGA^CHU-DEMO-UF-URG-ACC||CHU-DEMO-UF-URG-ACC^URGA|||M""",
        
        # A02 - Transfert en Cardiologie avec nature M (médicale - UF médicale change)
        f"""MSH|^~\\&|SRC|FAC|DST|FAC|{base_date.strftime('%Y%m%d%H%M%S')}||ADT^A02^ADT_A02|MSG002|P|2.5^FRA^2.1
EVN|A02|{base_date.strftime('%Y%m%d%H%M%S')}
PID|||TIMELINE001^^^FAC^PI||DEMO^Timeline||19850315|M
PV1||I|CHU-DEMO-UH-CARD-HOSP-3A^CHU-DEMO-CH-CARD-301^CHU-DEMO-LIT-CARD-30101|||||||||||||||||VN001|||||||||||||||||||||{base_date.strftime('%Y%m%d%H%M%S')}
ZBE|1|{base_date.strftime('%Y%m%d%H%M%S')}||UPDATE|N|A02|^^^^^^CARD-HC^CHU-DEMO-UF-CARD-HOSP||CHU-DEMO-UF-CARD-HOSP^CARD-HC|||M""",
        
        # A02 - Transfert en Soins Intensifs Cardio avec nature H (hébergement - changement lit)
        f"""MSH|^~\\&|SRC|FAC|DST|FAC|{base_date.strftime('%Y%m%d%H%M%S')}||ADT^A02^ADT_A02|MSG003|P|2.5^FRA^2.1
EVN|A02|{base_date.strftime('%Y%m%d%H%M%S')}
PID|||TIMELINE001^^^FAC^PI||DEMO^Timeline||19850315|M
PV1||I|CHU-DEMO-UH-CARD-SI^CHU-DEMO-CH-SI-01^CHU-DEMO-LIT-SI-0101|||||||||||||||||VN001|||||||||||||||||||||{base_date.strftime('%Y%m%d%H%M%S')}
ZBE|1|{base_date.strftime('%Y%m%d%H%M%S')}||UPDATE|N|A02|^^^^^^CARD-SI^CHU-DEMO-UF-CARD-SI||CHU-DEMO-UF-CARD-SI^CARD-SI|||H""",
        
        # A02 - Transfert dans même UF avec nature L (logistique - pas de changement UF)
        f"""MSH|^~\\&|SRC|FAC|DST|FAC|{base_date.strftime('%Y%m%d%H%M%S')}||ADT^A02^ADT_A02|MSG004|P|2.5^FRA^2.1
EVN|A02|{base_date.strftime('%Y%m%d%H%M%S')}
PID|||TIMELINE001^^^FAC^PI||DEMO^Timeline||19850315|M
PV1||I|CHU-DEMO-UH-CARD-SI^CHU-DEMO-CH-SI-02^CHU-DEMO-LIT-SI-0201|||||||||||||||||VN001|||||||||||||||||||||{base_date.strftime('%Y%m%d%H%M%S')}
ZBE|1|{base_date.strftime('%Y%m%d%H%M%S')}||UPDATE|N|A02|^^^^^^CARD-SI^CHU-DEMO-UF-CARD-SI||CHU-DEMO-UF-CARD-SI^CARD-SI|||L""",
        
        # A02 - Retour en hospitalisation cardio avec nature M (médicale)
        f"""MSH|^~\\&|SRC|FAC|DST|FAC|{base_date.strftime('%Y%m%d%H%M%S')}||ADT^A02^ADT_A02|MSG005|P|2.5^FRA^2.1
EVN|A02|{base_date.strftime('%Y%m%d%H%M%S')}
PID|||TIMELINE001^^^FAC^PI||DEMO^Timeline||19850315|M
PV1||I|CHU-DEMO-UH-CARD-HOSP-3B^CHU-DEMO-CH-CARD-302^CHU-DEMO-LIT-CARD-30201|||||||||||||||||VN001|||||||||||||||||||||{base_date.strftime('%Y%m%d%H%M%S')}
ZBE|1|{base_date.strftime('%Y%m%d%H%M%S')}||UPDATE|N|A02|^^^^^^CARD-HC^CHU-DEMO-UF-CARD-HOSP||CHU-DEMO-UF-CARD-HOSP^CARD-HC|||M""",
        
        # A03 - Sortie avec nature D (pas de changement)
        f"""MSH|^~\\&|SRC|FAC|DST|FAC|{base_date.strftime('%Y%m%d%H%M%S')}||ADT^A03^ADT_A03|MSG006|P|2.5^FRA^2.1
EVN|A03|{base_date.strftime('%Y%m%d%H%M%S')}
PID|||TIMELINE001^^^FAC^PI||DEMO^Timeline||19850315|M
PV1||I|CHU-DEMO-UH-CARD-HOSP-3B^CHU-DEMO-CH-CARD-302^CHU-DEMO-LIT-CARD-30201|||||||||||||||||VN001|||||||||||||||||||||{base_date.strftime('%Y%m%d%H%M%S')}
ZBE|1|{base_date.strftime('%Y%m%d%H%M%S')}||UPDATE|N|A03|^^^^^^CARD-HC^CHU-DEMO-UF-CARD-HOSP||CHU-DEMO-UF-CARD-HOSP^CARD-HC|||D""",
    ]
    
    return messages


async def main():
    print("🚀 Création d'un scénario de test pour la timeline des responsabilités\n")
    
    with Session(engine) as session:
        # Créer un endpoint de test
        ep = session.exec(select(SystemEndpoint).where(SystemEndpoint.name == "TEST_TIMELINE")).first()
        if not ep:
            ep = SystemEndpoint(name="TEST_TIMELINE", kind="MLLP", role="receiver")
            session.add(ep)
            session.commit()
            session.refresh(ep)
        
        messages = create_test_messages()
        
        print("📨 Injection des messages HL7...")
        for i, msg in enumerate(messages, 1):
            print(f"\n   [{i}/{len(messages)}] Envoi message...")
            ack = await on_message_inbound(msg, session, ep)
            if "MSA|AA|" in ack:
                print(f"   ✅ Message {i} accepté")
            else:
                print(f"   ❌ Message {i} rejeté: {ack[:200]}")
        
        # Récupérer le patient créé
        patient = session.exec(select(Patient).where(Patient.external_id == "TIMELINE001")).first()
        if not patient:
            print("\n❌ Patient non trouvé!")
            return
        
        # Récupérer le dossier
        dossier = session.exec(select(Dossier).where(Dossier.patient_id == patient.id)).first()
        if not dossier:
            print("\n❌ Dossier non trouvé!")
            return
        
        # Récupérer la venue
        venue = session.exec(select(Venue).where(Venue.dossier_id == dossier.id)).first()
        if not venue:
            print("\n❌ Venue non trouvée!")
            return
        
        # Afficher les mouvements créés
        mouvements = session.exec(
            select(Mouvement)
            .where(Mouvement.venue_id == venue.id)
            .order_by(Mouvement.when.asc())
        ).all()
        
        print(f"\n✅ Scénario créé avec succès!")
        print(f"\n📊 Résumé:")
        print(f"   - Patient: {patient.family} {patient.given} (ID: {patient.id})")
        print(f"   - Dossier: #{dossier.dossier_seq} (ID: {dossier.id})")
        print(f"   - Venue: #{venue.venue_seq} (ID: {venue.id})")
        print(f"   - Mouvements: {len(mouvements)}")
        
        print(f"\n🔗 Accédez à la timeline ici:")
        print(f"   http://127.0.0.1:8000/venues/{venue.id}")
        
        print(f"\n📋 Détail des mouvements:")
        for mvt in mouvements:
            nature = mvt.movement_nature or "—"
            uf_med = mvt.uf_medicale or "—"
            uf_heb = mvt.uf_hebergement or "—"
            uf_soins = mvt.uf_soins or "—"
            print(f"\n   {mvt.when.strftime('%H:%M:%S')} - {mvt.type}")
            print(f"      Nature: {nature}")
            print(f"      UF Med: {uf_med} | UF Héb: {uf_heb} | UF Soins: {uf_soins}")
            print(f"      Location: {mvt.location}")


if __name__ == "__main__":
    asyncio.run(main())
