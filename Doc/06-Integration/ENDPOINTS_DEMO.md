# Configuration des Endpoints de Démonstration

## Vue d'Ensemble

Le script `tools/init_all.py` crée automatiquement 4 endpoints de démonstration pour tester l'interopérabilité:

## Endpoints Créés

### 1. MLLP Receiver Demo (Réception)
**Configuration:**
- Type: `mllp` (HL7 v2.5)
- Rôle: `receiver` (réception de messages)
- Host: `127.0.0.1`
- Port: `2575`
- Sending App: `EXTERNAL_SYS` (système externe émetteur)
- Receiving App: `MedBridge` (notre application)
- Validation: IHE PAM FR activée (mode warn)

**Usage:**
- Reçoit les messages IHE PAM (ADT) depuis les systèmes externes
- Valide automatiquement les messages selon le profil IHE PAM FR
- Parse et intègre les patients, dossiers, venues, mouvements dans la base de données

**Pour tester:**
```bash
# Envoyer un message HL7 ADT A01 au receiver
echo "MSH|^~\&|EXTERNAL_SYS..." | nc 127.0.0.1 2575
```

### 2. MLLP Sender Demo (Émission)
**Configuration:**
- Type: `mllp` (HL7 v2.5)
- Rôle: `sender` (émission de messages)
- Host: `127.0.0.1`
- Port: `2576`
- Sending App: `MedBridge` (notre application)
- Receiving App: `TARGET_SYS` (système cible)

**Usage:**
- Émet automatiquement des messages MFN^M05 lors de modifications de structure (Location, Organization)
- Émet automatiquement des messages ADT lors de créations/modifications de mouvements
- Messages envoyés via MLLP avec ACK attendu

**Messages émis:**
- `MFN^M05` : Master File Notification pour locations (structures)
- `MFN^M05` : Master File Notification pour organizations (entités juridiques)
- `ADT^A01-A55` : Admissions, transferts, sorties (mouvements patients)

### 3. FHIR Receiver Demo (Réception)
**Configuration:**
- Type: `fhir` (FHIR R4)
- Rôle: `receiver` (réception de ressources)
- Base URL: `http://127.0.0.1:8000/fhir`
- Auth: none (pas d'authentification)

**Usage:**
- Point d'entrée FHIR pour l'application
- Reçoit des ressources FHIR (Patient, Encounter, Location, Organization)
- Convertit automatiquement en modèle interne

**Ressources acceptées:**
- `Patient` (fr-patient profile ANS)
- `Encounter` (venues/séjours)
- `Location` (fr-location profile ANS)
- `Organization` (fr-organization profile ANS)

**Pour tester:**
```bash
curl -X POST http://127.0.0.1:8000/fhir/Patient \
  -H "Content-Type: application/fhir+json" \
  -d '{"resourceType":"Patient",...}'
```

### 4. FHIR Sender Demo (Émission)
**Configuration:**
- Type: `fhir` (FHIR R4)
- Rôle: `sender` (émission de ressources)
- Base URL: `http://127.0.0.1:8080/fhir`
- Auth: none (pas d'authentification)

**Usage:**
- Émet automatiquement des Bundles FHIR lors de modifications
- Envoi via POST de Bundle transaction
- Utilisé pour synchroniser avec des serveurs FHIR externes

**Ressources émises:**
- `Location` : Lors de modifications de structure (UF, services, lits, etc.)
- `Organization` : Lors de modifications d'entités juridiques
- `Patient` : Lors de créations/modifications de patients
- `Encounter` : Lors de créations/modifications de venues

**Bundle format:**
```json
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [{
    "resource": {...},
    "request": {
      "method": "PUT",
      "url": "Location/123"
    }
  }]
}
```

## Émission Automatique

### Déclencheurs d'Émission

Les événements SQLAlchemy détectent automatiquement les modifications et émettent vers les endpoints `sender`:

#### Structure (Location)
- **Insert/Update**: EntiteGeographique, Pole, Service, UF, UH, Chambre, Lit
  - → FHIR: Bundle PUT Location vers `FHIR Sender Demo`
  - → MLLP: MFN^M05 snapshot complet vers `MLLP Sender Demo`

#### Organization (EntiteJuridique)
- **Insert/Update**: EntiteJuridique
  - → FHIR: Bundle PUT Organization vers `FHIR Sender Demo`
  - → MLLP: MFN^M05 Organization vers `MLLP Sender Demo`

#### Identités et Mouvements
- **Insert/Update**: Patient, Dossier, Venue, Mouvement
  - → FHIR: Bundle PUT Patient/Encounter vers `FHIR Sender Demo`
  - → MLLP: ADT^A01-A55 vers `MLLP Sender Demo`

### Traçabilité (MessageLog)

Toutes les émissions sont enregistrées dans la table `message_log`:

```sql
SELECT 
    direction,  -- 'out' pour émission
    kind,       -- 'FHIR' ou 'MLLP'
    endpoint_id,
    status,     -- 'sent', 'error', 'generated'
    message_type, -- 'MFN^M05', 'ADT^A01', etc.
    created_at
FROM message_log
WHERE direction = 'out'
ORDER BY created_at DESC;
```

## Configuration dans tools/init_all.py

```python
def init_demo_endpoints(session: Session, ght: GHTContext) -> None:
    """Crée des endpoints de démonstration pour réception et émission."""
    endpoints_config = [
        {
            "name": "MLLP Receiver Demo",
            "kind": "mllp",
            "role": "receiver",
            "host": "127.0.0.1",
            "port": 2575,
            "sending_app": "EXTERNAL_SYS",
            "sending_facility": "EXTERNAL_FACILITY",
            "receiving_app": "MedBridge",
            "receiving_facility": "GHT-DEMO",
            "pam_validate_enabled": True,
            "pam_validate_mode": "warn",
            "pam_profile": "IHE_PAM_FR",
        },
        # ... autres endpoints
    ]
```

## Tester les Endpoints

### Avec FastAPI en marche

1. **Démarrer l'application:**
```bash
.venv/Scripts/python -m uvicorn app.app:app --reload
```

2. **Créer une EntiteJuridique via l'UI:**
- Aller sur `http://127.0.0.1:8000/admin/ght/1/ej/new`
- Remplir le formulaire
- Soumettre

3. **Vérifier les émissions:**
```python
from sqlmodel import Session, select
from app.db import engine
from app.models_shared import MessageLog

with Session(engine) as session:
    messages = session.exec(
        select(MessageLog)
        .where(MessageLog.direction == "out")
        .order_by(MessageLog.created_at.desc())
        .limit(10)
    ).all()
    
    for msg in messages:
        print(f"{msg.kind} -> Endpoint {msg.endpoint_id}: {msg.status}")
```

### Test avec script test_endpoints_emission.py

```bash
python test_endpoints_emission.py
```

**Résultat attendu:**
```
+ Endpoints configures: 4
  - MLLP Receiver Demo (mllp receiver): 127.0.0.1:2575 [active]
  - MLLP Sender Demo (mllp sender): 127.0.0.1:2576 [active]
  - FHIR Receiver Demo (fhir receiver): http://127.0.0.1:8000/fhir [active]
  - FHIR Sender Demo (fhir sender): http://127.0.0.1:8080/fhir [active]

+ Messages emis: 2
  Endpoint: FHIR Sender Demo (fhir sender)
    ! FHIR - error (Connection refused - normal sans serveur FHIR externe)
  Endpoint: MLLP Sender Demo (mllp sender)
    ! MLLP - error (Connection refused - normal sans serveur MLLP externe)
```

## Erreurs Normales

### "Connection refused" (MLLP)
C'est normal si aucun serveur MLLP n'écoute sur le port 2576. Pour tester avec un vrai serveur:

```bash
# Installer un simulateur MLLP (exemple: Hapi TestPanel)
# ou utiliser netcat pour écouter:
nc -l 2576
```

### "Connection refused" (FHIR)
C'est normal si aucun serveur FHIR n'écoute sur http://127.0.0.1:8080/fhir. Pour tester avec un vrai serveur:

```bash
# Installer HAPI FHIR Server
docker run -p 8080:8080 hapiproject/hapi:latest
```

## Désactivation des Endpoints

Pour désactiver temporairement un endpoint sans le supprimer:

```python
from sqlmodel import Session, select
from app.db import engine
from app.models_shared import SystemEndpoint

with Session(engine) as session:
    endpoint = session.exec(
        select(SystemEndpoint).where(SystemEndpoint.name == "FHIR Sender Demo")
    ).first()
    
    if endpoint:
        endpoint.is_enabled = False
        session.commit()
        print("Endpoint desactive")
```

Ou via l'UI Admin: `http://127.0.0.1:8000/admin/endpoint`

## Production

Pour une utilisation en production:

1. **Modifier les hosts/ports** pour pointer vers les vrais serveurs
2. **Ajouter l'authentification** (auth_kind, auth_token pour FHIR)
3. **Configurer les facilities** (MSH-3, MSH-4 pour MLLP)
4. **Activer le chiffrement** (TLS/SSL pour MLLP, HTTPS pour FHIR)
5. **Surveiller MessageLog** pour détecter les erreurs d'émission

## Exemple de Configuration Production

```python
{
    "name": "FHIR Production Server",
    "kind": "fhir",
    "role": "sender",
    "base_url": "https://fhir.hopital.fr/fhir",
    "auth_kind": "bearer",
    "auth_token": "eyJhbGciOiJSUzI1NiIs...",
    "is_enabled": True,
}
```

```python
{
    "name": "MLLP Production Interface",
    "kind": "mllp",
    "role": "sender",
    "host": "interfaces.hopital.fr",
    "port": 2575,
    "sending_app": "MedBridge",
    "sending_facility": "GHT_PRODUCTION",
    "receiving_app": "DOSSIER_PATIENT",
    "receiving_facility": "HOSPITAL_SYSTEM",
    "is_enabled": True,
}
```

## Support

- Logs d'émission: `message_log` table
- Logs applicatifs: Vérifier les logs uvicorn/FastAPI
- Configuration: `system_endpoint` table
- Documentation API: `http://127.0.0.1:8000/docs`
