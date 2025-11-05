# Index de la Documentation - Validation PAM

## Vue d'ensemble

Le système de validation PAM implémente une validation en **4 couches** des messages HL7 v2.5 IHE PAM.

## Documents par Thème

### 🎯 Démarrage Rapide

- **[RESUME_VALIDATION_DATATYPES.md](./RESUME_VALIDATION_DATATYPES.md)** ⭐
  - Résumé exécutif de l'implémentation complète
  - Architecture des 4 couches
  - Résultats des tests
  - **Commencer par ce document**

### 📋 Règles de Validation

1. **[REGLES_VALIDATION_HL7v25.md](./REGLES_VALIDATION_HL7v25.md)**
   - Règles HL7 v2.5 de base (Couche 3)
   - Validation MSH, EVN, PID
   - Champs obligatoires

2. **[REGLES_DATATYPES_COMPLEXES_HL7v25.md](./REGLES_DATATYPES_COMPLEXES_HL7v25.md)**
   - Règles types de données complexes (Couche 4)
   - CX, XPN, XAD, XTN, TS, PL, XCN
   - Tables HL7 (0004, 0190, 0200, 0201, 0202)
   - **Document de référence technique**

### 🔧 Intégration et Utilisation

1. **[INTEGRATION_HL7v25_RECAP.md](./INTEGRATION_HL7v25_RECAP.md)**
   - Intégration HL7 v2.5 base
   - Modifications code
   - Configuration endpoints

2. **[INTEGRATION_DATATYPES_COMPLEXES_RECAP.md](./INTEGRATION_DATATYPES_COMPLEXES_RECAP.md)**
   - Intégration types de données complexes
   - Tests et résultats
   - Guide d'activation
   - **Guide d'utilisation complet**

### 📚 Spécifications HAPI

Les structures HAPI (Couche 2) sont documentées dans:

- **Doc/HAPI/hapi/custom/message/**
  - ADT_A01.java, ADT_A03.java, ADT_A05.java, etc.
  - Structures détaillées par trigger

### 📖 Standards et Conformité

- **Doc/HL7v2.5/**
  - CH02A.pdf - Types de données HL7 v2.5
  - Ch03.pdf - Segments HL7 v2.5
  
- **Doc/SpecIHEPAM/**
  - Spécifications IHE Patient Administration Management

## Documents par Couche de Validation

### Couche 1: IHE PAM (Règles Métier)

- **Doc/SpecIHEPAM/** - Profil IHE PAM complet
- Code: `app/services/pam_validation.py` (section IHE PAM)

### Couche 2: HAPI Structures

- **Doc/HAPI/** - Structures Java HAPI
- **[VALIDATION_ORDRE_SEGMENTS.md](./VALIDATION_ORDRE_SEGMENTS.md)** - Validation ordre segments
- Code: `SEGMENT_RULES` et `SEGMENT_ORDER` dicts dans `pam_validation.py`
- 18 triggers mappés: A01, A03-A08, A11-A13, A21-A23, A28, A31, A40, A47, A52-A53
- Validation de l'ordre des segments selon HAPI

### Couche 3: HL7 v2.5 Base

- **[REGLES_VALIDATION_HL7v25.md](./REGLES_VALIDATION_HL7v25.md)**
- **[INTEGRATION_HL7v25_RECAP.md](./INTEGRATION_HL7v25_RECAP.md)**
- Code: Section "HL7 v2.5 base validation" dans `pam_validation.py`

### Couche 4: Types de Données Complexes

- **[REGLES_DATATYPES_COMPLEXES_HL7v25.md](./REGLES_DATATYPES_COMPLEXES_HL7v25.md)** ⭐
- **[INTEGRATION_DATATYPES_COMPLEXES_RECAP.md](./INTEGRATION_DATATYPES_COMPLEXES_RECAP.md)** ⭐
- Code: Fonctions `_validate_*()` dans `pam_validation.py`

## Tests

### Tests Disponibles

| Fichier | Description | Commande |
|---------|-------------|----------|
| **smoke_test_pam_validation.py** | Tests HL7 v2.5 base | `python tools/smoke_test_pam_validation.py` |
| **smoke_test_datatype_validation.py** | Tests types de données | `python tools/smoke_test_datatype_validation.py` |
| **test_segment_order.py** | Tests ordre segments | `python tools/test_segment_order.py` |
| **test_integration_complete.py** | Test 4 couches | `python tools/test_integration_complete.py` |
| **test_message_valide.py** | Message valide complet | `python tools/test_message_valide.py` |

### Exécution de Tous les Tests

```powershell
# Test complet
python tools/smoke_test_pam_validation.py
python tools/smoke_test_datatype_validation.py
python tools/test_segment_order.py
python tools/test_integration_complete.py
python tools/test_message_valide.py
```

## Configuration

### Activation par Endpoint

Via `/sqladmin` → SystemEndpoint:

| Champ | Valeurs | Description |
|-------|---------|-------------|
| `pam_validate_enabled` | true/false | Activer validation |
| `pam_validate_mode` | warn/reject | Mode warn (info) ou reject (rejet si fail) |
| `pam_profile` | IHE_PAM_FR | Profil IHE PAM |

### Supervision des Résultats

- **Liste messages**: `/messages` - Colonne PAM avec badges (ok/warn/fail)
- **Détail message**: `/messages/{id}` - Issues détaillées en JSON
- **Messages rejetés**: `/messages/rejections` - Rejets avec raison

## Code Source

### Fichiers Principaux

- **app/services/pam_validation.py** - Module de validation complet (661 lignes)
  - Fonctions `_validate_*()` pour types de données
  - Fonction `validate_pam()` intégrant 4 couches
  - Dataclasses `ValidationResult`, `ValidationIssue`

- **app/models_shared.py** - Modèles étendus
  - `SystemEndpoint`: champs `pam_validate_*`
  - `MessageLog`: champs `pam_validation_*`

- **app/services/transport_inbound.py** - Pipeline inbound avec validation et rejet

- **app/services/emit_on_create.py** - Pipeline outbound avec validation info

### Migrations Base de Données

- **migrations/009_add_pam_validation.sql** - Ajout champs validation
- **apply_migration_009.py** - Script application migration

## Référence Rapide: Codes d'Erreur

### Par Type de Données

| Type | Codes | Sévérité |
|------|-------|----------|
| **CX** | `_CX_ID_EMPTY`, `_CX_SCHEME_MISSING` | error, warn |
| **XPN** | `_XPN_INCOMPLETE`, `_XPN_TYPE_INVALID` | error, warn |
| **XAD** | `_XAD_EMPTY`, `_XAD_TYPE_INVALID` | warn, info |
| **XTN** | `_XTN_EMPTY`, `_XTN_USE_INVALID`, `_XTN_EQUIP_INVALID` | warn, info, info |
| **TS** | `_TS_TOO_SHORT`, `_TS_FORMAT`, `_TS_*_INVALID` | error |
| **PV1** | `PV1_2_INVALID`, `PV1_3_EMPTY`, `PV1_7_XCN_*_INCOMPLETE` | warn |

### Par Sévérité

- **error** - Violation règle requise → rejet possible si mode='reject'
- **warn** - Violation règle recommandée → signalé mais traité
- **info** - Information → aucun impact

## Roadmap Optionnelle

Extensions non nécessaires pour conformité IHE PAM de base:

1. **Types additionnels**: CE, DT, SI, NM
2. **Validation inter-champs**: Cohérence dates, doublons
3. **Extensions régionales**: Tables locales, profils nationaux

## Liens Externes

- [HL7 v2.5 Standard](http://www.hl7.org/implement/standards/product_brief.cfm?product_id=144)
- [IHE PAM Profile](https://www.ihe.net/uploadedFiles/Documents/ITI/IHE_ITI_TF_Vol2a.pdf)
- [HAPI HL7 Library](https://hapifhir.github.io/hapi-hl7v2/)

---

**Dernière mise à jour**: 2024-11-05  
**Version**: 1.0  
**Statut**: ✅ Production Ready
