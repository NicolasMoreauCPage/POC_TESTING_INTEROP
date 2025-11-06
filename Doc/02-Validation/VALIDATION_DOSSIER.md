# Validation de dossier par supervision des messages

## Vue d'ensemble

La fonctionnalité de **validation de dossier** permet de valider le workflow de tous les messages HL7 associés à un dossier patient, en utilisant les messages déjà reçus ou émis par le système.

## Accès

1. Allez sur la page **Supervision des messages** : `http://127.0.0.1:8000/messages`
2. Cliquez sur le bouton **"Valider un dossier"** (bouton violet)
3. Ou accédez directement à : `http://127.0.0.1:8000/messages/validate-dossier`

## Fonctionnement

### 1. Identification du dossier

Vous pouvez identifier un dossier de deux manières :

- **Par ID interne** : L'identifiant du dossier dans la table `Dossier` (ex: `1`, `42`)
- **Par numéro externe** : Le numéro de visite contenu dans le champ **PV1-19** des messages HL7 (ex: `4159581`, `V2024-001`)

Le système cherche d'abord un dossier par ID interne. S'il en trouve un, il récupère son `dossier_seq` pour rechercher les messages. Sinon, il utilise directement le numéro fourni pour filtrer les messages par PV1-19.

### 2. Filtrage des messages

Le système :

1. Récupère **tous les messages MLLP** de la base de données (kind='MLLP')
2. Extrait l'IPP (PID-3) et le numéro de dossier (PV1-19) de chaque message
3. Filtre les messages dont le PV1-19 correspond au numéro recherché
4. Trie les messages par ordre chronologique (`created_at`)

Vous pouvez optionnellement filtrer par **endpoint** pour ne valider que les messages d'une source spécifique.

### 3. Validation du scénario

Une fois les messages filtrés :

1. Les payloads HL7 sont concaténés avec des sauts de ligne
2. Le scénario complet est validé via le service `scenario_validation.py`
3. Les validations effectuées :
   - **Structure** : Chaque message est validé individuellement (IHE PAM)
   - **Workflow** : Les transitions d'état sont vérifiées (A05→A01→A02→A03, etc.)
   - **Cohérence** : Patient unique, dossier unique, ordre chronologique

### 4. Affichage des résultats

La page de résultats affiche :

- **Statut global** : Scénario valide ✓ ou invalide ✗
- **Erreurs de workflow** : Transitions d'état incorrectes
- **Erreurs de cohérence** : Incohérences entre messages (patient différent, timestamps désordonnés)
- **Détails des messages** : Tableau avec type, état, patient, visite, timestamp et validation

## Cas d'usage

### Exemple 1 : Validation par ID interne

```
Numéro de dossier: 1
Endpoint: (tous)
```

→ Recherche le dossier `Dossier.id = 1`, trouve `dossier_seq = 70`, filtre tous les messages avec `PV1-19 = "70"`

### Exemple 2 : Validation par numéro externe

```
Numéro de dossier: 4159581
Endpoint: (tous)
```

→ Filtre directement tous les messages avec `PV1-19 = "4159581"`

### Exemple 3 : Validation avec filtrage par endpoint

```
Numéro de dossier: 4159581
Endpoint: MLLP Receiver A
```

→ Filtre les messages avec `PV1-19 = "4159581"` ET `endpoint_id = (ID de MLLP Receiver A)`

## Détection des erreurs

### Erreurs de workflow

- **Événement initial invalide** : Le premier message n'est pas un événement d'initialisation (A04, A01, A05)
- **Transition invalide** : Le workflow ne suit pas les règles IHE PAM (ex: A03 avant A01)

Exemple :
```
Message 1: A02 (Transfer patient) 
Erreur: "Invalid initial event: A02 is not in [A04, A01, A05]"
```

### Erreurs de cohérence

- **Patient multiple** : Les messages ont des identifiants patient différents
- **Dossier multiple** : Les messages ont des numéros de visite différents (ne devrait jamais arriver avec ce filtre)
- **Timestamps désordonnés** : Les horodatages ne sont pas croissants

Exemple :
```
Check: patient_uniqueness
Description: "Multiple patient IDs found in scenario: 900006654054, 900006654055"
```

## Architecture technique

### Fichiers impliqués

- **Router** : `app/routers/messages.py`
  - `GET /messages/validate-dossier` : Affiche le formulaire
  - `POST /messages/validate-dossier` : Traite la validation
  
- **Template** : `app/templates/validate_dossier.html`
  - Formulaire avec champ dossier et select endpoint
  - Affichage des résultats de validation
  
- **Service** : `app/services/scenario_validation.py`
  - `validate_scenario()` : Valide un scénario multi-messages
  
- **Fonction d'extraction** : `app/routers/messages.py`
  - `_extract_ipp_and_dossier()` : Extrait PID-3 (IPP) et PV1-19 (dossier)

### Flux de données

```
Utilisateur
    ↓ (saisit numéro dossier)
Formulaire (validate_dossier.html)
    ↓ (POST /messages/validate-dossier)
Router (messages.py)
    ↓ (cherche Dossier par ID)
    ↓ (filtre MessageLog par PV1-19)
    ↓ (concatène payloads)
Service (scenario_validation.py)
    ↓ (valide structure + workflow + cohérence)
Template (validate_dossier.html)
    ↓ (affiche résultats)
Utilisateur
```

## Limitations

- **MLLP uniquement** : Seuls les messages HL7 v2.5 via MLLP sont supportés (pas de FHIR)
- **PV1-19 requis** : Les messages doivent contenir un numéro de visite en PV1-19
- **Ordre chronologique** : Les messages sont triés par `created_at` (timestamp de réception), pas par l'horodatage du message
- **Performance** : Pour de très grandes bases de données, le filtrage peut être lent (pas d'index sur le contenu des payloads)

## Extensions futures possibles

- Ajouter un index sur les numéros de visite extraits (champ dédié dans MessageLog)
- Supporter la validation FHIR (Bundle de ressources Patient/Encounter)
- Permettre la sélection de plusieurs dossiers à la fois
- Ajouter un export PDF ou JSON des résultats de validation
- Intégrer avec le contexte GHT pour valider les dossiers d'une UF
