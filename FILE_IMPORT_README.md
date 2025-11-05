# Système d'import/export de messages basé sur des fichiers

## Résumé des fonctionnalités

Vous disposez maintenant d'un système complet pour lire et écrire des messages HL7 depuis/vers des répertoires locaux :

### ✅ Lecture automatique de messages
- Scan de répertoires configurés
- Traitement alphabétique des fichiers
- Détection automatique MFN (structure) vs ADT (PAM)
- Archivage automatique avec horodatage
- Gestion des erreurs avec répertoire dédié

### ✅ Export de messages
- Écriture dans des répertoires configurés
- Organisation optionnelle par date (sous-dossiers YYYY-MM-DD)
- Nommage automatique avec timestamp et ID

### ✅ Intégration complète
- Endpoints FILE dans l'admin
- API REST pour scan manuel : `POST /messages/scan`
- Import direct : `POST /structure/import/hl7`
- Logging dans MessageLog avec statut et ACK

## Démarrage rapide

### 1. Tester avec le fichier exemple

```bash
# Depuis la racine du projet
python tools/test_file_import.py
```

Ce script va :
- Créer un endpoint FILE de test
- Copier le fichier `ExempleExtractionStructure.txt` dans l'inbox
- Scanner et traiter le fichier
- Afficher les statistiques d'import

### 2. Créer un endpoint FILE en production

Via l'admin (`/sqladmin`) :
1. Créer un `SystemEndpoint`
2. Configurer :
   - Kind: `FILE`
   - Inbox Path: `C:\HL7\inbox` (ou `/var/hl7/inbox` sur Linux)
   - Archive Path: `C:\HL7\archive`
   - Error Path: `C:\HL7\error`
   - File Extensions: `.hl7,.txt`
   - Is Enabled: ✓

### 3. Déclencher un scan

```bash
# Via API
curl -X POST http://localhost:8000/messages/scan

# Ou via Python
from app.services.file_poller import scan_file_endpoints
from app.db_session_factory import session_factory

with session_factory() as session:
    stats = scan_file_endpoints(session)
```

## Fichiers créés

```
app/
├── adapters/
│   └── filesystem_transport.py      # FileSystemReader/Writer
├── utils/
│   └── hl7_detector.py              # Détection type message (MFN/ADT)
├── services/
│   └── file_poller.py               # Service de scan et routage
├── routers/
│   └── messages.py                  # Endpoint POST /messages/scan
└── models_shared.py                 # Extension SystemEndpoint avec champs FILE

tools/
└── test_file_import.py              # Script de test

Doc/
└── file_based_import.md             # Documentation complète
```

## Exemples d'utilisation

### Import structure hospitalière (MFN)

```python
# 1. Placer le fichier MFN dans l'inbox
shutil.copy("structure.txt", "C:/HL7/inbox/001_structure.txt")

# 2. Scanner
from app.services.file_poller import scan_file_endpoints
stats = scan_file_endpoints(session)

# 3. Vérifier les entités créées
eg_count = session.exec(select(EntiteGeographique)).all()
print(f"Entités géographiques: {len(eg_count)}")
```

### Import mouvements patients (ADT)

```python
# Les fichiers ADT sont traités automatiquement
# et créent/mettent à jour patients/dossiers/venues/mouvements
inbox = Path("C:/HL7/inbox")
inbox / "A01_patient1.hl7"  # ADT^A01 admission
inbox / "A02_patient1.hl7"  # ADT^A02 transfert
inbox / "A03_patient1.hl7"  # ADT^A03 sortie

scan_file_endpoints(session)
# Fichiers traités par ordre alphabétique
```

### Export vers système tiers

```python
from app.adapters.filesystem_transport import FileSystemWriter

writer = FileSystemWriter(
    outbox_path="C:/HL7/outbox",
    use_subdirs=True,  # Créer sous-dossiers par date
    extension=".hl7"
)

# Écrire un message
hl7_message = "MSH|^~\\&|SRC|FAC|DEST|FAC|..."
file_path = writer.write_message(hl7_message, message_id="A01_123")
# → C:/HL7/outbox/2025-02-06/20250206_143025_456_A01_123.hl7
```

## Flux de traitement

```
┌─────────────────┐
│ Répertoire      │
│ inbox           │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ FileSystemReader│ Tri alphabétique
│ (.hl7, .txt)    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ HL7Detector     │ Analyse MSH-9
└────────┬────────┘
         │
         ├─→ MFN^M05 ──→ mfn_importer ──→ Structure DB (EJ/EG/Services)
         │
         ├─→ ADT^A01/02/03... ──→ PAM handler ──→ Patient/Dossier/Venue/Mouvement
         │
         └─→ Autre ──→ Log erreur
         │
         ↓
┌─────────────────┐
│ Archivage       │ 20250206_143025_fichier.hl7
│ ou Erreur       │
└─────────────────┘
```

## Points importants

- ✅ **Détection automatique** : Le système identifie seul si c'est du MFN (structure) ou de l'ADT (PAM)
- ✅ **Ordre de traitement** : Alphabétique, pour garantir l'ordre des mouvements
- ✅ **Robustesse** : Fichiers en erreur isolés, n'empêchent pas le traitement des suivants
- ✅ **Traçabilité** : Tous les messages loggés dans `MessageLog` avec statut
- ✅ **Archivage** : Conservation avec timestamp pour audit

## Documentation complète

Voir `Doc/file_based_import.md` pour :
- Configuration détaillée des endpoints
- Architecture des composants
- Exemples avancés
- Dépannage

## Prochaines étapes suggérées

1. **Scan automatique périodique** : Ajouter un job APScheduler ou Celery pour scanner toutes les X minutes
2. **Interface UI** : Page web pour déclencher le scan et voir l'état des répertoires
3. **Notifications** : Alertes email/Slack en cas d'erreur
4. **Métriques** : Dashboard avec nombre de fichiers traités, temps moyen, etc.
5. **Validation** : Schéma validation HL7 avant traitement
