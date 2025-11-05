# Import de messages depuis des répertoires locaux

## Vue d'ensemble

Le système supporte maintenant la lecture et l'écriture de messages HL7 depuis des répertoires locaux, en complément de MLLP et FHIR.

### Fonctionnalités

- **Lecture automatique** : Scan des répertoires configurés et traitement alphabétique des fichiers
- **Détection automatique** : Distingue automatiquement MFN (structure) et ADT (PAM) via le segment MSH
- **Archivage** : Déplace les fichiers traités vers un répertoire d'archive avec horodatage
- **Gestion d'erreurs** : Déplace les fichiers en erreur vers un répertoire spécifique
- **Export** : Écriture de messages sortants dans des répertoires configurés

## Configuration d'un endpoint FILE

### Via l'interface admin

1. Aller dans **Administration** (`/sqladmin`)
2. Créer un nouveau **SystemEndpoint**
3. Configurer :
   - **Kind** : `FILE`
   - **Role** : `receiver` (pour lecture), `sender` (pour écriture), ou `both`
   - **Inbox Path** : Chemin du répertoire à surveiller (ex: `C:\HL7\inbox`)
   - **Outbox Path** : Chemin pour les messages sortants (ex: `C:\HL7\outbox`)
   - **Archive Path** : Chemin pour l'archivage (ex: `C:\HL7\archive`)
   - **Error Path** : Chemin pour les erreurs (ex: `C:\HL7\error`)
   - **File Extensions** : Extensions acceptées, séparées par virgules (ex: `.hl7,.txt`)
   - **Is Enabled** : Cocher pour activer

### Via code Python

```python
from app.models_shared import SystemEndpoint
from app.models_structure_fhir import GHTContext

endpoint = SystemEndpoint(
    name="Production Inbox",
    kind="FILE",
    role="receiver",
    is_enabled=True,
    ght_context_id=ght.id,
    inbox_path="C:/HL7/inbox",
    archive_path="C:/HL7/archive",
    error_path="C:/HL7/error",
    file_extensions=".txt,.hl7"
)
session.add(endpoint)
session.commit()
```

## Traitement des messages

### Scan manuel via API

```bash
# Déclencher un scan de tous les endpoints FILE
curl -X POST http://localhost:8000/messages/scan
```

Réponse:
```json
{
  "success": true,
  "stats": {
    "endpoints_scanned": 1,
    "files_processed": 5,
    "mfn_messages": 2,
    "adt_messages": 3,
    "unknown_messages": 0,
    "errors": []
  },
  "message": "Scanned 1 endpoints, processed 5 files"
}
```

### Scan programmatique

```python
from app.services.file_poller import scan_file_endpoints
from app.db_session_factory import session_factory

with session_factory() as session:
    stats = scan_file_endpoints(session)
    print(f"Processed {stats['files_processed']} files")
```

### Scan automatique (futur)

À implémenter : job planifié (APScheduler, Celery, ou cron) qui appelle périodiquement `scan_file_endpoints()`.

## Détection automatique des types de messages

Le système analyse le segment MSH pour déterminer le type :

### MFN (Structure)

```
MSH|^~\&|STR|STR|RECEPTEUR|RECEPTEUR|20250206141011||MFN^M05^MFN_M05|...
```
→ Routé vers `mfn_importer` pour créer/mettre à jour la structure (EntiteJuridique, EntiteGeographique, Services, etc.)

### ADT (PAM)

```
MSH|^~\&|SRC|FAC|DEST|FAC|20250206||ADT^A01^ADT_A01|...
```
→ Routé vers le handler PAM pour créer/mettre à jour patients, dossiers, venues, mouvements

## Test avec le fichier exemple

Un script de test est fourni pour valider l'import du fichier MFN exemple :

```bash
# Depuis la racine du projet
python tools/test_file_import.py
```

Ce script :
1. Crée un endpoint FILE de test
2. Copie `Doc/SpecStructureMFN/ExempleExtractionStructure.txt` dans l'inbox
3. Lance le scan et affiche les statistiques
4. Archive le fichier traité

Résultat attendu :
```
=== File-Based Message Import Test ===

Step 1: Setting up FILE endpoint...
Created GHT context: GHT Test (ID: 1)
Created FILE endpoint: Test File Inbox (ID: 1)
Inbox: C:\Travail\Fhir_Tester\MedData_Bridge\test_inbox
...

Step 3: Processing files...
Scanning file endpoints...

=== Processing Statistics ===
Endpoints scanned: 1
Files processed: 1
MFN messages: 1
ADT messages: 0
Unknown messages: 0

=== Summary ===
✓ File processing completed successfully
```

## Export de messages

### Via FileSystemWriter

```python
from app.adapters.filesystem_transport import FileSystemWriter

writer = FileSystemWriter(
    outbox_path="C:/HL7/outbox",
    use_subdirs=True,  # Organiser par date YYYY-MM-DD
    extension=".hl7"
)

# Écrire un message
file_path = writer.write_message(
    content=hl7_message,
    message_id="A01_12345"
)
print(f"Message écrit: {file_path}")
```

## Architecture

### Composants créés

1. **`app/adapters/filesystem_transport.py`**
   - `FileSystemReader` : Lecture et archivage
   - `FileSystemWriter` : Écriture vers répertoires

2. **`app/utils/hl7_detector.py`**
   - `HL7Detector` : Analyse du segment MSH
   - Détection MFN vs ADT

3. **`app/services/file_poller.py`**
   - `FilePollerService` : Orchestration du scan
   - Routage vers handlers appropriés

4. **`app/models_shared.py`**
   - Extension de `SystemEndpoint` avec champs FILE
   - `inbox_path`, `outbox_path`, `archive_path`, `error_path`, `file_extensions`

5. **Endpoints API**
   - `POST /messages/scan` : Scan manuel
   - `POST /structure/import/hl7` : Import direct (déjà existant)

### Flux de traitement

```
Répertoire inbox
    ↓
FileSystemReader (tri alphabétique)
    ↓
HL7Detector (analyse MSH-9)
    ↓
    ├─ MFN^M05 → mfn_importer → Structure DB
    ├─ ADT^A01/A02/... → PAM handler → Patient/Dossier/Venue/Mouvement
    └─ Autre → Log erreur
    ↓
Archivage avec timestamp
```

## Exemples d'utilisation

### Scénario 1 : Import structure hospitalière

1. Placer le fichier MFN dans `C:\HL7\inbox\structure_hopital.txt`
2. Appeler `POST /messages/scan`
3. Vérifier la structure importée via `/structure`

### Scénario 2 : Import mouvements patients

1. Placer des fichiers ADT dans `C:\HL7\inbox\` (ex: `ADT_A01_001.hl7`, `ADT_A02_002.hl7`)
2. Appeler `POST /messages/scan`
3. Les fichiers sont traités par ordre alphabétique
4. Vérifier les patients/mouvements via `/patients`, `/mouvements`

### Scénario 3 : Export vers système tiers

```python
from app.adapters.filesystem_transport import FileSystemWriter
from app.services.hl7_generator import generate_adt_a01

writer = FileSystemWriter("C:/HL7/outbox")

# Générer et exporter un ADT^A01
hl7_msg = generate_adt_a01(patient, dossier, venue)
writer.write_message(hl7_msg, message_id=f"A01_{patient.id}")
```

## Notes importantes

- Les fichiers sont traités **un par un** dans l'ordre alphabétique
- Le traitement s'arrête en cas d'erreur (fichier déplacé vers `error_path`)
- Les messages réussis sont archivés avec timestamp : `20250206_141530_fichier.hl7`
- Le contexte GHT est déterminé par l'endpoint ou le GHT actif par défaut
- Pour MFN : les relations parent-enfant (EJ→EG→Service) sont gérées automatiquement

## Dépannage

### Fichiers non traités

- Vérifier que l'endpoint est `is_enabled=True`
- Vérifier les extensions de fichiers (`file_extensions`)
- Vérifier les permissions sur les répertoires

### Erreurs d'import

- Consulter `/messages` pour voir les logs détaillés
- Vérifier le répertoire `error_path` pour les fichiers en erreur
- Consulter les logs serveur pour les stack traces

### MFN non reconnu

- Vérifier la présence du segment `MSH` avec `MFN^M05`
- Vérifier la syntaxe HL7 (séparateurs `|`, `^`, `~`, `\`, `&`)
