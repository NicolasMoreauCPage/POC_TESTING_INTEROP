# Proposition d'architecture : Intégration des scénarios dans le modèle de données

## 🎯 Objectif

Transformer les scénarios IHE d'une simple **collection de messages texte** en de véritables **scénarios métier** liés au modèle de données, permettant :
- ✅ Génération **HL7 PAM** à partir des données
- ✅ Génération **FHIR** à partir des données
- ✅ Traçabilité et cohérence des données
- ✅ Scénarios réutilisables et paramétrables

## 📊 Architecture actuelle vs. proposée

### ❌ **Architecture actuelle (problématique)**

```
InteropScenario
├── InteropScenarioStep (payload HL7 en texte brut)
└── ScenarioBinding → Dossier (lien faible, 1 seul dossier)
```

**Problèmes** :
- Messages HL7 figés (texte brut dans `payload`)
- Impossible de générer du FHIR à partir de ces données
- Pas de lien avec Venue, Mouvement
- Dates obsolètes nécessitant mise à jour post-hoc
- Duplication de données (Patient dans message ≠ Patient en base)

### ✅ **Architecture proposée (métier)**

```
WorkflowScenario (nouveau)
├── name: str (ex: "Admission simple")
├── description: str
├── scenario_type: enum (ADMISSION, TRANSFER, DISCHARGE, UPDATE, etc.)
├── ght_context_id: FK
└── steps: List[WorkflowScenarioStep]

WorkflowScenarioStep
├── order_index: int
├── action_type: enum (CREATE_DOSSIER, CREATE_VENUE, CREATE_MOVEMENT, UPDATE_PATIENT, etc.)
├── parameters: JSON (paramètres de l'action)
└── delay_seconds: int (délai avant prochaine étape)

WorkflowScenarioExecution (instance d'exécution)
├── scenario_id: FK → WorkflowScenario
├── ght_context_id: FK
├── patient_id: FK → Patient (créé ou existant)
├── dossier_id: FK → Dossier (créé)
├── execution_date: datetime
├── status: enum (PENDING, RUNNING, COMPLETED, FAILED)
└── steps: List[WorkflowExecutionStep]

WorkflowExecutionStep
├── execution_id: FK
├── step_id: FK → WorkflowScenarioStep
├── entity_type: enum (PATIENT, DOSSIER, VENUE, MOUVEMENT)
├── entity_id: int (ID de l'entité créée/modifiée)
├── hl7_message_id: FK → MessageLog (si émis en HL7)
├── fhir_message_id: FK → MessageLog (si émis en FHIR)
└── status: enum (PENDING, SENT, ACK, NACK, ERROR)
```

## 🔄 Flux de données proposé

### 1. **Définition d'un scénario** (design-time)

```python
scenario = WorkflowScenario(
    name="Admission urgence avec transfert",
    scenario_type=ScenarioType.ADMISSION_WITH_TRANSFER,
    steps=[
        WorkflowScenarioStep(
            order_index=1,
            action_type=ActionType.CREATE_PATIENT,
            parameters={
                "family": "DUPONT",
                "given": "Jean",
                "birth_date": "1980-01-01",
                "gender": "M"
            }
        ),
        WorkflowScenarioStep(
            order_index=2,
            action_type=ActionType.CREATE_DOSSIER,
            parameters={
                "dossier_type": "URGENCE",
                "uf_responsabilite": "UF-URGENCES",
                "admit_time_offset_hours": 0  # Maintenant
            }
        ),
        WorkflowScenarioStep(
            order_index=3,
            action_type=ActionType.CREATE_VENUE,
            parameters={
                "uf_responsabilite": "UF-URGENCES",
                "code": "URG-001",
                "start_time_offset_hours": 0
            }
        ),
        WorkflowScenarioStep(
            order_index=4,
            action_type=ActionType.CREATE_MOVEMENT,
            parameters={
                "type": "A02",  # Transfert
                "from_location": "URG-001",
                "to_location": "CARDIO-001",
                "when_offset_hours": 2  # 2h après admission
            },
            delay_seconds=7200  # Attendre 2h en temps simulé
        )
    ]
)
```

### 2. **Exécution d'un scénario** (runtime)

```python
from app.services.workflow_executor import execute_scenario

# Exécuter le scénario
execution = await execute_scenario(
    session=session,
    scenario=scenario,
    ght_context_id=1,
    emit_hl7=True,      # Émettre les messages HL7 PAM
    emit_fhir=True,     # Émettre les ressources FHIR
    hl7_endpoint=mllp_endpoint,
    fhir_endpoint=fhir_endpoint
)

# Résultat
print(f"Scénario exécuté: {execution.status}")
print(f"Patient créé: {execution.patient_id}")
print(f"Dossier créé: {execution.dossier_id}")
print(f"Messages HL7 émis: {len([s for s in execution.steps if s.hl7_message_id])}")
print(f"Ressources FHIR émises: {len([s for s in execution.steps if s.fhir_message_id])}")
```

### 3. **Génération HL7 PAM à partir des données**

```python
from app.services.hl7_generator import generate_adt_message

# Générer ADT^A01 (Admission)
hl7_message = generate_adt_message(
    patient=patient,
    dossier=dossier,
    venue=venue,
    message_type="A01",
    namespaces=ght.namespaces
)

# Le message est généré dynamiquement avec dates actuelles
# Plus besoin de update_hl7_message_dates()
```

### 4. **Génération FHIR à partir des données**

```python
from app.services.fhir_generator import generate_fhir_bundle

# Générer un Bundle FHIR
fhir_bundle = generate_fhir_bundle(
    patient=patient,
    dossier=dossier,
    venue=venue,
    encounter_class="emergency"
)

# POST vers serveur FHIR
await post_fhir_bundle(fhir_endpoint, fhir_bundle)
```

## 🗂️ Structure des fichiers

### Nouveaux modèles

```
app/models_workflows.py  (nouveau)
├── WorkflowScenario
├── WorkflowScenarioStep
├── WorkflowScenarioExecution
├── WorkflowExecutionStep
├── ScenarioType (enum)
└── ActionType (enum)
```

### Services

```
app/services/workflow_executor.py  (nouveau)
├── execute_scenario()
├── execute_step()
├── create_patient_from_step()
├── create_dossier_from_step()
├── create_venue_from_step()
├── create_movement_from_step()
└── emit_messages()

app/services/hl7_generator.py  (nouveau)
├── generate_adt_message()
├── generate_msh_segment()
├── generate_pid_segment()
├── generate_pv1_segment()
├── generate_zbe_segment()
└── build_message()

app/services/fhir_generator.py  (améliorer existant)
├── generate_fhir_bundle()
├── generate_patient_resource()
├── generate_encounter_resource()
└── generate_observation_resources()
```

## 🔄 Migration des scénarios existants

### Étape 1 : Analyser les messages HL7 existants

```python
from app.services.hl7_parser import parse_hl7_message

for scenario in session.exec(select(InteropScenario)):
    for step in scenario.steps:
        # Parser le message HL7
        parsed = parse_hl7_message(step.payload)
        
        # Extraire les données
        patient_data = parsed['PID']
        dossier_data = parsed['PV1']
        
        # Créer le nouveau scénario workflow
        workflow = WorkflowScenario(
            name=scenario.name,
            description=scenario.description,
            source_scenario_id=scenario.id  # Traçabilité
        )
        
        # Créer les steps à partir des données extraites
        # ...
```

### Étape 2 : Dupliquer la table (sans suppression)

- Garder `InteropScenario` pour référence historique
- Créer `WorkflowScenario` en parallèle
- Basculer progressivement l'UI et l'API

### Étape 3 : Tester la génération

```bash
# Test unitaire
pytest tests/test_workflow_executor.py

# Test d'intégration
python tools/test_workflow_scenario.py --scenario-id 1 --emit-hl7 --emit-fhir
```

## 💡 Avantages de l'approche

### ✅ **Pour le développement**

1. **Single Source of Truth** : Les données métier sont la source unique
2. **Génération dynamique** : HL7 et FHIR générés à partir des mêmes données
3. **Dates toujours actuelles** : Plus besoin de `update_hl7_message_dates()`
4. **Testabilité** : Tests sur le modèle métier, pas sur du texte

### ✅ **Pour l'interopérabilité**

1. **HL7 PAM** : Généré avec données actuelles et namespaces corrects
2. **FHIR R4** : Généré avec structure validée
3. **Cohérence** : Patient HL7 = Patient FHIR = Patient en base
4. **Traçabilité** : Chaque message lié à son entité source

### ✅ **Pour les utilisateurs**

1. **UI simplifiée** : "Créer une admission" au lieu de "Envoyer message HL7"
2. **Paramétrable** : "Admission en urgence" vs "Admission programmée"
3. **Réutilisable** : Même scénario pour différents patients
4. **Debuggable** : Traçabilité complète des actions

## 🚧 Plan de migration (4 étapes)

### Phase 1 : **Modèles et parsers** (1-2 jours)
- [ ] Créer `app/models_workflows.py`
- [ ] Créer `app/services/hl7_parser.py` (parser HL7 → dict)
- [ ] Créer `app/services/hl7_generator.py` (dict → HL7)
- [ ] Tests unitaires

### Phase 2 : **Workflow executor** (2-3 jours)
- [ ] Créer `app/services/workflow_executor.py`
- [ ] Implémenter `execute_scenario()`
- [ ] Implémenter actions (CREATE_PATIENT, CREATE_DOSSIER, etc.)
- [ ] Tests d'intégration

### Phase 3 : **Migration données** (1 jour)
- [ ] Script de migration `tools/migrate_scenarios_to_workflows.py`
- [ ] Analyser 125 scénarios existants
- [ ] Créer les workflows équivalents
- [ ] Validation

### Phase 4 : **UI et API** (2 jours)
- [ ] Routes `/workflows/scenarios`
- [ ] Formulaires de création de scénario
- [ ] Exécution depuis l'UI
- [ ] Monitoring des exécutions

**Total estimé : 6-8 jours**

## 🎯 Quick Win : Preuve de concept (POC)

Pour valider l'approche sans tout refaire :

```python
# tools/poc_workflow.py

from app.models import Patient, Dossier, Venue
from app.services.hl7_generator import generate_adt_a01

# 1. Créer les entités
patient = Patient(family="DUPONT", given="Jean", ...)
dossier = Dossier(patient_id=patient.id, ...)
venue = Venue(dossier_id=dossier.id, ...)

# 2. Générer HL7 dynamiquement
hl7_msg = generate_adt_a01(patient, dossier, venue, namespaces)

# 3. Envoyer
await send_mllp(host, port, hl7_msg)

# 4. Générer FHIR dynamiquement
fhir_bundle = generate_fhir_bundle(patient, dossier, venue)

# 5. Envoyer
await post_fhir_bundle(fhir_url, fhir_bundle)
```

## 🤔 Questions pour décision

1. **Priorité** : Voulez-vous cette refonte maintenant ou continuer avec l'existant ?
2. **Scope** : POC d'abord ou migration complète ?
3. **Compatibilité** : Garder les anciens scénarios en lecture seule ?
4. **Timeline** : 1-2 semaines de développement acceptable ?

---

**Recommandation** : Je suggère de commencer par un **POC** sur 1-2 scénarios pour valider l'approche avant de migrer les 125 scénarios existants.
