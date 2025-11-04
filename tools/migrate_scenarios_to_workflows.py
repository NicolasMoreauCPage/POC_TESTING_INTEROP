"""
Migration des scénarios IHE vers workflows.

Ce script analyse tous les scénarios IHE existants (InteropScenario) et crée
des workflows équivalents (WorkflowScenario) avec des étapes métier.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from sqlmodel import Session, select
from app.db import engine
from app.models_scenarios import InteropScenario, InteropScenarioStep
from app.models_workflows import (
    WorkflowScenario,
    WorkflowScenarioStep,
    ScenarioType,
    ActionType
)
from app.services.hl7_parser import parse_hl7_message, extract_scenario_metadata


def migrate_scenario(
    old_scenario: InteropScenario,
    session: Session
) -> WorkflowScenario:
    """
    Migre un InteropScenario vers WorkflowScenario.
    
    Args:
        old_scenario: Scénario IHE existant
        session: Session DB
    
    Returns:
        Nouveau WorkflowScenario créé
    """
    print(f"  Migration: {old_scenario.name} (ID: {old_scenario.id})")
    
    # Analyser la première étape pour extraire métadonnées
    metadata = {"name": old_scenario.name, "scenario_type": "OTHER", "category": None}
    
    if old_scenario.steps:
        first_step = old_scenario.steps[0]
        if first_step.payload:
            try:
                parsed = parse_hl7_message(first_step.payload)
                metadata = extract_scenario_metadata(parsed)
            except Exception as e:
                print(f"    ⚠ Erreur parsing message: {e}")
    
    # Créer le WorkflowScenario
    workflow = WorkflowScenario(
        name=metadata["name"],
        description=old_scenario.description or f"Migré depuis scénario IHE #{old_scenario.id}",
        scenario_type=metadata["scenario_type"],
        ght_context_id=None,  # À définir selon contexte
        is_active=old_scenario.is_active,
        category=metadata.get("category"),
        source_scenario_id=old_scenario.id,
        created_at=datetime.utcnow()
    )
    
    session.add(workflow)
    session.flush()  # Pour obtenir l'ID
    
    # Créer les étapes du workflow
    for idx, old_step in enumerate(old_scenario.steps):
        # Déterminer l'action basée sur le message_type
        action_type = ActionType.EMIT_HL7  # Par défaut
        
        trigger_event = old_step.message_type or ""
        if "A01" in trigger_event:
            action_type = ActionType.CREATE_DOSSIER
        elif "A02" in trigger_event:
            action_type = ActionType.CREATE_MOVEMENT
        elif "A03" in trigger_event:
            action_type = ActionType.CLOSE_DOSSIER
        elif "A08" in trigger_event:
            action_type = ActionType.UPDATE_DOSSIER
        elif "A11" in trigger_event:
            action_type = ActionType.CANCEL_DOSSIER
        
        # Paramètres basés sur le payload HL7
        parameters = {
            "hl7_payload": old_step.payload,
            "message_type": old_step.message_type,
            "message_format": old_step.message_format,
            "legacy_mode": True  # Indique qu'on utilise le payload HL7 existant
        }
        
        # Parser le message pour extraire plus de données
        if old_step.payload:
            try:
                parsed = parse_hl7_message(old_step.payload)
                
                # Extraire données patient
                if parsed.get("PID"):
                    pid = parsed["PID"]
                    parameters["patient_data"] = {
                        "family": pid.get("family", ""),
                        "given": pid.get("given", ""),
                        "birth_date": pid.get("birth_date").isoformat() if pid.get("birth_date") else None,
                        "gender": pid.get("gender", "")
                    }
                
                # Extraire données dossier
                if parsed.get("PV1"):
                    pv1 = parsed["PV1"]
                    parameters["dossier_data"] = {
                        "patient_class": pv1.get("patient_class", "I"),
                        "uf_responsabilite": pv1.get("uf_responsabilite", ""),
                        "visit_number": pv1.get("visit_number", "")
                    }
                
                # Extraire données mouvement
                if parsed.get("ZBE"):
                    zbe = parsed["ZBE"]
                    parameters["movement_data"] = {
                        "movement_id": zbe.get("movement_id", ""),
                        "movement_datetime": zbe.get("movement_datetime").isoformat() if zbe.get("movement_datetime") else None,
                        "uf_responsabilite": zbe.get("uf_responsabilite", "")
                    }
            except Exception as e:
                print(f"    ⚠ Erreur parsing étape {idx}: {e}")
        
        workflow_step = WorkflowScenarioStep(
            scenario_id=workflow.id,
            order_index=idx,
            action_type=action_type,
            name=old_step.name,
            description=old_step.description,
            parameters=parameters,
            delay_seconds=getattr(old_step, 'delay_seconds', 0) or 0,
            emit_hl7=getattr(old_step, 'send_message', True),
            emit_fhir=False  # Par défaut, pas de FHIR pour les anciens scénarios
        )
        
        session.add(workflow_step)
    
    print(f"    ✓ Workflow créé: {workflow.name} avec {len(old_scenario.steps)} étapes")
    
    return workflow


def main():
    """Migre tous les scénarios IHE vers workflows."""
    print("="*70)
    print("MIGRATION DES SCÉNARIOS IHE VERS WORKFLOWS")
    print("="*70)
    
    with Session(engine) as session:
        # Récupérer tous les scénarios IHE
        old_scenarios = session.exec(select(InteropScenario)).all()
        
        print(f"\n✓ {len(old_scenarios)} scénarios IHE trouvés")
        
        if not old_scenarios:
            print("⚠ Aucun scénario à migrer")
            return
        
        # Vérifier si des workflows existent déjà
        existing_workflows = session.exec(select(WorkflowScenario)).all()
        
        if existing_workflows:
            print(f"\n⚠ {len(existing_workflows)} workflows existent déjà")
            response = input("Supprimer et recréer ? (y/N): ")
            if response.lower() == "y":
                print("  Suppression des workflows existants...")
                for wf in existing_workflows:
                    session.delete(wf)
                session.commit()
                print("  ✓ Workflows supprimés")
            else:
                print("  Migration annulée")
                return
        
        print("\n" + "="*70)
        print("MIGRATION EN COURS")
        print("="*70)
        
        migrated_count = 0
        error_count = 0
        
        for old_scenario in old_scenarios:
            try:
                workflow = migrate_scenario(old_scenario, session)
                migrated_count += 1
            except Exception as e:
                print(f"  ✗ Erreur migration {old_scenario.name}: {e}")
                error_count += 1
        
        # Commit final
        session.commit()
        
        print("\n" + "="*70)
        print("RÉSULTATS DE LA MIGRATION")
        print("="*70)
        print(f"✓ Scénarios migrés: {migrated_count}")
        print(f"✗ Erreurs: {error_count}")
        
        # Statistiques
        workflows = session.exec(select(WorkflowScenario)).all()
        print(f"\n✓ Total workflows en base: {len(workflows)}")
        
        # Répartition par type
        type_counts = {}
        for wf in workflows:
            type_counts[wf.scenario_type] = type_counts.get(wf.scenario_type, 0) + 1
        
        print("\nRépartition par type:")
        for scenario_type, count in sorted(type_counts.items()):
            print(f"  • {scenario_type}: {count}")
        
        # Répartition par catégorie
        category_counts = {}
        for wf in workflows:
            cat = wf.category or "SANS_CATEGORIE"
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        print("\nRépartition par catégorie:")
        for category, count in sorted(category_counts.items()):
            print(f"  • {category}: {count}")
        
        print("\n" + "="*70)
        print("✓ MIGRATION TERMINÉE AVEC SUCCÈS")
        print("="*70)
        print("\nProchaines étapes:")
        print("1. Vérifier les workflows créés dans l'UI")
        print("2. Tester l'exécution d'un workflow (POC)")
        print("3. Adapter les routes API pour utiliser les workflows")


if __name__ == "__main__":
    main()
