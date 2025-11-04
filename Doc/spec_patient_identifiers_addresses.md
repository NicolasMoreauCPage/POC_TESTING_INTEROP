# Spécification: Amélioration gestion Patient - Adresses et Identifiants

**Date**: 3 novembre 2025  
**Contexte**: Suite à la conformité RGPD, amélioration gestion identifiants et adresses

---

## 🎯 Problèmes identifiés

### 1. ❌ Adresses incomplètes
**Problème**: Un seul jeu d'adresse (habitation), pas d'adresse de naissance

**HL7 v2.5 spec**:
- **PID-11** : Patient Address (adresse d'habitation)
- **PID-23** : Birth Place (lieu de naissance - texte)
- **Besoin**: Adresse complète de naissance (rue, ville, code postal, pays)

### 2. ❌ PID-32 Identity Reliability Code absent
**Problème**: Pas de champ pour le statut de l'identité

**HL7 v2.5 Table 0445 - Identity Reliability Code**:
- **VIDE** : Identité non vérifiée / déclarative
- **PROV** : Provisoire / Non validé
- **VALI** : Validé (pièce d'identité)
- **DOUTE** : Identité douteuse
- **FICTI** : Identité fictive (X, anonyme, etc.)

**IHE PAM France**: PID-32 est **obligatoire** pour INS (Identité Nationale de Santé)

### 3. ❌ Identifiants externes mal gérés
**Problème actuel**:
- Un seul champ `external_id` (texte libre)
- Pas de contrainte unicité avec namespace/OID
- Table `Identifier` existe mais pas utilisée pour external_id

**Besoin**:
- Contrainte: `UNIQUE(value, system, oid)` dans la table Identifier
- Un patient peut avoir plusieurs identifiants externes (IPP système A, IPP système B)
- **MAIS** dans un même système (system+oid), l'identifiant doit être unique

### 4. ❌ Identifiants internes non émis
**Problème**: Les messages HL7 n'émettent que `patient_seq` dans PID-3

**HL7 spec PID-3**: Peut contenir **plusieurs identifiants** avec répétitions `~`:
```
PID|1||12345^^^HOSP^PI~987654^^^NAT^NH~1234567890123^^^INS^INS-NIR||...
         ↑ IPP local    ↑ IPP nat     ↑ NIR
```

**Besoin**: Émettre tous les identifiants du patient:
- IPP (patient_seq) avec system HOSP
- external_id si présent
- NIR si présent
- Tous les Identifier liés au patient

---

## ✅ Solution proposée

### 1. Modèle Patient - Ajout champs

```python
class Patient(SQLModel, table=True):
    # ... champs existants ...
    
    # Adresse d'habitation (existant)
    address: Optional[str] = None  # PID-11.1 - Rue
    city: Optional[str] = None  # PID-11.3 - Ville
    state: Optional[str] = None  # PID-11.4 - Département/Région
    postal_code: Optional[str] = None  # PID-11.5 - Code postal
    country: Optional[str] = None  # PID-11.6 - Pays (ex: FRA)
    
    # Adresse de naissance (NOUVEAU)
    birth_address: Optional[str] = None  # Rue de naissance
    birth_city: Optional[str] = None  # Ville de naissance (PID-23 actuellement)
    birth_state: Optional[str] = None  # Département de naissance
    birth_postal_code: Optional[str] = None  # Code postal de naissance
    birth_country: Optional[str] = None  # Pays de naissance (ex: FRA)
    
    # Statut identité (NOUVEAU)
    identity_reliability_code: Optional[str] = None  # PID-32 (VIDE/PROV/VALI/DOUTE/FICTI)
    identity_reliability_date: Optional[str] = None  # Date de validation identité
    identity_reliability_source: Optional[str] = None  # Source validation (CNI, Passeport, etc.)
```

### 2. Contrainte unicité Identifier

**Migration DB**:
```sql
-- Ajouter contrainte unicité sur (value, system, oid)
ALTER TABLE identifier ADD CONSTRAINT unique_identifier_per_system 
    UNIQUE (value, system, oid);

-- Index pour performance
CREATE INDEX idx_identifier_lookup ON identifier(value, system, oid);
```

**Validation applicative**:
```python
def validate_unique_identifier(session: Session, value: str, system: str, oid: str, patient_id: int = None):
    """Vérifie qu'un identifiant est unique dans son système."""
    existing = session.exec(
        select(Identifier)
        .where(Identifier.value == value)
        .where(Identifier.system == system)
        .where(Identifier.oid == oid)
        .where(Identifier.patient_id != patient_id if patient_id else True)
    ).first()
    
    if existing:
        raise ValueError(f"Identifiant {value} déjà utilisé dans le système {system}")
```

### 3. Émission identifiants dans PID-3

**Format PID-3** (répétitions avec `~`):
```
PID|1||ID1^^^SYSTEM1^TYPE~ID2^^^SYSTEM2^TYPE~ID3^^^SYSTEM3^TYPE||...
```

**Implémentation**:
```python
def build_pid3_identifiers(patient, forced_system=None):
    """Construit PID-3 avec tous les identifiants du patient."""
    identifiers = []
    
    # 1. IPP (patient_seq) - toujours en premier
    if patient.patient_seq:
        system = forced_system or "HOSP"
        identifiers.append(f"{patient.patient_seq}^^^{system}^PI")
    
    # 2. External ID si présent
    if patient.external_id:
        # Si on a un Identifier lié, utiliser son system/oid
        ext_ident = session.exec(
            select(Identifier)
            .where(Identifier.patient_id == patient.id)
            .where(Identifier.value == patient.external_id)
            .where(Identifier.type == IdentifierType.PI)
        ).first()
        
        if ext_ident:
            identifiers.append(f"{ext_ident.value}^^^{ext_ident.system}^{ext_ident.type}")
        else:
            identifiers.append(f"{patient.external_id}^^^EXTERNAL^PI")
    
    # 3. NIR si présent
    if patient.nir:
        identifiers.append(f"{patient.nir}^^^INS-NIR^NH")
    
    # 4. Tous les autres identifiants actifs
    for ident in patient.identifiers:
        if ident.status == "active" and ident.value not in [patient.patient_seq, patient.external_id, patient.nir]:
            identifiers.append(f"{ident.value}^^^{ident.system}^{ident.type}")
    
    return "~".join(identifiers)
```

**Utilisation dans PID segment**:
```python
pid3 = build_pid3_identifiers(patient, forced_identifier_oid)
pid = f"PID|1||{pid3}||{family}^{given}||{birth_date}|{gender}|||{address}|||||||||||||||{identity_code}"
#                ↑ multiples identifiants                                                     ↑ PID-32
```

### 4. Refonte IHM formulaire patient

**Organisation en blocs accordéon**:

```html
<form>
  <!-- Bloc 1: IDENTITÉ -->
  <div class="form-block">
    <h3>👤 Identité</h3>
    - Civilité, Nom, Prénom(s)
    - Date de naissance, Sexe
    - Statut identité (PID-32) avec dropdown
  </div>
  
  <!-- Bloc 2: IDENTIFIANTS -->
  <div class="form-block">
    <h3>🔑 Identifiants</h3>
    - IPP (patient_seq) - auto
    - External ID + Système + OID
    - NIR (Sécurité sociale)
    - Liste identifiants additionnels (tableau dynamique)
  </div>
  
  <!-- Bloc 3: ADRESSE D'HABITATION -->
  <div class="form-block">
    <h3>🏠 Adresse d'habitation</h3>
    - Rue, Ville, Code postal
    - Département, Pays
  </div>
  
  <!-- Bloc 4: LIEU DE NAISSANCE -->
  <div class="form-block">
    <h3>🍼 Lieu de naissance</h3>
    - Rue de naissance, Ville
    - Code postal, Département, Pays
  </div>
  
  <!-- Bloc 5: CONTACT -->
  <div class="form-block">
    <h3>📞 Contact</h3>
    - Téléphone, Email
  </div>
  
  <!-- Bloc 6: ADMINISTRATIF -->
  <div class="form-block">
    <h3>📋 Informations administratives</h3>
    - Statut marital, Nationalité
    - Médecin traitant
    - Nom jeune fille mère
  </div>
</form>
```

**Gestion identifiants multiples** (tableau dynamique):
```javascript
// Permet d'ajouter/supprimer des identifiants
[
  { value: "ABC123", system: "LABO_X", oid: "1.2.250.1.x", type: "PI" },
  { value: "XYZ789", system: "RADIOL_Y", oid: "1.2.250.1.y", type: "PI" }
]
```

---

## 📋 Checklist implémentation

### Phase 1: Modèle & DB
- [ ] Ajouter champs adresse naissance à `Patient`
- [ ] Ajouter champs `identity_reliability_*` à `Patient`
- [ ] Ajouter champ `country` pour adresses
- [ ] Créer migration Alembic
- [ ] Ajouter contrainte UNIQUE sur `Identifier(value, system, oid)`

### Phase 2: Validation
- [ ] Fonction `validate_unique_identifier()`
- [ ] Validation PID-32 (codes Table 0445)
- [ ] Tests unitaires validation

### Phase 3: Émission HL7
- [ ] Fonction `build_pid3_identifiers()`
- [ ] Intégrer dans `generate_pam_hl7()`
- [ ] Ajouter PID-32 dans segment PID
- [ ] Ajouter adresse complète PID-11
- [ ] Tests émission identifiants multiples

### Phase 4: Réception HL7
- [ ] Parser PID-3 répétitions (split `~`)
- [ ] Créer/mettre à jour `Identifier` pour chaque identifiant reçu
- [ ] Parser PID-32 (identity_reliability_code)
- [ ] Gérer adresse de naissance

### Phase 5: IHM
- [ ] Formulaire création: blocs accordéon
- [ ] Formulaire édition: blocs accordéon
- [ ] Section identifiants avec tableau dynamique (+/- boutons)
- [ ] Dropdown PID-32 avec codes HL7 Table 0445
- [ ] Section adresse de naissance
- [ ] Tests UI

### Phase 6: Documentation
- [ ] Spec PID-32 et codes
- [ ] Spec identifiants multiples
- [ ] Exemples messages HL7 avec PID-3 répétitions
- [ ] Guide utilisateur gestion identifiants

---

## 🧪 Tests

### Test 1: Unicité identifiants
```python
# Cas 1: OK - même ID, systèmes différents
patient1 = create_patient(external_id="123", system="SYSTEM_A")
patient2 = create_patient(external_id="123", system="SYSTEM_B")  # OK

# Cas 2: KO - même ID, même système
patient3 = create_patient(external_id="123", system="SYSTEM_A")  # ❌ ValueError
```

### Test 2: Émission identifiants multiples
```python
patient = Patient(
    patient_seq=1001,
    external_id="EXT123",
    nir="1234567890123"
)
# Identifiers additionnels
add_identifier(patient, "IPP-GHT", "1.2.250.1.GHT", "12345", "IPP")

# Message émis doit contenir:
# PID|1||1001^^^HOSP^PI~EXT123^^^EXTERNAL^PI~1234567890123^^^INS-NIR^NH~12345^^^1.2.250.1.GHT^IPP||...
```

### Test 3: PID-32 validation
```python
# OK
set_identity_reliability(patient, "VALI", source="CNI")

# KO - code invalide
set_identity_reliability(patient, "INVALID")  # ❌ ValueError
```

---

## 📚 Références

### Standards
- **HL7 v2.5 - PID Segment**: Patient Identification
- **HL7 Table 0445**: Identity Reliability Code
- **IHE PAM France**: Guide d'implémentation
- **INS**: Identité Nationale de Santé (France)

### Codes PID-32 (Table 0445)
```
VIDE  - Non renseigné / Déclaratif
PROV  - Provisoire (en attente validation)
VALI  - Validé (pièce identité contrôlée)
DOUTE - Identité douteuse (incohérences détectées)
FICTI - Identité fictive (X, Anonyme, Inconnu)
```

---

## 🎯 Priorités

1. **CRITIQUE**: Contrainte unicité identifiants (éviter doublons)
2. **HAUTE**: PID-32 (obligatoire IHE PAM France pour INS)
3. **HAUTE**: Émission identifiants multiples PID-3
4. **MOYENNE**: Adresse de naissance
5. **MOYENNE**: Refonte IHM (UX)

---

**Status**: 📝 SPÉCIFICATION - En attente implémentation
