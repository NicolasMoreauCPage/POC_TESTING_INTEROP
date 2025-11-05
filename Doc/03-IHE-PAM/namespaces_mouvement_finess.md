# Namespaces d'identifiants - Mouvements (ZBE-1) et FINESS

## Résumé des modifications

Ce document décrit les changements apportés pour supporter :
1. **Les identifiants de mouvements** avec namespace dédié (utilisé dans le segment ZBE-1 des messages IHE PAM)
2. **L'OID FINESS officiel français** déjà configuré (`1.2.250.1.71.4.2.2`)

## 1. Namespace MOUVEMENT (ZBE-1)

### Configuration

Le namespace MOUVEMENT a été ajouté dans `tools/init_all.py` :

```python
{
    "name": "MOUVEMENT",
    "description": "Identifiant de mouvement patient (ZBE-1)",
    "oid": "1.2.250.1.213.1.1.1.4",
    "system": "urn:oid:1.2.250.1.213.1.1.1.4",
    "type": "MVT"
}
```

### Modèle de données

**app/models.py** - Classe `Mouvement` :
- Ajout de la relation `identifiers` avec le modèle `Identifier`

**app/models_identifiers.py** - Classe `Identifier` :
- Ajout du champ `mouvement_id: Optional[int]`
- Ajout de la relation `mouvement: Optional["Mouvement"]`
- Ajout du type `MVT = "MVT"` dans l'enum `IdentifierType`
- Ajout du type `FINESS = "FINESS"` dans l'enum `IdentifierType`

### Génération de messages HL7 PAM

**adapters/hl7_pam_fr.py** - Fonction `build_message_for_movement()` :

La fonction génère maintenant un **segment ZBE** avec le format suivant :

```
ZBE|31636^MOUVEMENT^1.2.250.1.213.1.1.1.4^ISO|20221016235900||INSERT|N||^^^^^^UF^^^3620||HMS
```

#### Structure du segment ZBE

| Champ | Description | Exemple |
|-------|-------------|---------|
| ZBE-1 | Identifiant du mouvement | `31636^MOUVEMENT^1.2.250.1.213.1.1.1.4^ISO` |
| ZBE-2 | Date/heure du mouvement | `20221016235900` |
| ZBE-3 | Action (vide) | `` |
| ZBE-4 | Type d'action | `INSERT` / `UPDATE` / `CANCEL` |
| ZBE-5 | Indicateur annulation | `N` / `Y` |
| ZBE-6 | Évènement d'origine | `` |
| ZBE-7 | UF responsable | `^^^^^^UF^^^3620` |
| ZBE-8 | Réservé | `` |
| ZBE-9 | Mode de traitement | `HMS` (Hospitalisation Médecine/Chirurgie) |

#### Format ZBE-1 (Identifiant du mouvement)

Le champ ZBE-1 suit le format standard HL7 pour les identifiants composés :

```
<ID>^<AUTHORITY>^<OID>^<TYPE>
```

Exemple : `31636^MOUVEMENT^1.2.250.1.213.1.1.1.4^ISO`

- **Composante 1** : Identifiant du mouvement (valeur de `mouvement_seq`)
- **Composante 2** : Authority/Namespace (`MOUVEMENT`)
- **Composante 3** : OID du namespace (`1.2.250.1.213.1.1.1.4`)
- **Composante 4** : Type d'identifiant (`ISO`)

### Utilisation

```python
from adapters.hl7_pam_fr import build_message_for_movement

# Récupérer le namespace MOUVEMENT
mouvement_ns = session.exec(
    select(IdentifierNamespace).where(
        IdentifierNamespace.name == "MOUVEMENT"
    )
).first()

# Générer le message avec segment ZBE
message = build_message_for_movement(
    dossier=dossier,
    venue=venue,
    movement=mouvement,
    patient=patient,
    movement_namespace=mouvement_ns  # Optionnel
)
```

## 2. Namespace FINESS

### Configuration

Le namespace FINESS utilise l'**OID officiel français** défini par l'ASIP (Agence des Systèmes d'Information Partagés de Santé) :

```python
{
    "name": "FINESS",
    "description": "Numéro FINESS des établissements",
    "oid": "1.2.250.1.71.4.2.2",
    "system": "urn:oid:1.2.250.1.71.4.2.2",
    "type": "FINESS"
}
```

### Référence

- **OID FINESS** : `1.2.250.1.71.4.2.2`
- **Domaine** : Identifiants d'établissements de santé en France
- **Source** : [Référentiel ASIP-Santé](https://esante.gouv.fr/)

Le numéro FINESS (Fichier National des Établissements Sanitaires et Sociaux) est un identifiant unique attribué à chaque établissement de santé en France.

## 3. Namespaces configurés

Voici la liste complète des namespaces dans le système :

| Nom | OID | Description | Usage |
|-----|-----|-------------|-------|
| CPAGE | `1.2.250.1.211.10.200.2` | Identifiants CPAGE | Identifiants patient du système CPAGE |
| IPP | `1.2.250.1.213.1.1.1.1` | Identifiant Patient Permanent | Identifiant unique du patient |
| NDA | `1.2.250.1.213.1.1.1.2` | Numéro de Dossier Administratif | Identifiant du dossier |
| VENUE | `1.2.250.1.213.1.1.1.3` | Identifiant de venue/séjour | Identifiant de la venue |
| **MOUVEMENT** | `1.2.250.1.213.1.1.1.4` | Identifiant de mouvement (ZBE-1) | **Nouveau** - Identifiant du mouvement patient |
| FINESS | `1.2.250.1.71.4.2.2` | Numéro FINESS établissement | OID officiel français |

## 4. Tests

Les tests sont disponibles dans `tests/test_movement_identifiers.py` :

- `test_mouvement_has_identifier_relationship()` - Vérifie la relation Mouvement ↔ Identifier
- `test_mouvement_namespace_config()` - Vérifie la configuration du namespace MOUVEMENT
- `test_finess_namespace_config()` - Vérifie l'OID FINESS officiel
- `test_hl7_message_with_zbe_segment()` - Vérifie la génération du segment ZBE
- `test_hl7_message_without_namespace()` - Vérifie le fallback sans namespace

Exécution :
```bash
.venv/bin/python3 -m pytest tests/test_movement_identifiers.py -v
```

## 5. Migration

Pour appliquer ces changements à une installation existante :

```bash
# Réinitialiser la base de données avec les nouveaux namespaces
.venv/bin/python3 tools/init_all.py --reset

# Régénérer les données de test
.venv/bin/python3 -m tools.init_interop_scenarios
```

## 6. Références

- **IHE PAM** : Profil Patient Administration Management
- **Segment ZBE** : Documentation CPAGE (Doc/SpecIHEPAM_CPage/)
- **OID FINESS** : [Référentiel ASIP-Santé](https://esante.gouv.fr/)
- **HL7 v2.5** : Standard de messagerie médicale

---

*Document créé le 2 novembre 2025*
