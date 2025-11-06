# Validation des Segments Obligatoires IHE PAM France

## Résumé

Implémentation de la validation des segments obligatoires selon le profil **IHE PAM France** pour la réception et l'émission de messages HL7v2 ADT.

## Règles Implémentées

### 1. Segment ZBE (Extension IHE PAM France)

**Règle** : Le segment **ZBE est obligatoire** pour tous les **messages de mouvement patient**.

#### Messages concernés (avec ZBE obligatoire)
- **A01** : Admission
- **A02** : Transfert
- **A03** : Sortie
- **A04** : Inscription ambulatoire
- **A05** : Pré-admission
- **A06** : Changement de statut ambulatoire vers hospitalisé
- **A07** : Changement de statut hospitalisé vers ambulatoire
- **A08** : Mise à jour des informations patient
- **A11** : Annulation admission
- **A12** : Annulation transfert
- **A13** : Annulation sortie
- **A21** : Permission de sortie
- **A22** : Retour de permission
- **A23** : Suppression inscription
- **A38** : Annulation pré-admission
- **A52** : Annulation permission (variante)
- **A53** : Annulation retour (variante)
- **A54** : Changement médecin traitant
- **A55** : Annulation changement médecin

#### Messages EXCLUS (ZBE NON obligatoire)
- **A28** : Ajout patient (message d'identité)
- **A31** : Mise à jour patient (message d'identité)
- **A40** : Fusion de patients (message d'identité)
- **A47** : Changement d'identifiant patient (message d'identité)

### 2. Segment MRG (Merge Patient Information)

**Règle** : Le segment **MRG est obligatoire** pour les **messages de fusion et changement d'identifiant**.

#### Messages concernés (avec MRG obligatoire)
- **A40** : Fusion de patients (merge)
- **A47** : Changement d'identifiant patient

Le segment MRG contient les informations d'identification du patient source (avant fusion/changement) :
- **MRG-1** : Prior Patient Identifier List (identifiant du patient à fusionner)
- **MRG-7** : Prior Patient Name (nom du patient à fusionner)

## Implémentation

### Réception (Inbound)

**Fichier** : `app/services/transport_inbound.py`

**Validation** : Effectuée au début du traitement, juste après la validation du type de message ADT.

**Comportement** :
- Si un segment obligatoire est manquant → Message **rejeté** avec **ACK AE**
- Message d'erreur explicite en français
- Code erreur HL7 : **207** (Application error)

**Exemple de rejet** :
```
MSA|AE|MSG001
ERR|||207^Segment ZBE obligatoire manquant pour le message ADT^A01. 
Le profil IHE PAM France requiert le segment ZBE pour tous les messages 
de mouvement patient.^HL70357|E
```

### Émission (Outbound)

**Fichier** : `app/services/hl7_generator.py`

**Validation** : Effectuée lors de la génération du message via `generate_adt_message()`.

**Comportement** :
- Si un segment obligatoire ne peut pas être généré → **ValueError** levée
- Pour les messages de mouvement : un objet `Mouvement` doit être fourni pour générer le segment ZBE
- Pour A40/A47 : **NotImplementedError** (génération MRG pas encore supportée)

**Exemple d'erreur** :
```python
ValueError: Le segment ZBE est obligatoire pour le message ADT^A01 selon le profil IHE PAM France. 
Un objet Mouvement doit être fourni pour générer le segment ZBE.
```

## Tests

**Fichier** : `test_mandatory_segments.py`

### Scénarios de test

| Test | Message | Segment | Résultat Attendu | Statut |
|------|---------|---------|------------------|--------|
| 1 | A01 | Sans ZBE | ❌ Rejeté | ✅ PASS |
| 2 | A01 | Avec ZBE | ✅ Accepté | ✅ PASS |
| 3 | A40 | Sans MRG | ❌ Rejeté | ✅ PASS |
| 4 | A40 | Avec MRG | ⚠️ Validé structurellement | ✅ PASS |
| 5 | A08 | Sans ZBE | ❌ Rejeté | ✅ PASS |
| 6 | A28 | Sans ZBE | ✅ Accepté (message d'identité) | ✅ PASS |

### Résultats des tests

```bash
python test_mandatory_segments.py
```

**Tous les tests passent avec succès** ✅

## Conformité IHE PAM

Cette implémentation assure la conformité avec le profil **IHE PAM France** qui étend le profil international IHE PAM avec :

1. **Segment ZBE** : Extension française obligatoire pour tracer précisément les mouvements patients
2. **Format des identifiants** : Respect du format CX avec OID et type d'identifiant
3. **Validation stricte** : Rejet des messages non conformes pour garantir l'intégrité des données

## Documentation de référence

- **IHE PAM Profile** : ITI-30 (Patient Identity Feed) et ITI-31 (Patient Encounter Management)
- **Spécification ZBE** : Extension profil PAM France (ANS)
- **HL7 v2.5** : Segments MRG pour les fusions de patients

## Améliorations futures

1. **Support A40/A47** : Implémenter la génération complète du segment MRG
2. **Support A47** : Implémenter le changement d'identifiant patient
3. **Validation ZBE avancée** : Valider le contenu des champs ZBE (dates cohérentes, UF valide, etc.)
4. **Logs détaillés** : Enrichir les logs pour le suivi des rejets liés aux segments manquants

## Migration

**Impact** : Cette validation est **rétrocompatible** pour les messages correctement formés selon IHE PAM France.

**Messages existants** : 
- Messages conformes (avec ZBE) → ✅ Aucun impact
- Messages non conformes (sans ZBE) → ❌ Seront rejetés avec erreur explicite

**Recommandation** : Vérifier que tous les systèmes émetteurs génèrent bien le segment ZBE pour les messages de mouvement.
