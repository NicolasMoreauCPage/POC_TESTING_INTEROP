# Organisation hiérarchique des endpoints par GHT et Établissement Juridique

## Vue d'ensemble

La page des endpoints (`/endpoints`) a été restructurée pour afficher les systèmes de manière hiérarchique :

- **GHT** (Groupement Hospitalier de Territoire)
  - **Établissement Juridique** (Entité juridique)
    - Endpoints

Cette organisation reflète la structure organisationnelle réelle et facilite la gestion dans un contexte multi-établissements.

## Modifications apportées

### 1. Modèle de données (`app/models_shared.py`)

Ajout d'une relation directe entre `SystemEndpoint` et `EntiteJuridique` :

```python
class SystemEndpoint(SQLModel, table=True):
    # ... champs existants ...
    
    entite_juridique_id: Optional[int] = Field(foreign_key="entitejuridique.id", nullable=True)
    entite_juridique: Optional["EntiteJuridique"] = Relationship(back_populates="endpoints")
```

### 2. Relation inverse (`app/models_structure_fhir.py`)

Ajout de la relation `endpoints` dans `EntiteJuridique` :

```python
class EntiteJuridique(SQLModel, table=True):
    # ... champs existants ...
    
    endpoints: List["SystemEndpoint"] = Relationship(back_populates="entite_juridique")
```

### 3. Router endpoints (`app/routers/endpoints.py`)

Modification de `list_endpoints()` pour :

- Charger les relations GHT et EJ avec `selectinload`
- Grouper les endpoints par GHT, puis par EJ
- Construire une structure hiérarchique pour le template
- Gérer les cas particuliers (endpoints sans GHT, sans EJ)

### 4. Template hiérarchique (`app/templates/endpoints_hierarchical.html`)

Nouveau template avec :

- **Groupes GHT** (bleu) : Affichent le nom, code et URL FHIR du GHT
- **Groupes EJ** (vert) : Affichent le nom, nom court et FINESS de l'établissement
- **Endpoints** : Tableau standard avec toutes les informations
- **Section "Sans GHT"** (gris) : Pour les endpoints non rattachés

Caractéristiques visuelles :

- Couleurs distinctives par niveau (bleu GHT, vert EJ, gris non rattaché)
- Badges pour codes GHT et FINESS EJ
- Tables cliquables redirigeant vers la page de détail
- Statuts colorés (ON/OFF, RUNNING/STOPPED)

### 5. Migration (`migrations/006_add_endpoint_ej_link.sql`)

Ajout de la colonne `entite_juridique_id` avec index pour les performances.

## Structure de la hiérarchie

```text
GHT: Centre Val de Loire (CODE_CVL)
├── Établissement Juridique: CH Tours (FINESS: 370000001)
│   ├── Endpoint: MLLP Tours ADT
│   └── Endpoint: FHIR Tours API
├── Établissement Juridique: CH Blois (FINESS: 410000001)
│   └── Endpoint: MLLP Blois ADT
└── Endpoint sans EJ: FILE Import Structure

Systèmes sans GHT
└── Endpoint: Test Local
```

## Utilisation

### Affichage

Naviguez vers `/endpoints` - la page affichera automatiquement la structure hiérarchique.

### Attribution d'un endpoint à une EJ

Lors de la création ou modification d'un endpoint, vous pouvez maintenant :

1. Sélectionner un GHT (via `ght_context_id`)
2. Sélectionner une entité juridique (via `entite_juridique_id`)

**Note** : L'EJ doit appartenir au même GHT que l'endpoint pour maintenir la cohérence.

### Ordre d'affichage

- GHTs triés par ID
- EJs triés par ID au sein de chaque GHT
- Endpoints sans EJ affichés après les EJs dans leur GHT
- Section "Sans GHT" en fin de page

## Avantages

1. **Clarté organisationnelle** : Vue immédiate de la répartition des endpoints
2. **Navigation facilitée** : Groupements logiques par structure administrative
3. **Gestion multi-établissements** : Idéal pour les GHT avec plusieurs EJ
4. **Compatibilité ascendante** : Les endpoints existants sans GHT/EJ restent visibles
5. **Performance** : Chargement optimisé avec `selectinload`

## Migration des données existantes

Les endpoints existants conservent leur `ght_context_id`. Pour les rattacher à une EJ :

```python
# Exemple : rattacher un endpoint à une EJ
endpoint = session.get(SystemEndpoint, endpoint_id)
endpoint.entite_juridique_id = ej_id
session.commit()
```

Ou via l'interface d'édition une fois celle-ci mise à jour pour inclure le champ EJ.

## Prochaines étapes

1. Mettre à jour le formulaire de création/édition d'endpoint pour inclure la sélection d'EJ
2. Ajouter une validation : l'EJ sélectionnée doit appartenir au GHT sélectionné
3. Implémenter un mécanisme d'attribution automatique d'EJ basé sur le contexte
4. Ajouter des filtres/recherche par GHT ou EJ sur la page des endpoints
