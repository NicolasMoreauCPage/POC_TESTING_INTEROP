# Validation de l'Ordre des Segments HL7 v2.5

## Vue d'ensemble

Cette validation vérifie que les segments d'un message HL7 v2.5 apparaissent dans l'**ordre correct** selon les structures HAPI définies pour chaque trigger ADT.

## Principe

Chaque trigger ADT (A01, A03, A04, etc.) a une **structure définie** dans HAPI qui spécifie l'ordre attendu des segments. Par exemple, pour ADT^A01:

```
1. MSH (Message Header)
2. SFT (Software Segment) - optionnel
3. EVN (Event Type)
4. PID (Patient Identification)
5. PD1 (Patient Additional Demographic) - optionnel
6. NK1 (Next of Kin) - optionnel
7. PV1 (Patient Visit)
8. PV2 (Patient Visit Additional) - optionnel
9. ZBE (Mouvement) - optionnel
10. ZFP, ZFV, ZFM... (segments Z français) - optionnels
...
```

## Règles de Validation

### Règle Générale

**Les segments présents dans le message doivent apparaître dans l'ordre défini par la structure HAPI.**

Si un segment A doit venir avant un segment B dans la structure, et qu'ils sont tous deux présents dans le message, alors A doit apparaître physiquement avant B dans le message.

### Segments Ignorés

- Les segments **non définis** dans la structure attendue sont ignorés (pas d'erreur)
- Les segments **optionnels absents** ne génèrent pas d'erreur d'ordre
- Seuls les segments **présents ET définis** dans la structure sont vérifiés

### Sévérité

- **warn** - Violation de l'ordre des segments
  - Le message est traité mais signalé
  - Peut indiquer un problème d'implémentation chez l'émetteur

## Triggers Supportés

18 triggers ADT ont leur ordre défini:

- **A01** - Admission
- **A03** - Discharge
- **A04** - Register patient
- **A05** - Pre-admission
- **A06** - Change outpatient to inpatient
- **A07** - Change inpatient to outpatient
- **A08** - Update patient information
- **A11** - Cancel admission
- **A12** - Cancel transfer
- **A13** - Cancel discharge
- **A21** - Leave of absence
- **A22** - Return from leave of absence
- **A23** - Delete patient record
- **A28** - Add person information
- **A31** - Update person information
- **A40** - Merge patient
- **A47** - Change patient identifier
- **A52** - Cancel leave of absence
- **A53** - Cancel return from leave of absence

## Exemples

### Exemple 1: Ordre Correct ✓

```hl7
MSH|^~\&|APP|FAC|...|20240101120000||ADT^A01|MSG001|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^HOSP||DOE^JOHN||19800101
PV1|1|I|WARD^101^A|||DOC123^SMITH^JANE
PV2|1|||||...
ZBE|MOVEMENT|UF001|SERVICE001
```

**Résultat**: Aucune erreur d'ordre

### Exemple 2: PID et PV1 Inversés ✗

```hl7
MSH|^~\&|APP|FAC|...|20240101120000||ADT^A01|MSG001|P|2.5
EVN|A01|20240101120000
PV1|1|I|WARD^101^A|||DOC123^SMITH^JANE
PID|1||123456^^^HOSP||DOE^JOHN||19800101
```

**Résultat**:
```
[warn] SEGMENT_ORDER_PID: Segment PID at line 4 should appear before PV1 (line 3) according to HAPI A01 structure
```

**Explication**: PID doit venir AVANT PV1 dans la structure A01.

### Exemple 3: ZBE Avant PV1 ✗

```hl7
MSH|^~\&|APP|FAC|...|20240101120000||ADT^A01|MSG001|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^HOSP||DOE^JOHN||19800101
ZBE|MOVEMENT|UF001|SERVICE001
PV1|1|I|WARD^101^A|||DOC123^SMITH^JANE
PV2|1|||||...
```

**Résultat**:
```
[warn] SEGMENT_ORDER_PV1: Segment PV1 at line 5 should appear before ZBE (line 4) according to HAPI A01 structure
```

**Explication**: Dans A01, PV1 doit venir AVANT ZBE (qui est après PV2).

### Exemple 4: Segments Optionnels Omis (Correct) ✓

```hl7
MSH|^~\&|APP|FAC|...|20240101120000||ADT^A01|MSG001|P|2.5
EVN|A01|20240101120000
PID|1||123456^^^HOSP||DOE^JOHN||19800101
PV1|1|I|WARD^101^A|||DOC123^SMITH^JANE
ZBE|MOVEMENT|UF001|SERVICE001
```

**Résultat**: Aucune erreur d'ordre

**Explication**: PV2 est optionnel, son absence ne cause pas d'erreur. L'ordre MSH→EVN→PID→PV1→ZBE est respecté.

## Codes d'Erreur

### Format

`SEGMENT_ORDER_{SEGMENT_NAME}`

### Exemples

- `SEGMENT_ORDER_PID` - Le segment PID est mal placé
- `SEGMENT_ORDER_PV1` - Le segment PV1 est mal placé
- `SEGMENT_ORDER_ZBE` - Le segment ZBE est mal placé

### Message d'Erreur

```
Segment {X} at line {N} should appear before {Y} (line {M}) according to HAPI {trigger} structure
```

Où:
- `{X}` = segment mal placé
- `{N}` = numéro de ligne du segment mal placé
- `{Y}` = segment qui devrait venir après
- `{M}` = numéro de ligne du segment qui devrait venir après
- `{trigger}` = code du trigger (A01, A03, etc.)

## Intégration

### Activation

La validation de l'ordre des segments est **automatiquement activée** pour tous les messages PAM validés avec un trigger supporté.

Aucune configuration supplémentaire n'est nécessaire.

### Position dans la Hiérarchie

Cette validation fait partie de la **Couche 2: HAPI Structures**:

```
1. IHE PAM (règles métier)
2. HAPI Structures ← Validation ordre des segments ICI
   - Présence/absence segments
   - Ordre des segments ← NOUVEAU
3. HL7 v2.5 Base (segments requis)
4. Types de Données Complexes (CX, XPN, etc.)
```

### Impact

- **Sévérité**: warn (pas de rejet automatique)
- **Traitement**: Le message est traité normalement
- **Signalement**: L'erreur est visible dans la supervision

## Test

### Exécuter le Test

```powershell
python tools/test_segment_order.py
```

### Scénarios de Test

Le test couvre 4 scénarios:

1. **Ordre correct** (A01) - MSH, EVN, PID, PV1, PV2, ZBE
2. **PID/PV1 inversés** (A01) - Détecte l'inversion
3. **ZBE mal placé** (A01) - ZBE avant PV1/PV2
4. **A28 correct** - Message identity-only

### Résultats Attendus

```
Test 1 (ordre correct): 0 issues ordre (OK)
Test 2 (PID/PV1 inversés): 1 issue ordre (détecté)
Test 3 (ZBE mal placé): 1 issue ordre (détecté)
Test 4 (A28 correct): 0 issues ordre (OK)
```

## Limitations

### Segments Répétables

La validation vérifie l'ordre de la **première occurrence** de chaque segment. Pour les segments répétables (NK1, OBX, DG1, etc.), seule la position de la première occurrence est validée.

### Groupes de Segments

Les groupes de segments HAPI (INSURANCE, PROCEDURE, etc.) ne sont pas encore validés au niveau groupe. Seuls les segments individuels sont vérifiés.

### Segments Inconnus

Les segments non définis dans `SEGMENT_ORDER` pour le trigger sont **ignorés** sans erreur. Cela permet de tolérer des segments propriétaires ou des extensions.

## Évolutions Futures (Optionnel)

1. **Validation des répétitions**
   - Vérifier l'ordre des occurrences multiples d'un même segment

2. **Validation des groupes**
   - Vérifier que les groupes de segments (ex: INSURANCE) sont complets et ordonnés

3. **Sévérité configurable**
   - Permettre de passer de "warn" à "error" selon les besoins

4. **Segments propriétaires**
   - Ajouter des règles d'ordre pour segments Z* personnalisés

## Références

- **Code**: `app/services/pam_validation.py` - `_validate_segment_order()`
- **Structures HAPI**: `Doc/HAPI/hapi/custom/message/ADT_*.java`
- **Dictionnaire ordre**: `SEGMENT_ORDER` dans `pam_validation.py`
- **Tests**: `tools/test_segment_order.py`

---

**Date**: 2024-11-05  
**Version**: 1.0  
**Statut**: ✅ Implémenté et testé
