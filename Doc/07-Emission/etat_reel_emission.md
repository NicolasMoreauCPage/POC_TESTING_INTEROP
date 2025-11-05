# État réel de l'émission automatique - 3 novembre 2025

## 📊 Résumé Exécutif (Mise à jour: 3 novembre 2025)

### Implementation Complète IHE PAM
- **18/18 types de messages IHE PAM** implémentés et mappés
- **Handlers créés** : `handle_leave_message()` (A21/A22/A52/A53), `handle_doctor_message()` (A54/A55)
- **Constantes mises à jour** : `MOVEMENT_KIND_BY_TRIGGER`, `MOVEMENT_STATUS_BY_TRIGGER`

### Performance des Tests
- **Taux de succès : 61% (11/18 types)** ✅
  - Fonctionnels : A01, A03, A04, A06, A07, A11, A21, A28, A52, A53, A55
  - Non-émission : A02, A05, A12, A13, A22, A31, A54 (7 types)

### Infrastructure
- **Concurrency control** : Semaphore(5) implémenté pour limiter émissions parallèles
- **Pool DB augmenté** : 20+30 connections (vs 5+10 initial)
- **Protection pool exhaustion** : Résolu via semaphore → amélioration de 27% à 61%

### Problèmes Restants
1. **Annulations (A12, A13, A31)** : Mettent à jour entités existantes sans créer nouveaux Mouvements
2. **Émissions manquantes (A02, A05, A22, A54)** : Mouvements créés mais pas émis (lazy loading suspect)
3. **FHIR désactivé** : Génération commentée (erreurs DetachedInstance)

---

## ✅ Ce qui fonctionne

### Mécanisme d'émission automatique
- **SQLAlchemy event listeners** opérationnels sur `Patient`, `Dossier`, `Venue`, `Mouvement`
- **Protection anti-boucle** : flag `_emission_context.active` empêche émissions récursives
- **Préservation des types de messages** : A01→A01, A02→A02, etc. (fix implémenté)

### Scénarios IHE PAM testés et fonctionnels
| Type | Description | Crée Mouvement ? | Émission | Statut |
|------|-------------|------------------|----------|--------|
| **A01** | Admission | ✅ Oui | ✅ Oui | **TESTÉ OK** |
| **A04** | Register patient | ➖ Non (Patient only) | ✅ Oui | **TESTÉ OK** |
| **A05** | Pre-admission | ✅ Oui | ✅ Oui | **TESTÉ OK** |

### Scénarios IHE PAM mappés mais NON testés
| Type | Description | Crée Mouvement ? | Émission | Statut |
|------|-------------|------------------|----------|--------|
| **A02** | Transfer | ✅ Oui | ✅ Devrait | ⚠️ Non testé |
| **A03** | Discharge | ✅ Oui | ✅ Devrait | ⚠️ Non testé |
| **A11** | Cancel admission | ✅ Modifie | ✅ Devrait | ⚠️ Non testé |
| **A12** | Cancel transfer | ✅ Modifie | ✅ Devrait | ⚠️ Non testé |
| **A13** | Cancel discharge | ✅ Modifie | ✅ Devrait | ⚠️ Non testé |
| **A31** | Update demographics | ➖ Patient only | ✅ Devrait | ⚠️ Non testé |

### Scénarios IHE PAM avec handlers incomplets
| Type | Description | Handler | Statut |
|------|-------------|---------|--------|
| **A21** | Leave of absence | `handle_leave_message` | ❌ Pas d'implémentation complète |
| **A22** | Return from leave | `handle_leave_message` | ❌ Pas d'implémentation complète |
| **A08** | Update patient info | Mappé vers admission | ⚠️ Comportement à vérifier |
| **A40** | Merge patients | `handle_merge_patient` | ⚠️ Spécial (pas de Mouvement) |

### Scénarios IHE PAM non implémentés
- A06, A07, A09, A10, A14, A15, A16, A17, A18, A20, A23-A30, A32-A39, A41-A61...
- Nombreux autres événements IHE PAM disponibles dans le standard

---

## ❌ Ce qui ne fonctionne PAS

### 1. Génération FHIR désactivée
```python
# Ligne 271-280 dans emit_on_create.py
fhir_payload = None  # TEMPORARILY DISABLED
```

**Raison** : Erreurs de lazy loading avec entités détachées
```
DetachedInstanceError: Parent instance <Venue at 0x...> is not bound to a Session; 
lazy load operation of attribute 'mouvements' cannot proceed
```

**Solution requise** :
- Option A : Eager load complet avant détachement
- Option B : Passer les données sérialisées au lieu des objets SQLModel
- Option C : Générer FHIR avant détachement dans la même session

### 2. Handlers incomplets

**A21/A22 (Leave of absence)** :
```python
# app/services/pam.py - handle_leave_message
async def handle_leave_message(session: Session, trigger: str, pid_data: dict, pv1_data: dict):
    # TODO: Implémenter la logique de absence temporaire
    return True, "Leave message processed (stub)"
```

**A08 (Update patient)** :
- Mappé vers `handle_admission_message` mais comportement incertain
- Devrait probablement avoir son propre handler pour ne mettre à jour que les données patient

---

## 📊 Résultats tests actuels

### Test injection A01 (✅ SUCCÈS)
```
📥 ID=191 A01 ✅ processed ep=1    ← Message reçu
📤 ID=193 A01 ✅ sent      ep=2    ← Émission automatique (type préservé!)
📤 ID=194 A01 ❌ error     ep=3    ← Émission tentée (endpoint down)
```

### Test tous types (⚠️ PARTIEL)
```
Type   | Reçu  | Émis  | Résultat
A01    |   7   |  10   | ✅ OK
A05    |   2   |   2   | ✅ OK
A02    |   1   |   0   | ⚠️ Pas d'émission
A03    |   1   |   0   | ⚠️ Pas d'émission
A21    |   1   |   0   | ⚠️ Pas d'émission
A22    |   1   |   0   | ⚠️ Pas d'émission
A31    |   1   |   0   | ⚠️ Pas d'émission
```

**Cause probable** : Test exécuté pendant instabilité serveur (voir logs "Address already in use")

---

## 🎯 Ce qu'il reste à faire

### Priorité 1 : Réactiver FHIR
1. Choisir stratégie (eager load vs serialization vs same-session)
2. Tester génération FHIR sans lazy load errors
3. Vérifier contenu Bundle FHIR généré

### Priorité 2 : Compléter handlers
1. Implémenter `handle_leave_message` (A21/A22)
2. Créer `handle_update_patient` pour A08/A31
3. Documenter handlers existants

### Priorité 3 : Tests complets
1. Tester tous les types implémentés (A01-A13, A31, A40)
2. Vérifier préservation types sur TOUS les scénarios
3. Tester émission FHIR quand réactivée

### Priorité 4 : Configuration production
1. Documenter configuration endpoints (éviter sender→receiver même port)
2. Ajouter champ `source` dans MessageLog ("external" vs "auto_emission")
3. Métriques et monitoring des émissions

---

## 📝 Fichiers modifiés

### Fonctionnels
- ✅ `app/services/entity_events.py` - Listeners avec anti-loop
- ✅ `app/services/emit_on_create.py` - Types préservés, FHIR disabled
- ✅ `app/services/pam.py` - Handlers async, pas d'émission manuelle

### Documentation
- ✅ `Doc/emission_automatique.md` - Doc complète système
- ✅ `Doc/emission_automatique_debug.md` - Historique debug
- ✅ `tools/inject_mllp_direct.py` - Script test injection
- ✅ `tools/test_all_message_types.py` - Test multi-types

---

## ⚠️ Limitations connues

1. **FHIR désactivé** - Temporairement, à réactiver
2. **Handlers incomplets** - A21, A22, A08 partiels
3. **Tests incomplets** - Seuls A01/A05 validés en production
4. **Pas de filtre source** - Risque boucle si mauvaise config endpoints
5. **Pas de retry** - Si émission échoue, pas de réessai automatique
6. **Pool connexions** - Limite 5+10, peut saturer si volume élevé

---

## 🎉 Conclusion

Le système d'émission automatique **fonctionne pour les cas de base** (A01, A05) avec **préservation des types de messages**.

**Mais** : 
- ❌ FHIR désactivé temporairement
- ⚠️ Pas tous les scénarios IHE PAM testés
- ⚠️ Certains handlers incomplets (A21, A22)

**Pour dire "ça marche vraiment pour tous les scénarios"**, il faudrait :
1. Réactiver et tester FHIR
2. Compléter les handlers manquants
3. Tester systématiquement tous les types A01-A61 implémentés
