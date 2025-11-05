# Règles de Validation des Types de Données Complexes HL7 v2.5

## Vue d'ensemble

Ce document décrit les règles de validation implémentées pour les types de données complexes HL7 v2.5 dans le module PAM.

## Types de Données Validés

### 1. CX - Extended Composite ID with Check Digit

**Format**: `ID^CheckDigit^CheckDigitScheme^AssigningAuthority^IdentifierTypeCode^AssigningFacility`

**Règles**:
- Le composant ID (1er composant) est **requis** et ne doit pas être vide
- Si un Check Digit est présent (2ème composant), alors le Check Digit Scheme (3ème composant) est **recommandé**

**Champs utilisant CX**:
- PID-3 (Patient Identifier List) - avec répétitions séparées par `~`
- PV1-19 (Visit Number)

**Codes d'erreur**:
- `{FIELD}_CX_ID_EMPTY` (error): Le composant ID est vide
- `{FIELD}_CX_SCHEME_MISSING` (warn): Check Digit présent mais Scheme manquant

---

### 2. XPN - Extended Person Name

**Format**: `FamilyName^GivenName^MiddleName^Suffix^Prefix^Degree^NameTypeCode^...`

**Règles**:
- Au minimum **Family Name OU Given Name** doit être présent
- Le Name Type Code (7ème composant) doit être dans HL7 Table 0200 si présent:
  - Valeurs: A, B, C, D, I, L, M, N, P, R, S, T, U

**Champs utilisant XPN**:
- PID-5 (Patient Name) - avec répétitions séparées par `~`

**Codes d'erreur**:
- `{FIELD}_XPN_INCOMPLETE` (error): Ni Family ni Given Name présent
- `{FIELD}_XPN_TYPE_INVALID` (warn): Name Type Code invalide

---

### 3. XAD - Extended Address

**Format**: `StreetAddress^OtherDesignation^City^State^Zip^Country^AddressType^...`

**Règles**:
- Au moins un des 6 premiers composants d'adresse doit être présent
- Le Address Type (7ème composant) doit être dans HL7 Table 0190 si présent:
  - Valeurs standard: B, BA, BDL, BI, BR, C, F, H, L, M, N, O, P, RH, SH, BIR

**Champs utilisant XAD**:
- PID-11 (Patient Address) - avec répétitions séparées par `~`

**Codes d'erreur**:
- `{FIELD}_XAD_EMPTY` (warn): Aucun composant d'adresse présent
- `{FIELD}_XAD_TYPE_INVALID` (info): Address Type non standard

---

### 4. XTN - Extended Telecommunication Number

**Format**: `[CountryCode]^TelephoneNumber^TelecommunicationUseCode^TelecommunicationEquipmentType^...`

**Règles**:
- Le numéro de téléphone (1er ou 2ème composant) est **requis**
- Le Use Code (3ème composant) doit être dans HL7 Table 0201 si présent:
  - Valeurs: ASN, BPN, EMR, NET, ORN, PRN, PRS, VHN, WPN
- Le Equipment Type (4ème composant) doit être dans HL7 Table 0202 si présent:
  - Valeurs: BP, CP, FX, Internet, MD, PH, SAT, TDD, TTY, X.400

**Champs utilisant XTN**:
- PID-13 (Phone Number - Home) - avec répétitions séparées par `~`
- PID-14 (Phone Number - Business) - avec répétitions séparées par `~`

**Codes d'erreur**:
- `{FIELD}_XTN_EMPTY` (warn): Aucun numéro de téléphone présent
- `{FIELD}_XTN_USE_INVALID` (info): Use Code invalide
- `{FIELD}_XTN_EQUIP_INVALID` (info): Equipment Type invalide

---

### 5. TS - Time Stamp

**Format**: `YYYY[MM[DD[HH[MM[SS[.S[S[S[S]]]]]]]]][+/-ZZZZ]`

**Règles**:
- Minimum **YYYY** (4 caractères) requis
- Format strict numérique (sauf timezone et fractions)
- Validation des valeurs:
  - Mois: 01-12
  - Jour: 01-31
  - Heure: 00-23
  - Minute: 00-59
  - Seconde: 00-59

**Champs utilisant TS**:
- MSH-7 (Date/Time of Message)
- EVN-2 (Recorded Date/Time)
- EVN-6 (Event Occurred)
- PID-7 (Date of Birth)
- PV1-44 (Admit Date/Time)
- PV1-45 (Discharge Date/Time)

**Codes d'erreur**:
- `{FIELD}_TS_TOO_SHORT` (error): Moins de 4 caractères
- `{FIELD}_TS_FORMAT` (error): Format non numérique
- `{FIELD}_TS_MONTH_INVALID` (error): Mois invalide
- `{FIELD}_TS_DAY_INVALID` (error): Jour invalide
- `{FIELD}_TS_HOUR_INVALID` (error): Heure invalide
- `{FIELD}_TS_MINUTE_INVALID` (error): Minute invalide
- `{FIELD}_TS_SECOND_INVALID` (error): Seconde invalide

---

### 6. PL - Person Location (PV1-3)

**Format**: `PointOfCare^Room^Bed^Facility^LocationStatus^PersonLocationType^Building^Floor`

**Règles**:
- Au moins un des 4 premiers composants (PointOfCare, Room, Bed, Facility) devrait être présent

**Codes d'erreur**:
- `PV1_3_EMPTY` (warn): Aucun composant de location présent

---

### 7. XCN - Extended Composite ID Number and Name (PV1-7)

**Format**: `ID^FamilyName^GivenName^MiddleName^Suffix^Prefix^Degree^SourceTable^AssigningAuthority^NameTypeCode^...`

**Règles**:
- Au minimum **ID OU Family Name** doit être présent

**Champs utilisant XCN**:
- PV1-7 (Attending Doctor) - avec répétitions séparées par `~`

**Codes d'erreur**:
- `{FIELD}_XCN_{idx}_INCOMPLETE` (warn): Ni ID ni Family Name présent

---

## Validation PV1 Additionnelle

### PV1-2 (Patient Class)

**Règles**:
- Champ **requis**
- Doit être dans HL7 Table 0004:
  - Valeurs: E (Emergency), I (Inpatient), O (Outpatient), P (Preadmit), R (Recurring), B (Obstetrics), C (Commercial), N (Not Applicable), U (Unknown)

**Codes d'erreur**:
- `PV1_2_MISSING` (error): PV1-2 manquant
- `PV1_2_INVALID` (warn): Valeur non dans Table 0004

---

## Répétitions

Certains champs acceptent des **répétitions** séparées par le caractère `~`:
- PID-3 (Patient Identifier List)
- PID-5 (Patient Name)
- PID-11 (Patient Address)
- PID-13 (Phone Number - Home)
- PID-14 (Phone Number - Business)
- PV1-7 (Attending Doctor)

Chaque répétition est validée **individuellement**, avec un index `[0]`, `[1]`, etc. dans le code d'erreur.

---

## Exemples

### Exemple valide complet

```
MSH|^~\&|SENDING|FACILITY|RECEIVING|DEST|20240101120000||ADT^A01^ADT_A01|MSG123|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^HOSP^PI||DOE^JOHN^MIDDLE^JR^DR||19800101|M||||||123 Main St^Apt 5^Paris^^75001^FRA^H~456 Oak Ave^^Lyon^^69001^FRA^B||(33)123456789^^PRN^PH~0601020304^^ORN^CP
PV1|1|I|SERVICE^101^A^HOSPITAL|||DOC123^SMITH^JANE^L^DR||||||||||||V123456^^^HOSP||||||||||||||||||||||||20240101100000
```

### Exemples d'erreurs

#### CX ID vide
```
PID|1||^1234567^M10^HOSP||DOE^JOHN||19800101
```
→ `PID3[0]_CX_ID_EMPTY`: Le composant ID est vide

#### XPN incomplet
```
PID|1||123456^^^HOSP||^^MIDDLE||19800101
```
→ `PID5[0]_XPN_INCOMPLETE`: Ni Family ni Given Name présent

#### TS format invalide
```
PID|1||123456^^^HOSP||DOE^JOHN||198013XX
```
→ `PID7_TS_FORMAT`: Format invalide (XX non numérique)

#### XAD vide
```
PID|1||123456^^^HOSP||DOE^JOHN||19800101|||||^^^^^
```
→ `PID11[0]_XAD_EMPTY`: Aucun composant d'adresse

---

## Intégration

Ces validations sont **intégrées automatiquement** dans le module `app/services/pam_validation.py` et s'appliquent à tous les messages PAM validés.

### Hiérarchie de Validation

1. **IHE PAM** (règles métier IHE)
2. **HAPI Structures** (présence/absence segments)
3. **HL7 v2.5 Base** (segments requis MSH, EVN, PID)
4. **Types de Données Complexes** (cette couche) ← **NOUVELLE**

### Test

Exécuter les tests de validation:

```powershell
python tools/smoke_test_datatype_validation.py
```

---

## Références

- HL7 v2.5 Standard - Chapter 2A (Data Types)
- HL7 v2.5 Standard - Chapter 3 (Segments)
- Doc/HL7v2.5/CH02A.pdf
- Doc/HL7v2.5/Ch03.pdf
