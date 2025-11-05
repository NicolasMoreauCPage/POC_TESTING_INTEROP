# Intégration des Règles de Validation des Types de Données Complexes HL7 v2.5

## Résumé

Cette mise à jour ajoute la validation approfondie des **types de données complexes HL7 v2.5** au module de validation PAM existant.

## Modifications Apportées

### 1. Module de Validation (`app/services/pam_validation.py`)

Ajout de **7 fonctions de validation** pour les types de données complexes:

- `_validate_cx_identifier()` - Extended Composite ID (CX)
- `_validate_xpn_name()` - Extended Person Name (XPN)
- `_validate_xad_address()` - Extended Address (XAD)
- `_validate_xtn_telecom()` - Extended Telecommunication Number (XTN)
- `_validate_ts_timestamp()` - Time Stamp (TS)
- Validation PL (Person Location) intégrée dans PV1-3
- Validation XCN (Extended Composite ID and Name) intégrée dans PV1-7

### 2. Champs Validés

#### Segment PID (Patient Identification)

| Champ | Type | Répétitions | Validation |
|-------|------|-------------|------------|
| PID-3 | CX | Oui (~) | ID requis, Check Digit Scheme si Check Digit présent |
| PID-5 | XPN | Oui (~) | Family OU Given Name requis, Name Type Code |
| PID-7 | TS | Non | Format YYYY[MM[DD[HH[MM[SS]]]]], valeurs valides |
| PID-11 | XAD | Oui (~) | Au moins un composant d'adresse, Address Type |
| PID-13 | XTN | Oui (~) | Numéro requis, Use Code, Equipment Type |
| PID-14 | XTN | Oui (~) | Numéro requis, Use Code, Equipment Type |

#### Segment EVN (Event Type)

| Champ | Type | Validation |
|-------|------|------------|
| EVN-2 | TS | Format timestamp valide |
| EVN-6 | TS | Format timestamp valide |

#### Segment PV1 (Patient Visit)

| Champ | Type | Validation |
|-------|------|------------|
| PV1-2 | IS | Requis, HL7 Table 0004 (Patient Class) |
| PV1-3 | PL | Au moins un composant de location |
| PV1-7 | XCN | Répétitions (~), ID ou Family Name requis |
| PV1-19 | CX | ID requis |
| PV1-44 | TS | Format timestamp valide |
| PV1-45 | TS | Format timestamp valide |

#### Segment MSH (Message Header)

| Champ | Type | Validation |
|-------|------|------------|
| MSH-7 | TS | Format timestamp valide (déjà existant, amélioré) |

### 3. Tables HL7 Validées

- **Table 0004** (Patient Class): E, I, O, P, R, B, C, N, U
- **Table 0190** (Address Type): B, BA, BDL, BI, BR, C, F, H, L, M, N, O, P, RH, SH, BIR
- **Table 0200** (Name Type Code): A, B, C, D, I, L, M, N, P, R, S, T, U
- **Table 0201** (Telecom Use Code): ASN, BPN, EMR, NET, ORN, PRN, PRS, VHN, WPN
- **Table 0202** (Telecom Equipment Type): BP, CP, FX, Internet, MD, PH, SAT, TDD, TTY, X.400

## Tests

### Suite de Tests (`tools/smoke_test_datatype_validation.py`)

7 scénarios de test couvrant tous les types de données:

1. **Test CX** - ID manquant dans PID-3
2. **Test XPN** - Ni Family ni Given Name dans PID-5
3. **Test XAD/XTN** - Adresse vide et téléphone vide
4. **Test TS** - Timestamps invalides (format et mois)
5. **Test PV1** - Patient Class invalide
6. **Test Complet** - Message valide avec tous les types de données
7. **Test Répétitions** - Erreurs dans répétitions multiples

### Résultats des Tests

```
================================================================================
TESTS DE VALIDATION DES TYPES DE DONNÉES COMPLEXES HL7 v2.5
================================================================================

Test 1: CX - ID manquant dans PID-3
Valid: False, Level: fail
Issues: 1
  [error] PID3[0]_CX_ID_EMPTY
[OK] All expected issues found

Test 2: XPN - Ni Family ni Given Name dans PID-5
Valid: False, Level: fail
Issues: 1
  [error] PID5[0]_XPN_INCOMPLETE
[OK] All expected issues found

Test 3: XAD vide et XTN vide dans PID-11/PID-13
Valid: True, Level: warn
Issues: 2
  [warn] PID11[0]_XAD_EMPTY
  [warn] PID13[0]_XTN_EMPTY
[OK] All expected issues found

Test 4: Timestamps invalides - PID-7 format et PV1-44 mois
Valid: False, Level: fail
Issues: 2
  [error] PID7_TS_FORMAT
  [error] PV1_44_TS_MONTH_INVALID
[OK] All expected issues found

Test 5: PV1 - Patient Class invalide
Valid: True, Level: warn
Issues: 1
  [warn] PV1_2_INVALID
[OK] All expected issues found

Test 6: Message complet VALIDE avec tous les types de données
Valid: True, Level: ok
Issues: 2 (info seulement - codes non standard acceptés)

Test 7: Répétitions - erreurs CX, XPN dans répétitions
Valid: False, Level: fail
Issues: 3
  [error] PID3[0]_CX_ID_EMPTY
  [warn] PID3[0]_CX_SCHEME_MISSING
  [error] PID5[1]_XPN_INCOMPLETE
[OK] All expected issues found

================================================================================
Tests terminés - TOUS LES TESTS PASSENT
================================================================================
```

## Hiérarchie de Validation Complète

Le module PAM valide maintenant sur **4 couches**:

1. **IHE PAM** - Règles métier IHE PAM (ex: segments requis par profil)
2. **HAPI Structures** - Validation structure détaillée par trigger (16 triggers)
3. **HL7 v2.5 Base** - Segments MSH, EVN, PID requis
4. **Types de Données Complexes** ← **NOUVELLE COUCHE**
   - CX (Extended Composite ID)
   - XPN (Extended Person Name)
   - XAD (Extended Address)
   - XTN (Extended Telecommunication)
   - TS (Time Stamp)
   - PL (Person Location)
   - XCN (Extended Composite ID and Name)

## Sévérités des Erreurs

- **error** - Violation de règle requise, message peut être rejeté si mode='reject'
- **warn** - Violation de règle recommandée, message traité mais signalé
- **info** - Information, pas de non-conformité critique

## Utilisation

### Exécuter les Tests

```powershell
python tools/smoke_test_datatype_validation.py
```

### Configuration

Aucune configuration supplémentaire nécessaire. Les validations sont **automatiquement appliquées** à tous les messages PAM.

La configuration existante dans `SystemEndpoint` s'applique:
- `pam_validate_enabled` - Activer/désactiver la validation
- `pam_validate_mode` - "warn" (info) ou "reject" (rejet si fail)
- `pam_profile` - Profil IHE PAM utilisé

### Supervision

Les résultats sont visibles dans l'UI `/messages`:
- Colonne **PAM** avec badges ok/warn/fail
- Détail du message `/messages/{id}` avec liste des issues

## Impact sur les Messages

### Messages Affectés

Tous les messages ADT IHE PAM avec:
- Identifiants patients (PID-3)
- Noms patients (PID-5)
- Dates de naissance (PID-7)
- Adresses patients (PID-11)
- Téléphones patients (PID-13, PID-14)
- Timestamps (MSH-7, EVN-2, EVN-6, PV1-44, PV1-45)
- Informations visite (PV1-2, PV1-3, PV1-7, PV1-19)

### Compatibilité

Les validations sont **strictes mais graduelles**:
- **error** uniquement pour violations graves (ID vide, format invalide)
- **warn** pour recommandations HL7 (champs recommandés manquants)
- **info** pour extensions ou codes non standard (acceptés)

Les messages avec codes non standard sont **acceptés** avec niveau "ok" ou "warn", pas "fail".

## Documentation

### Fichiers Créés

1. **Doc/REGLES_DATATYPES_COMPLEXES_HL7v25.md**
   - Règles détaillées par type de données
   - Formats, codes d'erreur, exemples
   - Tables HL7 validées

2. **Doc/INTEGRATION_DATATYPES_COMPLEXES_RECAP.md** (ce fichier)
   - Résumé de l'intégration
   - Résultats des tests
   - Guide d'utilisation

3. **tools/smoke_test_datatype_validation.py**
   - Suite de tests automatisés
   - 7 scénarios couvrant tous les types

### Documents Existants

Complètent les documents existants:
- Doc/REGLES_VALIDATION_HL7v25.md (règles base)
- Doc/INTEGRATION_HL7v25_RECAP.md (intégration base)
- Doc/HAPI/* (structures HAPI)

## Prochaines Étapes (Optionnel)

### Extensions Possibles

1. **Validation CE (Coded Element)**
   - Codes et systèmes de codage
   - PID-10 (Race), PID-22 (Ethnic Group)

2. **Validation DT (Date)**
   - Format YYYYMMDD strict
   - PID-33 (Last Update Date/Time)

3. **Validation SI/NM (Numeric)**
   - Valeurs numériques strictes
   - PID-18 (Patient Account Number)

4. **Validation supplémentaire des répétitions**
   - Ordre des répétitions
   - Doublons

5. **Validation inter-champs**
   - Cohérence PID-7 (DOB) vs PID-29 (Patient Death Date)
   - Cohérence PV1-44 (Admit) vs PV1-45 (Discharge)

Ces extensions ne sont **pas nécessaires** pour la conformité IHE PAM de base mais peuvent être ajoutées selon les besoins.

## Références

- HL7 v2.5 Standard - Chapter 2A: Data Types
- HL7 v2.5 Standard - Chapter 3: Segments
- IHE Patient Administration Management (PAM) Profile
- HAPI Structures (Doc/HAPI/)
- Doc/HL7v2.5/CH02A.pdf
- Doc/HL7v2.5/Ch03.pdf

---

**Date**: 2024-11-05  
**Version**: 1.0  
**Statut**: ✅ Tests passent, Production ready
