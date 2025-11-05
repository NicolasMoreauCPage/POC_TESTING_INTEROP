# 02 - Validation HL7 v2.5 & IHE PAM

Documentation complète sur la validation des messages HL7 v2.5 selon le profil IHE PAM.

## Documents Principaux

### 📋 [INDEX_VALIDATION_PAM.md](INDEX_VALIDATION_PAM.md) - **COMMENCER ICI**
Vue d'ensemble complète du système de validation multi-couches.

**Contenu** :
- Architecture de validation (4 couches)
- Utilisation de la fonction `validate_pam()`
- Exemples de messages valides et invalides
- Guide de débogage

### 📊 [RESUME_VALIDATION_DATATYPES.md](RESUME_VALIDATION_DATATYPES.md)
Résumé de l'implémentation de validation des types de données complexes.

### 📖 [REGLES_VALIDATION_HL7v25.md](REGLES_VALIDATION_HL7v25.md)
Règles de validation HL7 v2.5 standard (MSH, EVN, PID, PV1).

### 🔍 [REGLES_DATATYPES_COMPLEXES_HL7v25.md](REGLES_DATATYPES_COMPLEXES_HL7v25.md)
Règles détaillées pour les types CX, XPN, XAD, XTN, TS, DT.

### 🔢 [VALIDATION_ORDRE_SEGMENTS.md](VALIDATION_ORDRE_SEGMENTS.md)
Validation de l'ordre des segments selon structures HAPI.

## Hiérarchie de Validation

```
1. Règles IHE PAM (priorité maximale)
   └─ Profil d'intégration français
   └─ Segments Z (ZBE, ZFP, ZFV, etc.)
   
2. Structures HAPI/CPage
   └─ Extensions locales
   └─ Messages ADT_A01, MFN_M02, etc.
   
3. Règles HL7 v2.5 Base
   └─ Standard international
   └─ MSH, EVN, PID, PV1, PV2, etc.
   
4. Validation datatypes
   └─ CX (Extended Composite ID)
   └─ XPN (Extended Person Name)
   └─ XAD (Extended Address)
   └─ XTN (Extended Telecommunication)
   └─ TS (Time Stamp)
   └─ DT (Date)
```

## Utilisation

### Interface Web
Accessible via : **[/validation](http://127.0.0.1:8000/validation)**

### API Programmatique

```python
from app.services.pam_validation import validate_pam

# Valider un message
result = validate_pam(hl7_message, direction="in", profile="IHE_PAM_FR")

# Consulter les résultats
print(f"Niveau: {result.level}")  # ok, warn, fail
for issue in result.issues:
    print(f"{issue.severity}: {issue.code} - {issue.message}")
```

## Couverture

| Aspect | Statut |
|--------|--------|
| MSH (Message Header) | ✅ Complet |
| EVN (Event Type) | ✅ Complet |
| PID (Patient Identification) | ✅ Complet |
| PV1 (Patient Visit) | ✅ Complet |
| Segments Z | ✅ Complet |
| Ordre des segments | ✅ Complet |
| Types complexes | ✅ Complet |

## Références

- Spécifications HL7 v2.5 : `Doc/HL7v2.5/`
- Structures HAPI : `Doc/HAPI/`
- Spécifications IHE PAM : `Doc/SpecIHEPAM/` et `Doc/SpecIHEPAM_CPage/`

---

[← Retour à l'index](../INDEX.md)
