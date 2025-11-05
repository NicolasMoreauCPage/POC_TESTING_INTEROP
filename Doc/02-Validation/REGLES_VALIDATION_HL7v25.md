# Règles HL7 v2.5 implémentées dans le validateur PAM

Ce document récapitule les règles HL7 v2.5 standard intégrées dans `app/services/pam_validation.py`.

## Sources
- **Doc/HL7v2.5/CH02A.pdf** : Chapitres sur les segments et types de données
- **Doc/HL7v2.5/Ch03.pdf** : Messages de contrôle et ADT
- **Doc/HAPI/hapi/custom/message/** : Structures HAPI/CPage (extensions locales)
- **Doc/SpecIHEPAM/** : Profil IHE PAM (prédominant)

## Hiérarchie des règles
1. **IHE PAM** : Profil d'intégration (prédominant)
2. **HAPI/CPage** : Extensions locales (segments Z, groupes personnalisés)
3. **HL7 v2.5 base** : Standard HL7 (règles générales)

## Règles HL7 v2.5 implémentées

### Segment MSH (Message Header)
| Champ | Règle | Sévérité | Code issue |
|-------|-------|----------|------------|
| MSH-1 | Field Separator = `\|` | error | MSH1_INVALID |
| MSH-2 | Encoding Characters = `^~\\&` (standard) | warn | MSH2_NONSTANDARD |
| MSH-9 | Format `type^trigger[^structure]` | error | MSH9_FORMAT |
| MSH-10 | Message Control ID non vide | error | MSH10_EMPTY |
| MSH-11 | Processing ID ∈ {P, D, T} | warn | MSH11_INVALID |
| MSH-12 | Version ID présent | info | MSH12_MISSING |

### Segment EVN (Event Type)
| Champ | Règle | Sévérité | Code issue |
|-------|-------|----------|------------|
| EVN-1 | Event Type Code cohérent avec MSH-9 | warn | EVN_MISMATCH |

### Segment PID (Patient Identification)
| Champ | Règle | Sévérité | Code issue |
|-------|-------|----------|------------|
| PID-3 | Patient Identifier List non vide | error | PID3_EMPTY |
| PID-5 | Patient Name présent | warn | PID5_MISSING |
| PID-7 | Date of Birth format YYYYMMDD[HHMM[SS]] | warn | PID7_FORMAT |

### Segment PV1 (Patient Visit)
| Règle | Condition | Sévérité | Code issue |
|-------|-----------|----------|------------|
| PV1 requis | Triggers A01, A03, A04, A05, A06, A08, A11, A12, A13, A21, A22, A23, A52, A53 | error | PV1_MISSING |
| PV1 optionnel | Triggers A28, A31, A40, A47 (identité) | - | - |

## Règles non implémentées (référence)

Les règles suivantes sont documentées dans CH02A.pdf et Ch03.pdf mais non implémentées dans ce validateur léger:

### Règles de cardinalité avancées
- Répétitions de segments (ex. NK1, OBX, AL1...)
- Groupes optionnels conditionnels
- Ordre exact des segments dans les groupes

### Règles de types de données
- Validation stricte des types CE, CX, XPN, XAD, XTN, TS, etc.
- Longueur maximale des champs
- Tables de codes HL7 (ex. Table 0001 pour MSH-11)

### Règles de conformité stricte
- Utilisation de segments dans les structures non prévues
- Validation des composants et sous-composants
- Échappement des caractères spéciaux

## Utilisation

Pour une conformité complète HL7 v2.5, consulter les documents PDF et utiliser un parseur certifié (ex. HAPI avec validation stricte activée).

Ce validateur se concentre sur les contrôles essentiels pour l'intégration IHE PAM.
