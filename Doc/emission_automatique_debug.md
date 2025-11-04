"""
Résumé du problème et solutions tentées - Émission automatique de messages

## Objectif
Modification des entités (Patient, Dossier, Venue, Mouvement) → émission automatique de messages HL7/FHIR vers endpoints configurés

## Problème 1: Type de message non préservé
❌ **BUG découvert**: `generate_pam_hl7()` hardcode les types de messages
- Mouvement → toujours ADT^A02 (alors que entity.type contient le vrai type)
- Dossier → toujours ADT^A01  
- Patient → toujours ADT^A04

✅ **FIX**: Extraction du type depuis `entity.type` et utilisation dans MSH-9
- Pour mouvement: utilise `entity.type` (ex: "ADT^A01", "ADT^A02", etc.)
- Construction complète du message avec MSH+EVN+PID+PV1

## Problème 2: Pool de connexions saturé
❌ Les sessions SQLModel restaient ouvertes pendant l'émission MLLP (lente)
- Pool limité à 5 connexions + 10 overflow
- Timeouts après 30s

✅ **Tentative 1**: Expunge entity puis créer nouvelle session pour émission  
❌ **Échec**: Lazy load errors sur relations (venue.mouvements, dossier.venues, etc.)

✅ **Tentative 2**: Eager load toutes les relations avant expunge
❌ **Échec**: Toujours des lazy load errors dans FHIR generation

## Problème 3: Boucle infinie d'émissions
❌ **PROBLÈME ACTUEL**:
1. Message A01 reçu → crée Patient/Dossier/Venue/Mouvement
2. Listeners déclenchent émissions automatiques
3. Émissions envoient messages HL7 à endpoints
4. Messages HL7 re-reçus par serveur MLLP (boucle)
5. Processus se répète infiniment → saturation

## Solutions possibles

### Option A: Flag pour désactiver listeners pendant émission (RECOMMANDÉ)
```python
# Dans entity_events.py
_emission_in_progress = threading.local()

def _emit_in_new_session(...):
    _emission_in_progress.active = True
    try:
        await emit_to_senders_async(...)
    finally:
        _emission_in_progress.active = False

# Dans listener
if getattr(_emission_in_progress, 'active', False):
    return  # Skip emission during emission
```

### Option B: Identifier la source du message
- Ajouter champ `source` dans MessageLog ("external", "auto_emission")
- Ne jamais re-émettre les messages avec source="auto_emission"
- Marquer tous les messages générés automatiquement

### Option C: Désactiver temporairement FHIR generation
✅ **IMPLÉMENTÉ** (temporaire): Commenté génération FHIR dans emit_on_create.py
- Permet de tester HL7 seul
- FHIR generation à réactiver une fois boucle résolue

### Option D: Ne pas écouter sur le même port qu'on envoie
- Endpoint receiver: 29000
- Endpoint senders: 29001, 29002 (ports différents)
- Empêche la réception immédiate des messages émis

## État actuel
- ✅ Type de message préservé (fix implémenté)
- ✅ FHIR generation désactivée (temporaire)
- ⏳ Session management simplifié (keep open pendant émission)
- ❌ Boucle infinie non résolue

## Prochaines étapes
1. Implémenter Option A (flag emission_in_progress)
2. Tester avec tous les types de messages (A01, A02, A03, A05, A21, A22, A31)
3. Réactiver FHIR generation avec fix pour lazy loads
4. Documenter configuration endpoints (éviter sender → receiver sur même port)

## Fichiers modifiés
- `app/services/emit_on_create.py`: Fix types messages + FHIR disabled
- `app/services/entity_events.py`: Session management multiple iterations
- `tools/inject_mllp_direct.py`: Script test injection directe
- `tools/test_all_message_types.py`: Test complet tous types

## Tests réussis
- ✅ Injection A01 → ACK reçu
- ✅ Type A01 préservé dans message généré (IDs 111, 112)
- ❌ Test complet (7 types) : boucle infinie empêche vérification complète
