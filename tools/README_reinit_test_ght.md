# Script de Réinitialisation du GHT de Test

## Description

Le script `reinit_test_ght.py` permet de mettre à jour **uniquement** le GHT de test (code=`TEST_GHT`) avec les données d'initialisation standard, sans toucher aux autres GHT qui pourraient exister dans la base de données.

## Utilisation

```bash
.venv/bin/python tools/reinit_test_ght.py
```

## Ce que fait le script

1. **Initialisation du GHT et namespaces** (Étape 1/4)
   - Trouve ou crée le GHT avec code `TEST_GHT`
   - Crée les 6 namespaces standards : CPAGE, IPP, NDA, VENUE, MOUVEMENT, FINESS

2. **Initialisation des endpoints** (Étape 2/4)
   - Crée 4 endpoints de test :
     - MLLP Receiver Test (port 2575)
     - MLLP Sender Test (port 2576)
     - FHIR Receiver Test (http://127.0.0.1:8000/fhir)
     - FHIR Sender Test (http://127.0.0.1:8080/fhir)

3. **Initialisation des vocabulaires** (Étape 3/4)
   - Initialise les vocabulaires FHIR standards (genre administratif, statut de venue, etc.)

4. **Seeding de la structure** (Étape 4/4)
   - Crée une structure de démonstration complète :
     - 1 Entité Juridique (CHU Demo)
     - Entités Géographiques
     - Pôles, Services, Unités Fonctionnelles
     - Unités d'Hébergement, Chambres, Lits

## Sécurité

⚠️ **Le script ne modifie QUE le GHT avec code=`TEST_GHT`**

Les autres GHT (par exemple `GHT-DEMO-INTEROP` ou d'autres contextes de production) restent totalement intacts.

## Différence avec `init_all.py`

- `init_all.py` : Script complet qui crée/recrée **tout** avec le code `GHT-DEMO-INTEROP`, y compris injection de patients/mouvements de démonstration
- `reinit_test_ght.py` : Script ciblé qui met à jour **uniquement** le GHT `TEST_GHT` avec la structure de base (sans les patients/mouvements)

## Sortie attendue

```
======================================================================
RÉINITIALISATION DU GHT DE TEST UNIQUEMENT
======================================================================

⚠️  Ce script ne touche QUE au GHT avec code=TEST_GHT
   Les autres GHT restent intacts.

[1/4] Initialisation du GHT de test et namespaces...
✓ GHT de test trouvé: Test GHT (id=1)
  ✓ Namespace CPAGE existe déjà
  ...

[2/4] Initialisation des endpoints de test...
  ✓ Endpoint 'MLLP Receiver Test' existe déjà
  ...

[3/4] Initialisation des vocabulaires...
  ✓ Vocabulaires initialisés

[4/4] Seeding de la structure de démonstration...
  ✓ Structure de démonstration créée

======================================================================
✓ RÉINITIALISATION DU GHT DE TEST TERMINÉE
======================================================================

GHT mis à jour: Test GHT
  • ID: 1
  • Code: TEST_GHT
  • OID racine: Non défini
  • URL FHIR: Non défini
```
