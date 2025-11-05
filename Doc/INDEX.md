# 📚 Documentation MedData Bridge

Documentation complète du projet MedData Bridge - Plateforme d'interopérabilité HL7v2 (IHE PAM) et FHIR pour le système de santé français.

---

## 🚀 Démarrage Rapide

### [📖 Getting Started](01-Getting-Started/)

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Guide d'installation et de configuration |
| [CONTRIBUTING.md](01-Getting-Started/CONTRIBUTING.md) | Guide de contribution au projet |

**Points clés** :
- Installation et configuration de l'environnement
- Variables d'environnement (`TESTING`, `INIT_VOCAB`, `MLLP_TRACE`)
- Commandes de démarrage (développement et production)
- Structure du code et conventions

---

## 📋 Validation HL7 v2.5 & IHE PAM

### [✅ 02-Validation](02-Validation/)

Documentation complète sur la validation des messages HL7 v2.5 et conformité IHE PAM.

| Document | Description |
|----------|-------------|
| [INDEX_VALIDATION_PAM.md](02-Validation/INDEX_VALIDATION_PAM.md) | 🔍 **INDEX PRINCIPAL** - Vue d'ensemble validation |
| [RESUME_VALIDATION_DATATYPES.md](02-Validation/RESUME_VALIDATION_DATATYPES.md) | Résumé validation des types de données complexes |
| [REGLES_VALIDATION_HL7v25.md](02-Validation/REGLES_VALIDATION_HL7v25.md) | Règles de validation HL7 v2.5 standard |
| [REGLES_DATATYPES_COMPLEXES_HL7v25.md](02-Validation/REGLES_DATATYPES_COMPLEXES_HL7v25.md) | Règles détaillées pour CX, XPN, XAD, etc. |
| [VALIDATION_ORDRE_SEGMENTS.md](02-Validation/VALIDATION_ORDRE_SEGMENTS.md) | Validation de l'ordre des segments |

**Couverture** :
- ✅ Validation HL7 v2.5 base (MSH, EVN, PID, PV1)
- ✅ Types de données complexes (CX, XPN, XAD, XTN, TS, DT)
- ✅ Ordre des segments selon structures HAPI
- ✅ Règles IHE PAM spécifiques France

---

## 🏥 IHE PAM (Patient Administration Management)

### [📘 03-IHE-PAM](03-IHE-PAM/)

Documentation sur le profil IHE PAM et extensions françaises (segments Z).

| Document | Description |
|----------|-------------|
| [conformite_zbe.md](03-IHE-PAM/conformite_zbe.md) | Conformité segment ZBE (extension CPage) |
| [namespaces_mouvement_finess.md](03-IHE-PAM/namespaces_mouvement_finess.md) | Namespaces MOUVEMENT et FINESS |

**Sujets abordés** :
- Segment ZBE (ZBE-1: Identifiant mouvement, ZBE-2: Date/heure, ZBE-9: Mode traitement)
- Règle ZBE-9="C" : uniquement Z99 sur A01/A04/A05, état admission/préadmission
- Namespaces : CPAGE, IPP, NDA, VENUE, MOUVEMENT, FINESS
- Format CX pour identifiants (valeur^^^namespace^type)

---

## 👤 Gestion des Patients

### [🧑‍⚕️ 04-Patient-Management](04-Patient-Management/)

Documentation sur la gestion des patients, RGPD et identifiants.

| Document | Description |
|----------|-------------|
| [PATIENT_IMPROVEMENTS_RECAP.md](04-Patient-Management/PATIENT_IMPROVEMENTS_RECAP.md) | 📊 **Récapitulatif** améliorations formulaire patient |
| [formulaire_patient_rgpd.md](04-Patient-Management/formulaire_patient_rgpd.md) | Conformité RGPD (Article 9 - données sensibles) |
| [spec_patient_identifiers_addresses.md](04-Patient-Management/spec_patient_identifiers_addresses.md) | Spécification identifiants et adresses multi-valués |

**Conformité réglementaire** :
- ✅ RGPD Article 9 : Pas de collecte race/religion
- ✅ NIR (Numéro de sécurité sociale) : Usage conforme santé
- ✅ PID-32 : Statut fiabilité identité (INS)
- ✅ Standards HL7 Table 0002 (statut marital), Table 0445 (fiabilité identité)

---

## 🏗️ Architecture & Workflows

### [⚙️ 05-Architecture](05-Architecture/)

Architecture technique et gestion des workflows IHE PAM.

| Document | Description |
|----------|-------------|
| [architecture_workflows_proposal.md](05-Architecture/architecture_workflows_proposal.md) | Proposition architecture workflows et transitions |
| [dossier_types.md](05-Architecture/dossier_types.md) | Types de dossiers (Hospitalisation, Externe, Urgence) |
| [STANDARDS.md](05-Architecture/STANDARDS.md) | Standards et références (HL7 v2.5, FHIR R4, IHE PAM) |

**Points clés** :
- Modèle Patient → Dossier → Venue → Mouvement
- Transitions d'état IHE PAM (A01→A02→A03, A05→A01, A04→A06, etc.)
- Types de dossiers et synchronisation avec PV1-2 (patient_class)
- Gestion des annulations (A11/A12/A13/A23/A38/A52/A53/A55)

---

## 🔗 Intégration & Endpoints

### [🌐 06-Integration](06-Integration/)

Documentation sur l'intégration HL7 v2.5, FHIR et endpoints.

| Document | Description |
|----------|-------------|
| [INTEGRATION_HL7v25_RECAP.md](06-Integration/INTEGRATION_HL7v25_RECAP.md) | Récapitulatif intégration HL7 v2.5 |
| [INTEGRATION_DATATYPES_COMPLEXES_RECAP.md](06-Integration/INTEGRATION_DATATYPES_COMPLEXES_RECAP.md) | Intégration types de données complexes |
| [FILE_IMPORT_README.md](06-Integration/FILE_IMPORT_README.md) | Import/export de messages via fichiers |
| [file_based_import.md](06-Integration/file_based_import.md) | Système d'import basé fichiers (détaillé) |
| [endpoints_hierarchical_organization.md](06-Integration/endpoints_hierarchical_organization.md) | Organisation hiérarchique des endpoints |

**Modes d'intégration** :
- 🔌 **MLLP** : Serveur HL7 v2.5 temps réel (ITI-30/31)
- 📁 **FILE** : Polling de répertoires (inbox/archive/error)
- 🌐 **HTTP** : REST API pour messages HL7 ou FHIR
- 🔄 **FHIR** : Export/import de ressources Patient/Encounter

---

## 📤 Émission de Messages

### [📨 07-Emission](07-Emission/)

Documentation sur l'émission automatique de messages vers systèmes externes.

| Document | Description |
|----------|-------------|
| [emission_automatique.md](07-Emission/emission_automatique.md) | Vue d'ensemble émission automatique |
| [emission_automatique_debug.md](07-Emission/emission_automatique_debug.md) | Guide de débogage émission |
| [etat_reel_emission.md](07-Emission/etat_reel_emission.md) | État réel du système d'émission |
| [correction_a31_emission.md](07-Emission/correction_a31_emission.md) | Corrections spécifiques A31 (update patient) |

**Fonctionnalités** :
- Émission automatique via entity_events (SQLModel listeners)
- Configuration sender_endpoints : MLLP, HTTP, FHIR
- Mapping événements : `on_patient_created`, `on_venue_updated`, etc.
- Gestion des erreurs et retries

---

## 🎬 Scénarios de Test

### [🧪 08-Scenarios](08-Scenarios/)

Scénarios de test et cas d'usage.

| Document | Description |
|----------|-------------|
| [scenario_date_update.md](08-Scenarios/scenario_date_update.md) | Scénario de mise à jour de dates (A54/A55) |

**À venir** :
- Scénarios complets d'admission/sortie
- Tests de transition d'état
- Cas limites et gestion d'erreurs

---

## 📦 Archives

### [🗂️ _Archived](_Archived/)

Documents archivés (consolidés ou obsolètes).

| Document | Raison |
|----------|--------|
| [FORMULAIRE_PATIENT_RESUME.md](_Archived/FORMULAIRE_PATIENT_RESUME.md) | Fusionné dans PATIENT_IMPROVEMENTS_RECAP.md |
| [POINT_GENERAL_FORMULAIRE_PATIENT.md](_Archived/POINT_GENERAL_FORMULAIRE_PATIENT.md) | Fusionné dans PATIENT_IMPROVEMENTS_RECAP.md |

---

## 🔍 Références Externes

### Spécifications HL7 & IHE

| Dossier | Contenu |
|---------|---------|
| `HAPI/` | Structures de messages HAPI (ADT_A01, MFN_M02, etc.) |
| `HL7v2.5/` | Spécifications HL7 v2.5 officielles (CH02A, CH03, etc.) |
| `SpecIHEPAM/` | Spécifications IHE PAM internationales |
| `SpecIHEPAM_CPage/` | Extensions IHE PAM CPage (France) |
| `SpecStructureMFN/` | Spécifications MFN (Master File Notification) |

---

## 🛠️ Outils & Scripts

### Initialisation

```bash
# Initialiser tous les vocabulaires et données de test
python tools/init_all.py

# Initialiser avec export FHIR
python tools/init_all.py --export-fhir

# Ré-initialiser uniquement les mouvements de test
python tools/init_demo_movements.py
```

### Validation

```bash
# Valider un message HL7
python tools/test_validation.py <fichier.hl7>

# Tester l'import de fichiers
python tools/test_file_import.py
```

### Base de données

```bash
# Inspecter le schéma DB
python tools/inspect_db.py

# Lister toutes les tables
python tools/list_tables.py
```

---

## 📊 Indicateurs de Qualité

| Aspect | Statut | Détails |
|--------|--------|---------|
| **Validation HL7 v2.5** | ✅ Complete | 4 couches (IHE PAM, HAPI, HL7 base, datatypes) |
| **Types de données** | ✅ Complete | CX, XPN, XAD, XTN, TS, DT validés |
| **Conformité IHE PAM** | ✅ Conforme | Transitions, segments Z, namespaces |
| **RGPD** | ✅ Conforme | Pas de race/religion, NIR autorisé santé |
| **Tests** | ⚠️ Partiel | Tests unitaires à compléter |
| **Documentation** | ✅ Complete | Guide complet disponible |

---

## 💡 Navigation Rapide

### Par Type de Tâche

| Je veux... | Document |
|------------|----------|
| Installer le projet | [README.md](../README.md) |
| Comprendre la validation | [INDEX_VALIDATION_PAM.md](02-Validation/INDEX_VALIDATION_PAM.md) |
| Configurer un endpoint | [endpoints_hierarchical_organization.md](06-Integration/endpoints_hierarchical_organization.md) |
| Gérer les patients RGPD | [formulaire_patient_rgpd.md](04-Patient-Management/formulaire_patient_rgpd.md) |
| Déboguer l'émission | [emission_automatique_debug.md](07-Emission/emission_automatique_debug.md) |
| Comprendre les workflows | [architecture_workflows_proposal.md](05-Architecture/architecture_workflows_proposal.md) |

### Par Standard

| Standard | Documents Associés |
|----------|-------------------|
| **HL7 v2.5** | [REGLES_VALIDATION_HL7v25.md](02-Validation/REGLES_VALIDATION_HL7v25.md), [INTEGRATION_HL7v25_RECAP.md](06-Integration/INTEGRATION_HL7v25_RECAP.md) |
| **IHE PAM** | [conformite_zbe.md](03-IHE-PAM/conformite_zbe.md), [INDEX_VALIDATION_PAM.md](02-Validation/INDEX_VALIDATION_PAM.md) |
| **FHIR R4** | [README.md](../README.md) section FHIR |
| **RGPD** | [formulaire_patient_rgpd.md](04-Patient-Management/formulaire_patient_rgpd.md) |

---

## 📞 Support & Contributions

- **Issues** : Rapporter un bug ou demander une fonctionnalité
- **Pull Requests** : Voir [CONTRIBUTING.md](01-Getting-Started/CONTRIBUTING.md)
- **Documentation** : Cette documentation est générée et maintenue automatiquement

---

*Dernière mise à jour : 5 novembre 2025*
*Version : 1.0.0*
