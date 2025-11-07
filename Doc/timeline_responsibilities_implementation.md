# Implémentation des responsabilités par mouvement - ZBE-9 Timeline

## 📋 Résumé des modifications

Cette mise à jour implémente le tracking détaillé des responsabilités (UF) au niveau de chaque mouvement et ajoute une timeline visuelle dans l'interface venue.

## 🎯 Objectifs

1. **Tracer les responsabilités par mouvement** : Chaque mouvement porte maintenant les 4 UF et la nature ZBE-9
2. **Timeline visuelle** : Afficher l'évolution chronologique des responsabilités dans le détail d'une venue
3. **Liste enrichie** : Afficher les UF et la nature dans la liste des mouvements

## 🔧 Modifications techniques

### 1. Modèle de données (`app/models.py`)

**Ajout de 5 nouveaux champs au modèle `Mouvement`** :
- `uf_responsabilite: Optional[str]` - UF de responsabilité calculée selon ZBE-9
- `uf_hebergement: Optional[str]` - UF d'hébergement (PV1-3-1)
- `uf_medicale: Optional[str]` - UF médicale (ZBE-7 si M dans nature)
- `uf_soins: Optional[str]` - UF de soins (ZBE-7 si S dans nature)
- `movement_nature: Optional[str]` - Nature du mouvement (ZBE-9 ou ZBE-10)

### 2. Handlers PAM (`app/services/pam.py`)

**Mise à jour des 3 handlers principaux** :

#### `handle_admission_message` (lignes ~880-920)
- Calcul des UF avant création du mouvement
- Population des 5 nouveaux champs lors de la création
- Priorité M > H > S respectée

#### `handle_discharge_message` (lignes ~1100-1180)
- Réorganisation : calcul UF avant création du mouvement
- Population des 5 nouveaux champs lors de la création
- Nature D ne change pas l'UF responsabilité

#### `handle_transfer_message` (lignes ~970-1050)
- Calcul des UF selon même logique que admission
- Population des 5 nouveaux champs lors de la création
- Nature L ne change pas l'UF responsabilité

### 3. Interface venue (`app/routers/venues.py`)

**Route `get_venue` enrichie** (lignes ~260-320) :
- Récupération de tous les mouvements de la venue
- Construction d'une liste `timeline` avec pour chaque mouvement :
  - `when` : date/heure
  - `trigger` : type de message (ADT^A01, etc.)
  - `movement_type` : admission, discharge, transfer
  - `nature` : ZBE-9 value
  - `uf_responsabilite`, `uf_medicale`, `uf_hebergement`, `uf_soins`
  - `location` : localisation

### 4. Template timeline (`app/templates/venue_detail.html`)

**Nouvelle section timeline** (après ligne 60) :
- Timeline verticale avec points et cartes par événement
- Affichage des 4 UF avec icônes et couleurs distinctes :
  - 🟢 UF Responsabilité (vert émeraude)
  - 🔴 UF Médicale (rouge)
  - 🔵 UF Hébergement (bleu)
  - 🟡 UF Soins (ambre)
- Badge pour la nature du mouvement (M, H, S, L, D, etc.)
- Timestamp et localisation

### 5. Liste des mouvements (`app/routers/mouvements.py`)

**Colonnes ajoutées** :
- "UF Resp." avec badge vert si présent
- "Nature" avec badge violet si présent

**Fonctions helper** :
- `_uf_resp_cell()` : formatte l'UF responsabilité avec badge
- `_nature_cell()` : formatte la nature avec badge

### 6. Migration base de données

**Migration 010** (`migrations/010_add_mouvement_uf_fields.sql`) :
```sql
ALTER TABLE mouvement ADD COLUMN uf_responsabilite TEXT;
ALTER TABLE mouvement ADD COLUMN uf_hebergement TEXT;
ALTER TABLE mouvement ADD COLUMN uf_medicale TEXT;
ALTER TABLE mouvement ADD COLUMN uf_soins TEXT;
ALTER TABLE mouvement ADD COLUMN movement_nature TEXT;

CREATE INDEX idx_mouvement_uf_responsabilite ON mouvement(uf_responsabilite);
CREATE INDEX idx_mouvement_nature ON mouvement(movement_nature);
```

**Script d'application** :
- `apply_migration_010.py` : script standalone
- `apply_all_migrations.py` : mis à jour pour inclure migration 010

### 7. Tests

**Tests ZBE-9** (`tests/test_zbe9_responsibility.py`) :
- Validation priorité M > H > S ✅
- Validation L/D ne changent pas l'UF ✅

**Test d'intégration** (`tests/test_ihe_integration.py`) :
- Mis à jour pour inclure segment ZBE dans les messages de test ✅

## 🚀 Utilisation

### Appliquer la migration

```bash
# Sur base existante
python3 apply_migration_010.py

# Ou inclure dans migration globale
python3 apply_all_migrations.py
```

### Tester la timeline

```bash
# Créer des données de démonstration
python3 demo_timeline_responsibilities.py

# Lancer le serveur
python3 -m uvicorn app.app:app --reload

# Naviguer vers l'URL affichée (ex: http://127.0.0.1:8000/venues/1)
```

### Exécuter les tests

```bash
# Tests ZBE-9
pytest tests/test_zbe9_responsibility.py -v

# Tests business rules
pytest tests/test_new_business_rules.py -v

# Test intégration IHE
pytest tests/test_ihe_integration.py -v
```

## 📊 Exemple de timeline

Une venue avec plusieurs mouvements affichera :

```
Timeline des responsabilités
│
●─ 2025-11-06 14:30 - ADT^A01 (Admission)
│  Nature: M
│  🟢 UF Responsabilité: CARDIO^001
│  🔴 UF Médicale: CARDIO^001
│  🔵 UF Hébergement: CARDIO
│  📍 CARDIO^001^LIT01
│
●─ 2025-11-06 16:15 - ADT^A02 (Transfer)
│  Nature: H
│  🟢 UF Responsabilité: CHIR
│  🔵 UF Hébergement: CHIR
│  📍 CHIR^002^LIT02
│
●─ 2025-11-06 18:00 - ADT^A02 (Transfer)
│  Nature: L
│  🟢 UF Responsabilité: CHIR (inchangé)
│  🔵 UF Hébergement: CHIR
│  📍 CHIR^002^LIT03
│
●─ 2025-11-06 20:30 - ADT^A03 (Discharge)
   Nature: D
   🟢 UF Responsabilité: CHIR (inchangé)
   📍 CHIR^002^LIT03
```

## 🎨 Design de la timeline

- **Ligne verticale bleue** relie tous les événements
- **Points bleus** marquent chaque mouvement
- **Cartes blanches** avec bordure contiennent les détails
- **Badges colorés** pour les UF avec icônes sémantiques
- **Responsive** : s'adapte aux petits écrans

## 🔍 Règles ZBE-9 implémentées

1. **Nature M** (Médicale) : `uf_responsabilite = ZBE-7`, `uf_medicale = ZBE-7`
2. **Nature H** (Hébergement) : `uf_responsabilite = PV1-3-1`, `uf_hebergement = PV1-3-1`
3. **Nature S** (Soins) : `uf_responsabilite = ZBE-7`, `uf_soins = ZBE-7`
4. **Nature L/D/LD/C** : Pas de changement de `uf_responsabilite`
5. **Priorité** : M > H > S si plusieurs lettres présentes

## ✅ Tests validés

- ✅ 2 tests ZBE-9 responsabilités
- ✅ 7 tests business rules (A06/A07, A01/A04)
- ✅ 1 test intégration IHE PAM end-to-end
- ✅ 143 tests passent au total

## 📝 Notes

- Les mouvements existants auront `NULL` pour les nouveaux champs UF
- La timeline ne s'affiche que si des mouvements existent
- Le mode TESTING (env var) tolère l'absence de structure UF pour les tests
- Les index sur `uf_responsabilite` et `movement_nature` optimisent les recherches

## 🔄 Prochaines étapes possibles

1. Filtre par UF responsabilité dans la liste des mouvements
2. Graphique d'évolution des UF sur le tableau de bord
3. Export CSV/Excel de la timeline
4. Alertes sur changements anormaux d'UF
5. Statistiques par UF (durée moyenne, nombre de passages)
