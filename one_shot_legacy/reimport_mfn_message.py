"""Script pour réimporter un message MFN spécifique."""
from app.db import get_session
from app.models_shared import MessageLog
from app.models_structure_fhir import GHTContext
from app.services.mfn_importer import import_mfn
from sqlmodel import select

# Récupérer le message
session = next(get_session())
msg = session.exec(
    select(MessageLog)
    .where(MessageLog.correlation_id.like('%20250206141011%'))
    .order_by(MessageLog.id.desc())
).first()

if not msg:
    print("Message non trouvé!")
    exit(1)

print(f"Message trouvé: ID={msg.id}, Type={msg.message_type}")
print(f"Endpoint: {msg.endpoint_id}")

# Récupérer le GHT "TEST Nico" (id=2)
ght = session.exec(select(GHTContext).where(GHTContext.id == 2)).first()
if not ght:
    print("GHT TEST Nico (id=2) non trouvé!")
    exit(1)

print(f"GHT: {ght.name} (id={ght.id})")

# Réimporter
print("\nRéimportation...")
result = import_mfn(msg.payload, session, ght)

print(f"\nRésultat:")
print(f"  EJ créées: {result['ej']}")
print(f"  EG créées: {result['eg']}")
print(f"  Services créés: {result['service']}")

print("\n✅ Import terminé!")
