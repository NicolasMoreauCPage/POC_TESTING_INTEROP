### Objectif rapide
Ce dépôt est un POC FastAPI pour tester l'interopérabilité FHIR et HL7v2 (MLLP).
L'agent doit aider à modifier, étendre et tester des intégrations MLLP et FHIR.

### Points d'entrée & exécution
- Application FastAPI : `app.create_app()` dans `app/app.py`. L'instance exposée est `app`.
- Commande de développement courante :
  - uvicorn app.app:app --reload
- UI d'administration (SQLAdmin) : montée automatiquement par `app/app.py` (chemin par défaut `/admin`).

### Architecture & flux de données (haut-niveau)
- FastAPI routes (`app/routers/*`) exposent l'API web et les points opérationnels (ex. `/interop/*` pour contrôler MLLP).
- Persist: SQLModel/SQLite via `app/db.py`, modèles définis dans `app/models.py` et `app/models_endpoints.py`.
- MLLP (HL7v2) :
  - Manager : `app/services/mllp_manager.py` — démarre/arrête des serveurs MLLP et garde la table des serveurs en mémoire.
  - Serveur et framing : `app/services/mllp.py` — fonctions clés : `frame_hl7`, `deframe_hl7`, `parse_msh_fields`, `build_ack`, `start_mllp_server`, `send_mllp`.
  - Hook message entrant : `app/services/transport_inbound.py::on_message_inbound` est passé à `MLLPManager` lors de la création (voir `app/app.py`).
- FHIR outbound : `app/services/fhir_transport.py` utilise `httpx.AsyncClient` pour poster des Bundles/Resources.
- Génération FHIR exemple : `app/services/fhir.py::generate_fhir_bundle_for_dossier(dossier)` construit un Bundle Patient+Encounter.

### Conventions et patterns spécifiques
- Sessions DB
  - Routeurs FastAPI utilisent `Depends(get_session)` (défini dans `app/db.py`) pour l'injection de session.
  - Les handlers MLLP utilisent `app/db_session_factory.session_factory()` pour obtenir une session de courte durée (contexte synchro dans worker asyncio).
- Séquences métiers
  - Suite simple via `Sequence` + fonctions `peek_next_sequence` / `get_next_sequence` dans `app/db.py`.
- Journaux de messages
  - `MessageLog` (voir `app/models_endpoints.py`) contient `direction`, `kind`, `status`, `payload`, `ack_payload` — utile pour rechercher exemples de messages et ACK.

### Points d'attention pour un agent
- Quand tu touches au MLLP :
  - Respecte le pattern `frame/deframe` et n'écrase pas `parse_msh_fields` sans tests. Les ACKs sont construits par `build_ack`.
  - Utilise `session_factory()` dans les callbacks MLLP pour isoler transactions (voir `mllp.start_mllp_server` usage actuel).
- Pour appels FHIR sortants :
  - `app/services/fhir_transport.py` possède déjà `httpx.AsyncClient`. Pour certificats d'entreprise, passe `verify="/chemin/ca.pem"` au client ou configure `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE` dans l'environnement.
- Variables d'environnement utiles
  - `MLLP_TRACE=1` active des logs MLLP plus verbeux (`mllp.TRACE`).

### Exemples rapides (recherche/usage)
- Démarrer un MLLP depuis l'API : route POST `/interop/mllp/start/{endpoint_id}` (voir `app/routers/interop.py`).
- Générer un Bundle FHIR pour un dossier (méthode d'exemple) :
  - `from app.services.fhir import generate_fhir_bundle_for_dossier`
  - `bundle = generate_fhir_bundle_for_dossier(dossier)`

### Tests / debug spécifiques au projet
- Logs MLLP très utiles : set `MLLP_TRACE=1` puis lancer uvicorn; regarde les dumps HEX dans les logs.
- La DB est SQLite `sqlite:///./poc.db` par défaut (fichier local). Pour tests isolés, supprimer/renommer `poc.db` entre runs.

### Fichiers clés à consulter
- `app/app.py` — composition de l'application, création de `MLLPManager`, enregistrement des routeurs.
- `app/services/mllp.py` — framing, parsing, serveur asyncio.
- `app/services/mllp_manager.py` — orchestration des serveurs MLLP.
- `app/services/transport_inbound.py` — logique d'ingestion HL7 → journalisation → ACK.
- `app/services/fhir_transport.py` & `app/services/fhir.py` — envoi FHIR / génération Bundle.
- `app/models.py`, `app/models_endpoints.py` et `app/db.py` — modèle de données et helpers de séquence.

Si une section est incomplète ou tu veux ajouter des exemples de tests unitaires / snippets pour la gestion SSL en entreprise, dis-moi quelles parties tu veux que j'étende et j'itérerai.
