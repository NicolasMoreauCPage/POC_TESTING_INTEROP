# 03 - IHE PAM

Documentation sur le profil IHE Patient Administration Management et ses extensions françaises.

## Documents

### [conformite_zbe.md](conformite_zbe.md)
Conformité du segment ZBE (extension CPage/IHE PAM France).

**Contenu** :
- Structure du segment ZBE
- ZBE-1 : Identifiant du mouvement
- ZBE-2 : Date/heure du mouvement
- ZBE-6 : Type d'événement original (pour Z99)
- ZBE-9 : Mode de traitement (valeur "C" pour corrections)

**Règle importante** :
- ZBE-9="C" autorisé uniquement dans Z99 sur A01/A04/A05
- Venue doit être en état "planned" (préadmission) ou "active" (admission)

### [namespaces_mouvement_finess.md](namespaces_mouvement_finess.md)
Configuration des namespaces MOUVEMENT et FINESS pour identifiants.

**Contenu** :
- Namespace MOUVEMENT (ZBE-1)
- Namespace FINESS (établissements)
- Format CX : `valeur^^^namespace^type`
- Configuration dans `IdentifierNamespace`

## Profil IHE PAM

Le profil IHE PAM définit les messages ADT pour la gestion administrative des patients :

### Événements Principaux

| Événement | Description | Segments |
|-----------|-------------|----------|
| A01 | Admission | MSH, EVN, PID, PV1, ZBE |
| A02 | Transfert | MSH, EVN, PID, PV1, ZBE |
| A03 | Sortie | MSH, EVN, PID, PV1, ZBE |
| A04 | Inscription externe | MSH, EVN, PID, PV1, ZBE |
| A05 | Pré-admission | MSH, EVN, PID, PV1, ZBE |
| Z99 | Modification (CPage) | MSH, EVN, PID, PV1, ZBE |

### Extensions Françaises (CPage)

- Segment **ZBE** : Données administratives françaises
- Segment **ZFP** : Fusion de patients
- Segment **ZFV** : Fusion de venues
- Message **Z99** : Modifications sans créer de mouvement

## Références

- Spécifications IHE PAM : `Doc/SpecIHEPAM/`
- Extensions CPage : `Doc/SpecIHEPAM_CPage/`
- Format ZBE : `Doc/SpecIHEPAM_CPage/INT_CPAGE_FORMAT_IHE_PAM_2.11.txt`

---

[← Retour à l'index](../INDEX.md)
