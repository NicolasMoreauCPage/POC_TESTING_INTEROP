# Formulaire Patient - Conformité RGPD France

## 📋 Résumé des corrections appliquées

Date : 3 novembre 2025

### 🔴 Problèmes identifiés et corrigés

#### 1. **Champs interdits en France (RGPD - Article 9)**
   - ❌ **Race** : SUPPRIMÉ des formulaires (interdit par la loi Informatique et Libertés)
   - ❌ **Religion** : SUPPRIMÉ des formulaires (données sensibles interdites)
   - ⚠️ Ces champs restent en base de données pour compatibilité legacy mais ne sont plus collectés

#### 2. **Doublon de champ sexe**
   - ❌ **`gender` ET `administrative_gender`** : doublons supprimés
   - ✅ Un seul champ **`gender`** (sexe administratif) conservé
   - Vocabulaire : `male`, `female`, `other`, `unknown` (conforme HL7/FHIR)

#### 3. **Statut marital**
   - ❌ Champ texte libre (non standardisé)
   - ✅ **Dropdown list** avec codes HL7 v2.5 Table 0002 :
     - **S** - Célibataire (Single)
     - **M** - Marié(e) (Married)
     - **P** - Partenariat/PACS (Domestic partner)
     - **D** - Divorcé(e) (Divorced)
     - **A** - Séparé(e) (Separated)
     - **W** - Veuf/Veuve (Widowed)
     - **U** - Non spécifié (Unknown)

#### 4. **Civilité (prefix)**
   - ❌ Champ texte libre
   - ✅ **Dropdown list** avec options françaises :
     - **M.** - Monsieur
     - **Mme** - Madame
     - **Mlle** - Mademoiselle

#### 5. **Erreur d'enregistrement**
   - ❌ Appels manuels à `emit_to_senders()` obsolètes
   - ✅ Émission automatique via `entity_events.py` (after_insert/after_update listeners)
   - ✅ Ajout de `session.rollback()` en cas d'erreur

---

## 📝 Champs du formulaire (ordre final)

### ✅ Formulaire de création/modification

#### **Section Identité**
1. **Numéro de séquence** (`patient_seq`) - Généré automatiquement
2. **Nom** (`family`) - **Obligatoire**
3. **Prénom** (`given`) - **Obligatoire**
4. **Deuxième prénom** (`middle`) - Optionnel
5. **Date de naissance** (`birth_date`) - Format AAAA-MM-JJ
6. **Sexe administratif** (`gender`) - Dropdown : Masculin/Féminin/Autre/Inconnu
7. **Civilité** (`prefix`) - Dropdown : M./Mme/Mlle

#### **Section Coordonnées**
8. **Adresse** (`address`) - Numéro et rue
9. **Ville** (`city`)
10. **Code postal** (`postal_code`) - Ex: 75001
11. **Téléphone** (`phone`) - Ex: 0601020304
12. **Email** (`email`) - Format email validé

#### **Section Administrative**
13. **NIR** (`nir`) - Numéro de Sécurité Sociale (15 chiffres)
14. **Statut marital** (`marital_status`) - Dropdown codes HL7
15. **Nationalité** (`nationality`) - Code pays ISO (ex: FR, BE, CH)
16. **External ID** (`external_id`) - Identifiant système source

### ❌ Champs supprimés (non conformes RGPD)
- ~~`race`~~ - Interdit Article 9 RGPD
- ~~`religion`~~ - Interdit Article 9 RGPD
- ~~`administrative_gender`~~ - Doublon de `gender`
- ~~`ssn`~~ - Remplacé par `nir` (spécifique France)

---

## 🔧 Modifications techniques

### Fichiers modifiés

#### 1. **`app/routers/patients.py`**
   - ✅ Formulaire création : champs RGPD compliant + dropdowns
   - ✅ Formulaire édition : champs RGPD compliant + dropdowns
   - ✅ POST `/new` : ajout de tous les champs standards + rollback erreur
   - ✅ POST `/{id}/edit` : suppression des champs interdits + pas d'émission manuelle
   - ✅ DELETE : suppression émission manuelle (géré par entity_events)

#### 2. **`app/templates/patient_detail.html`**
   - ✅ Suppression affichage race/religion
   - ✅ Organisation par sections (Identité/Coordonnées/Administratif)
   - ✅ Ajout note RGPD en bas de page
   - ✅ Amélioration confirmation suppression

#### 3. **`app/models.py`**
   - ✅ Documentation complète du modèle Patient
   - ✅ Marquage champs deprecated (race/religion/ssn/administrative_gender)
   - ✅ Commentaires RGPD explicites avec ⚠️

---

## 📊 Conformité réglementaire

### ✅ RGPD (Règlement Général sur la Protection des Données)
- **Article 9** : Données sensibles (race, religion) NON collectées
- **Minimisation des données** : Collecte uniquement des données nécessaires
- **Transparence** : Note explicite sur la page de détail

### ✅ Loi Informatique et Libertés (France)
- **Article 8** : Pas de collecte de données sensibles sans justification
- **NIR** : Utilisation conforme (identifiant de santé autorisé)

### ✅ Standards interopérabilité
- **HL7 v2.5** : Codes statut marital conformes (Table 0002)
- **FHIR** : Vocabulaire gender conforme (ValueSet AdministrativeGender)

---

## 🧪 Tests recommandés

### Test 1 : Création patient
```bash
# Accéder au formulaire
curl http://localhost:8000/patients/new

# Vérifier que les champs race/religion n'apparaissent PAS
# Vérifier que marital_status est une dropdown
# Vérifier que prefix est une dropdown
```

### Test 2 : Enregistrement patient
```bash
# Créer un patient avec tous les champs
# Vérifier que l'enregistrement réussit
# Vérifier que l'émission automatique fonctionne (pas d'erreur)
```

### Test 3 : Modification patient
```bash
# Modifier un patient existant
# Vérifier que les champs interdits ne sont pas modifiables
# Vérifier que l'émission A31 est déclenchée automatiquement
```

### Test 4 : Affichage détail
```bash
# Afficher un patient
# Vérifier que race/religion n'apparaissent PAS
# Vérifier la note RGPD en bas de page
```

---

## 🚀 Prochaines étapes recommandées

### Court terme
1. ✅ **Migration données existantes** : Nettoyer race/religion si présents
2. ✅ **Validation NIR** : Ajouter validation format 15 chiffres + clé Luhn
3. ✅ **Validation téléphone** : Format français (0X XX XX XX XX)

### Moyen terme
1. ⚠️ **Audit RGPD complet** : Vérifier tous les autres formulaires (Dossier, Venue, etc.)
2. ⚠️ **Registre des traitements** : Documenter la finalité de chaque champ
3. ⚠️ **Durée de conservation** : Implémenter politique de suppression automatique

### Long terme
1. 📋 **Consentement explicite** : Ajouter gestion des consentements patients
2. 📋 **Droit à l'oubli** : Implémenter suppression/anonymisation complète
3. 📋 **Portabilité** : Export des données patient format standard

---

## 📚 Références

### Réglementation
- [RGPD - Article 9](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre2#Article9) : Traitement des catégories particulières de données
- [Loi Informatique et Libertés](https://www.cnil.fr/fr/la-loi-informatique-et-libertes) : Cadre français
- [Guide CNIL Santé](https://www.cnil.fr/fr/sante) : Recommandations secteur santé

### Standards techniques
- [HL7 v2.5 Table 0002](http://hl7-definition.caristix.com:9010/Default.aspx?version=HL7+v2.5.1&table=0002) : Marital Status
- [FHIR Patient](https://www.hl7.org/fhir/patient.html) : Spécification FHIR
- [IHE PAM France](https://www.interopsante.org/) : Profil français

---

## ✅ Checklist validation

- [x] Champs race/religion supprimés des formulaires
- [x] Un seul champ gender (pas de doublon)
- [x] Statut marital en dropdown avec codes HL7
- [x] Civilité en dropdown
- [x] Émission automatique via entity_events
- [x] Gestion erreurs avec rollback
- [x] Documentation modèle Patient
- [x] Page détail mise à jour
- [x] Note RGPD ajoutée
- [ ] Tests manuels effectués
- [ ] Migration données legacy planifiée
- [ ] Audit RGPD complet des autres entités

---

## 📞 Contact

Pour toute question sur la conformité RGPD ou les modifications techniques :
- **Documentation technique** : `/Doc/STANDARDS.md`
- **Conformité ZBE** : `/Doc/conformite_zbe.md`
- **Architecture** : `/Doc/architecture_workflows_proposal.md`
