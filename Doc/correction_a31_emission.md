# Correction A31 - Émission automatique Patient Update

**Date** : 3 novembre 2025  
**Contexte** : Correction formulaire Patient + émission A31

---

## 🔴 Problème découvert

Lors de la correction du formulaire Patient pour conformité RGPD, nous avons découvert que :

❌ **A31 (Update person information) ne générait AUCUN message sortant**

```
Test IHE PAM AVANT correction :
A31 | Update person | Reçu: 8 | Émis: 0 | ⚠️ Pas d'émission
Résumé: 17/18 types OK (94%)
```

---

## 🔍 Analyse de la cause

### Chaîne d'émission

```
┌──────────────────┐
│  Patient modifié │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────┐
│ entity_events.py                 │
│ after_update listener            │
│ _schedule_emission(              │
│   session, entity, type,         │
│   operation="update" ✅          │  ← operation capturé
│ )                                │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ after_commit                     │
│ _emit_in_new_session(            │
│   entity_class, id, type         │  ← operation PERDU ❌
│ )                                │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ emit_to_senders_async(           │
│   entity, type, session          │  ← operation manquant ❌
│ )                                │
└────────┬─────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ generate_pam_hl7(                │
│   entity, type, session          │  ← operation manquant ❌
│ )                                │
│                                  │
│ TOUJOURS génère A04 ❌           │
└──────────────────────────────────┘
```

**Cause** : Le paramètre `operation` n'était pas propagé à travers toute la chaîne.

---

## ✅ Solution implémentée

### 1. Propagation du paramètre `operation`

**Fichier** : `app/services/entity_events.py`

```python
# AVANT
loop.create_task(_emit_in_new_session(entity_class, entity_id, entity_type))

# APRÈS
loop.create_task(_emit_in_new_session(entity_class, entity_id, entity_type, operation))
```

```python
# AVANT
async def _emit_in_new_session(entity_class, entity_id, entity_type):
    await emit_to_senders_async(entity, entity_type, emit_session)

# APRÈS  
async def _emit_in_new_session(entity_class, entity_id, entity_type, operation):
    await emit_to_senders_async(entity, entity_type, emit_session, operation)
```

### 2. Signature `emit_to_senders_async`

**Fichier** : `app/services/emit_on_create.py`

```python
# AVANT
async def emit_to_senders_async(entity, entity_type, session):
    hl7_message = generate_pam_hl7(entity, entity_type, session)

# APRÈS
async def emit_to_senders_async(entity, entity_type, session, operation="insert"):
    hl7_message = generate_pam_hl7(entity, entity_type, session, operation=operation)
```

### 3. Génération conditionnelle dans `generate_pam_hl7`

**Fichier** : `app/services/emit_on_create.py`

```python
# AVANT
if entity_type == "patient":
    # ADT^A04 (Register patient) - new patient created
    event_type = "A04"  # TOUJOURS A04 ❌

# APRÈS
if entity_type == "patient":
    # Déterminer event type based on operation
    if operation == "update":
        event_type = "A31"  # ADT^A31 (Update person information) ✅
    else:
        event_type = "A04"  # ADT^A04 (Register patient) ✅
```

---

## 🧪 Validation

### Test après correction

```bash
python3 tools/test_ihe_pam_complete.py
```

**Résultat** :
```
📊 RÉSULTATS PAR TYPE:
A31 | Update person | Reçu: 8 | Émis: 14 | ✅ OK

📈 Résumé: 18/18 types OK (100%) 🎉🎉🎉
```

### Matrice des événements Patient

| Opération | Type HL7 | Description |
|-----------|----------|-------------|
| INSERT (nouveau) | **ADT^A04** | Register patient |
| UPDATE (existant) | **ADT^A31** | Update person information |

---

## 📝 Modifications complémentaires

### Suppression des appels manuels obsolètes

**Fichier** : `app/routers/patients.py`

```python
# AVANT
session.add(patient)
session.commit()
emit_to_senders(patient, "patient", session)  # ❌ Appel manuel

# APRÈS
session.add(patient)
session.commit()
# ✅ Émission automatique via entity_events.py (after_insert/after_update)
```

**Avantages** :
- Plus de code dupliqué
- Garantie que tous les changements sont émis
- Gestion centralisée

---

## 🎯 Impact

### Avant
- ✅ A04 émis pour nouveaux patients
- ❌ **AUCUN message** pour mises à jour patients
- ⚠️ 17/18 types IHE PAM OK (94%)

### Après
- ✅ A04 émis pour nouveaux patients
- ✅ **A31 émis** pour mises à jour patients
- ✅ 18/18 types IHE PAM OK (100%)

---

## 📚 Fichiers modifiés

1. `app/services/entity_events.py` (lignes 104, 111-135)
   - Ajout paramètre `operation` à `_emit_in_new_session()`
   - Propagation vers `emit_to_senders_async()`

2. `app/services/emit_on_create.py` (lignes 13-50, 252-268)
   - Ajout paramètre `operation` à `emit_to_senders_async()`
   - Ajout paramètre `operation` à `generate_pam_hl7()`
   - Génération conditionnelle A04/A31 pour Patient

3. `app/routers/patients.py` (lignes 150-220)
   - Suppression appels manuels `emit_to_senders()`
   - Ajout commentaires explicatifs

---

## ✅ Conclusion

L'émission automatique de messages A31 fonctionne maintenant correctement.

**Tous les types IHE PAM sont à 100%** :
- ✅ 18/18 types conformes
- ✅ A04 pour nouveaux patients
- ✅ A31 pour mises à jour patients
- ✅ Émission complètement automatique

---

**Validé le** : 3 novembre 2025  
**Test de non-régression** : ✅ Réussi (18/18)
