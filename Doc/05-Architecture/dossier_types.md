# Types de dossier et mouvements IHE PAM

Ce document décrit les règles de compatibilité entre les types de dossier et les mouvements IHE PAM dans l'application.

## Types de dossier

### 1. Hospitalisé (HOSPITALISE)
Patient admis pour une hospitalisation complète.
- **Classe HL7/FHIR** : `IMP` (Inpatient)
- **Mouvements autorisés** :
  - A01 : Admission
  - A02 : Transfert
  - A03 : Sortie
  - A06/A07 : Changement de classe
  - A21 : Absence temporaire
  - A22 : Retour d'absence

### 2. Externe (EXTERNE)
Patient venant pour une consultation ou un acte externe.
- **Classe HL7/FHIR** : `AMB` (Ambulatory)
- **Mouvements autorisés** :
  - A04 : Inscription
  - A06/A07 : Changement de classe

### 3. Urgence (URGENCE)
Patient admis aux urgences.
- **Classe HL7/FHIR** : `EMER` (Emergency)
- **Mouvements autorisés** :
  - A04 : Arrivée aux urgences
  - A03 : Sortie des urgences
  - A06 : Passage en hospitalisation

## Transitions autorisées

### Urgence → Hospitalisé
- **Mouvement** : A06
- **Conditions** :
  - Requiert une unité d'hospitalisation (location)
  - Le dossier ne doit pas être déjà sorti (A03)

### Hospitalisé → Externe
- **Mouvement** : A06
- **Conditions** :
  - Aucun mouvement A02 (transfert) ou A21 (absence) actif
  - Le patient n'est pas en permission

### Externe → Hospitalisé
- **Mouvement** : A07
- **Conditions** :
  - Requiert une unité d'hospitalisation (location)

## Validation des changements

Lors d'une tentative de changement de type :

1. Le système vérifie la compatibilité avec les mouvements existants
2. Si des incompatibilités sont détectées :
   - Un avertissement détaillé est affiché
   - Le changement est bloqué par défaut
   - Option de forcer le changement (avec avertissement)

## Notes importantes

1. Un changement de type implique automatiquement :
   - Mise à jour du type de dossier (`dossier_type`)
   - Mise à jour de la classe de rencontre (`encounter_class`)
   - Génération du mouvement IHE PAM correspondant

2. Les mouvements existants ne sont pas supprimés lors d'un changement forcé, mais :
   - Ils peuvent créer des incohérences dans les rapports
   - Les systèmes externes peuvent rejeter les messages

3. Recommandations :
   - Éviter les changements de type sur les dossiers ayant des mouvements
   - Préférer créer un nouveau dossier si possible
   - Documenter la raison des changements forcés