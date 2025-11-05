# Résumé de l'intégration des règles HL7 v2.5

## Modifications apportées

### 1. Validateur PAM enrichi (`app/services/pam_validation.py`)

**Règles HL7 v2.5 ajoutées:**

#### Segment MSH
- MSH-1 : Field Separator doit être `|` (error si incorrect)
- MSH-2 : Encoding Characters standard `^~\&` (warn si différent)
- MSH-9 : Format `type^trigger[^structure]` requis (error)
- MSH-10 : Message Control ID non vide (error)
- MSH-11 : Processing ID valide (P, D, T) (warn)
- MSH-12 : Version ID recommandé (info)

#### Segment PID
- PID-3 : Patient Identifier List non vide (error) - HL7 + IHE PAM
- PID-5 : Patient Name fortement recommandé (warn)
- PID-7 : Date of Birth format YYYYMMDD[HHMM[SS]] si présent (warn)

#### Cohérence
- EVN-1 cohérent avec MSH-9 trigger (warn si différent)

### 2. Documentation (`Doc/REGLES_VALIDATION_HL7v25.md`)

Tableau récapitulatif des règles implémentées avec:
- Champ concerné
- Règle de validation
- Sévérité (error/warn/info)
- Code d'issue généré

Liste des règles HL7 v2.5 **non implémentées** (référence pour extensions futures):
- Cardinalité avancée (répétitions, groupes conditionnels)
- Types de données complexes (CE, CX, XPN, XAD, XTN, TS...)
- Tables de codes HL7 complètes
- Longueurs maximales de champs

### 3. Tests (`tools/smoke_test_pam_validation.py`)

4 scénarios de test:
1. **A04 sans PV1**: Validation IHE PAM (PV1 requis)
2. **A01 complet**: Segments optionnels présents (info)
3. **A28 identité**: Message valide traité avec succès
4. **Violations HL7 v2.5**: MSH-11 invalide, EVN incohérent, PID-3 vide, PID-7 format

## Résultats des tests

```
=== Test: HL7 v2.5 violations ===
Status: processed, PAM: fail
Issues count: 4
  [warn] MSH11_INVALID: MSH-11 (Processing ID) 'X' not in (P, D, T)
  [info] MSH12_MISSING: MSH-12 (Version ID) is recommended
  [warn] EVN_MISMATCH: EVN-1 (A99) differs from MSH-9 trigger (A01)
  [error] PID3_EMPTY: PID-3 (Patient Identifier List) must not be empty
```

## Hiérarchie de validation

1. **IHE PAM** (prédominant): Structures de messages, segments requis par trigger
2. **HAPI/CPage**: Extensions locales (segments Z, groupes personnalisés)
3. **HL7 v2.5 base**: Règles générales de structure et format

## Activation du rejet automatique

Pour rejeter les messages invalides (AE/AR ACK):
1. Aller dans `/sqladmin` → SystemEndpoint
2. Configurer l'endpoint receiver:
   - `pam_validate_enabled` = True
   - `pam_validate_mode` = "reject"
   - `pam_profile` = "IHE_PAM_FR"

Les messages avec `pam_validation_status='fail'` seront rejetés avec ACK AE contenant le premier message d'erreur.

## Consultation des résultats

- **Liste des messages** (`/messages`): Colonne PAM avec badges ok/warn/fail
- **Détail d'un message** (`/messages/{id}`): Badge validation + JSON des issues
- **Vue rejets** (`/messages/rejections`): Groupement par endpoint/IPP/dossier

## Références

- **Doc/HL7v2.5/CH02A.pdf**: Segments et types de données HL7 v2.5
- **Doc/HL7v2.5/Ch03.pdf**: Messages ADT et contrôle
- **Doc/HAPI/hapi/custom/message/**: Structures HAPI/CPage
- **Doc/SpecIHEPAM/**: Profil IHE PAM France

Pour une conformité HL7 v2.5 stricte, consulter les PDFs et utiliser un parseur certifié avec validation complète activée.
