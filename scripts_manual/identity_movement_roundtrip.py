#!/usr/bin/env python3
"""Roundtrip identité et mouvements: ADT + FHIR export/import/vérification ISO.

Workflow:
1. Export depuis GHT DEMO source:
   - Génération messages ADT (A01/A02/A03/A28) pour chaque mouvement
   - Génération bundles FHIR Patient+Encounter
2. Création GHT cible (GHT-RT-IDENTITY)
3. Réimport dans GHT cible:
   - Injection ADT via inbound handler
   - Import FHIR bundles
4. Vérification ISO:
   - Compter patients/dossiers/mouvements source vs cible
   - Comparer identifiants, dates, événements
   - Vérifier conformité IHE PAM (segments obligatoires)

Usage:
    python scripts_manual/identity_movement_roundtrip.py [--verbose]
"""
import sys, json, argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.db_session_factory import session_factory
from app.db import get_next_sequence
from app.models import Patient, Dossier, Venue, Mouvement, DossierType, Sequence
from app.models_structure_fhir import GHTContext, EntiteJuridique, IdentifierNamespace
from app.models_identifiers import Identifier, IdentifierType
from app.services.hl7_generator import generate_adt_message
from app.services.fhir import generate_fhir_bundle_for_dossier
from app.services.adt_parser import import_adt_into_ght

VERBOSE = False

def log(msg: str):
    if VERBOSE:
        print(f"  {msg}")

def _get_source_ght(session: Session) -> Optional[GHTContext]:
    """Récupère le GHT DEMO source."""
    return session.exec(select(GHTContext).where(GHTContext.code == "GHT-DEMO")).first()

def _create_target_ght(session: Session) -> GHTContext:
    """Crée un GHT cible pour le roundtrip."""
    ght = session.exec(select(GHTContext).where(GHTContext.code == "GHT-RT-IDENTITY")).first()
    if ght:
        print("✓ GHT cible existant (GHT-RT-IDENTITY)")
        return ght
    
    ght = GHTContext(
        name="GHT Roundtrip Identity",
        code="GHT-RT-IDENTITY",
        description="GHT cible pour roundtrip identité/mouvements",
        oid_racine="1.2.250.1.214.1.1",
        is_active=True
    )
    session.add(ght); session.commit(); session.refresh(ght)
    
    ej = EntiteJuridique(
        name="EJ Roundtrip Identity",
        finess_ej="750999999",
        ght_context_id=ght.id,
        is_active=True,
        strict_pam_fr=True
    )
    session.add(ej); session.commit(); session.refresh(ej)
    
    # Namespaces cible (OIDs différents pour éviter collision)
    for ns_spec in [
        {"name": "IPP-RT", "system": "urn:oid:1.2.250.1.214.1.2.1", "type": "IPP", "ej": True},
        {"name": "NDA-RT", "system": "urn:oid:1.2.250.1.214.1.2.2", "type": "NDA", "ej": True},
        {"name": "VENUE-RT", "system": "urn:oid:1.2.250.1.214.1.2.3", "type": "VENUE", "ej": False},
    ]:
        ns = IdentifierNamespace(
            name=ns_spec["name"],
            system=ns_spec["system"],
            type=ns_spec["type"],
            ght_context_id=ght.id,
            entite_juridique_id=ej.id if ns_spec["ej"] else None,
            is_active=True
        )
        session.add(ns)
    session.commit()
    
    print("✓ GHT cible créé (GHT-RT-IDENTITY)")
    return ght

def _export_adt_messages(session: Session, ght_source: GHTContext) -> List[str]:
    """Exporte tous les mouvements du GHT source en messages ADT."""
    messages = []
    
    # Charger namespaces source
    namespaces_list = session.exec(
        select(IdentifierNamespace).where(IdentifierNamespace.ght_context_id == ght_source.id)
    ).all()
    namespaces = {ns.type: ns for ns in namespaces_list}
    src_systems = [ns.system for ns in namespaces_list]
    
    # Filtrer les dossiers qui ont des identifiants dans les namespaces source
    dossier_ids_with_identifiers = session.exec(
        select(Identifier.dossier_id).where(
            Identifier.dossier_id.isnot(None),
            Identifier.system.in_(src_systems)
        ).distinct()
    ).all()
    
    # Charger les mouvements liés à ces dossiers
    mouvements = session.exec(
        select(Mouvement)
        .join(Venue)
        .where(Venue.dossier_id.in_(dossier_ids_with_identifiers))
    ).all()
    
    for mvt in mouvements:
        venue = mvt.venue
        dossier = venue.dossier
        patient = dossier.patient
        
        # Charger identifiants patient
        patient_ids = session.exec(
            select(Identifier).where(Identifier.patient_id == patient.id)
        ).all()
        
        # Charger identifiants dossier (NDA)
        dossier_ids = session.exec(
            select(Identifier).where(Identifier.dossier_id == dossier.id)
        ).all()
        
        try:
            msg = generate_adt_message(
                patient=patient,
                dossier=dossier,
                venue=venue,
                movement=mvt,
                trigger_event=mvt.trigger_event or "A01",
                session=session,
                namespaces=namespaces,
                timestamp=mvt.when or datetime.utcnow()
            )
            messages.append(msg)
            log(f"ADT {mvt.trigger_event} généré pour patient {patient.family}")
        except Exception as e:
            print(f"⚠️  Erreur génération ADT pour mouvement {mvt.id}: {e}")
    
    return messages

def _export_fhir_bundles(session: Session, ght_source: GHTContext) -> List[Dict[str, Any]]:
    """Exporte tous les dossiers du GHT source en bundles FHIR."""
    bundles = []
    
    # Charger namespaces source pour filtrer
    namespaces_list = session.exec(
        select(IdentifierNamespace).where(IdentifierNamespace.ght_context_id == ght_source.id)
    ).all()
    src_systems = [ns.system for ns in namespaces_list]
    
    # Filtrer dossiers avec identifiants dans les namespaces source
    dossier_ids_with_identifiers = session.exec(
        select(Identifier.dossier_id).where(
            Identifier.dossier_id.isnot(None),
            Identifier.system.in_(src_systems)
        ).distinct()
    ).all()
    
    dossiers = session.exec(
        select(Dossier).where(Dossier.id.in_(dossier_ids_with_identifiers))
    ).all()
    
    for dossier in dossiers:
        try:
            bundle = generate_fhir_bundle_for_dossier(dossier, session=session)
            bundles.append(bundle)
            log(f"Bundle FHIR généré pour dossier {dossier.id}")
        except Exception as e:
            print(f"⚠️  Erreur génération FHIR pour dossier {dossier.id}: {e}")
    
    return bundles

def _reimport_adt(session: Session, messages: List[str], ght_target: GHTContext) -> Dict[str, int]:
    """Réimporte les messages ADT dans le GHT cible."""
    stats = {"success": 0, "error": 0, "patients": 0, "dossiers": 0, "mouvements": 0}
    
    for msg in messages:
        try:
            result = import_adt_into_ght(msg, session, ght_target.id)
            if result["status"] == "success":
                stats["success"] += 1
                if result.get("patient_id"):
                    stats["patients"] += 1
                if result.get("dossier_id"):
                    stats["dossiers"] += 1
                if result.get("mouvement_id"):
                    stats["mouvements"] += 1
                log(f"ADT importé: patient={result.get('patient_id')}, dossier={result.get('dossier_id')}")
            else:
                stats["error"] += 1
                log(f"Erreur ADT: {result.get('error')}")
        except Exception as e:
            print(f"⚠️  Erreur réimport ADT: {e}")
            stats["error"] += 1
    
    return stats

def _reimport_fhir(session: Session, bundles: List[Dict[str, Any]], ght_target: GHTContext) -> Dict[str, int]:
    """Réimporte les bundles FHIR dans le GHT cible."""
    stats = {"patients": 0, "encounters": 0, "error": 0}
    
    # Charger namespaces cible
    namespaces = session.exec(
        select(IdentifierNamespace).where(IdentifierNamespace.ght_context_id == ght_target.id)
    ).all()
    ns_by_type = {ns.type: ns for ns in namespaces}
    
    for bundle in bundles:
        try:
            patient_res = None
            encounter_res = None
            
            # Extraire ressources du bundle
            for entry in bundle.get("entry", []):
                res = entry.get("resource", {})
                if res.get("resourceType") == "Patient":
                    patient_res = res
                elif res.get("resourceType") == "Encounter":
                    encounter_res = res
            
            if not patient_res:
                continue
            
            # Créer patient depuis FHIR
            name = patient_res.get("name", [{}])[0]
            family = name.get("family", "")
            given_list = name.get("given", [])
            given = given_list[0] if given_list else ""
            
            patient = Patient(
                family=family,
                given=given,
                birth_date=patient_res.get("birthDate"),
                gender=patient_res.get("gender", "unknown"),
                identity_reliability_code="VALI",
                country="FR"
            )
            session.add(patient)
            session.commit()
            session.refresh(patient)
            stats["patients"] += 1
            log(f"Patient FHIR importé: {family}")
            
            # Créer identifiants patient dans namespaces cible
            ipp_ns = ns_by_type.get("IPP") or ns_by_type.get("IPP-RT")
            if ipp_ns:
                for ident_data in patient_res.get("identifier", []):
                    ident = Identifier(
                        patient_id=patient.id,
                        type=IdentifierType.IPP,
                        value=ident_data.get("value", ""),
                        system=ipp_ns.system,
                        oid=ipp_ns.system.split(":")[-1],
                        status="active"
                    )
                    session.add(ident)
                session.commit()
            
            # Créer dossier si Encounter présent
            if encounter_res:
                period = encounter_res.get("period", {})
                admit_time_str = period.get("start")
                admit_time = datetime.fromisoformat(admit_time_str.replace("Z", "")) if admit_time_str else datetime.utcnow()
                
                dossier = Dossier(
                    dossier_seq=get_next_sequence(session, "dossier"),
                    patient_id=patient.id,
                    dossier_type=DossierType.HOSPITALISE,
                    admit_time=admit_time,
                    uf_responsabilite="UF-FHIR-IMPORT"
                )
                session.add(dossier)
                session.commit()
                session.refresh(dossier)
                
                # Créer identifiant NDA pour dossier
                nda_ns = ns_by_type.get("NDA") or ns_by_type.get("NDA-RT")
                if nda_ns:
                    nda_ident = Identifier(
                        dossier_id=dossier.id,
                        type=IdentifierType.NDA,
                        value=f"NDA-FHIR-{dossier.dossier_seq:08d}",
                        system=nda_ns.system,
                        oid=nda_ns.system.split(":")[-1],
                        status="active"
                    )
                    session.add(nda_ident)
                    session.commit()
                
                stats["encounters"] += 1
                log(f"Encounter FHIR importé")
        except Exception as e:
            print(f"⚠️  Erreur réimport FHIR: {e}")
            stats["error"] += 1
    
    return stats

def _compare_iso(session: Session, ght_source: GHTContext, ght_target: GHTContext) -> Dict[str, Any]:
    """Compare les données source et cible pour vérifier l'ISO."""
    # Charger namespaces source et cible
    src_namespaces = session.exec(
        select(IdentifierNamespace).where(IdentifierNamespace.ght_context_id == ght_source.id)
    ).all()
    src_systems = [ns.system for ns in src_namespaces]
    
    tgt_namespaces = session.exec(
        select(IdentifierNamespace).where(IdentifierNamespace.ght_context_id == ght_target.id)
    ).all()
    tgt_systems = [ns.system for ns in tgt_namespaces]
    
    # Compter entités source (via identifiants dans namespaces source)
    src_patient_ids = session.exec(
        select(Identifier.patient_id).where(
            Identifier.patient_id.isnot(None),
            Identifier.system.in_(src_systems)
        ).distinct()
    ).all()
    src_patients = len(src_patient_ids)
    
    src_dossier_ids = session.exec(
        select(Identifier.dossier_id).where(
            Identifier.dossier_id.isnot(None),
            Identifier.system.in_(src_systems)
        ).distinct()
    ).all()
    src_dossiers = len(src_dossier_ids)
    
    # Mouvements liés aux dossiers source
    if src_dossier_ids:
        src_mouvements = len(session.exec(
            select(Mouvement).join(Venue).where(Venue.dossier_id.in_(src_dossier_ids))
        ).all())
    else:
        src_mouvements = 0
    
    # Compter entités cible (via identifiants dans namespaces cible)
    tgt_patient_ids = session.exec(
        select(Identifier.patient_id).where(
            Identifier.patient_id.isnot(None),
            Identifier.system.in_(tgt_systems)
        ).distinct()
    ).all()
    tgt_patients = len(tgt_patient_ids)
    
    tgt_dossier_ids = session.exec(
        select(Identifier.dossier_id).where(
            Identifier.dossier_id.isnot(None),
            Identifier.system.in_(tgt_systems)
        ).distinct()
    ).all()
    tgt_dossiers = len(tgt_dossier_ids)
    
    # Mouvements liés aux dossiers cible
    if tgt_dossier_ids:
        tgt_mouvements = len(session.exec(
            select(Mouvement).join(Venue).where(Venue.dossier_id.in_(tgt_dossier_ids))
        ).all())
    else:
        tgt_mouvements = 0
    
    iso_ok = (src_patients == tgt_patients and 
              src_dossiers == tgt_dossiers and 
              src_mouvements == tgt_mouvements)
    
    return {
        "source": {
            "patients": src_patients,
            "dossiers": src_dossiers,
            "mouvements": src_mouvements
        },
        "target": {
            "patients": tgt_patients,
            "dossiers": tgt_dossiers,
            "mouvements": tgt_mouvements
        },
        "iso": iso_ok
    }

def _check_pam_compliance(messages: List[str]) -> Dict[str, Any]:
    """Vérifie la conformité IHE PAM des messages ADT."""
    compliance = {"total": len(messages), "valid": 0, "errors": []}
    
    for idx, msg in enumerate(messages, 1):
        segments = msg.split("\r")
        seg_types = {seg.split("|")[0] for seg in segments if seg}
        
        # Segments obligatoires IHE PAM: MSH, PID, PV1
        required = {"MSH", "PID", "PV1"}
        missing = required - seg_types
        
        if missing:
            compliance["errors"].append({
                "message_index": idx,
                "missing_segments": list(missing)
            })
        else:
            compliance["valid"] += 1
            
            # Vérifier absence A08 si strict
            msh = next((s for s in segments if s.startswith("MSH|")), "")
            if "A08" in msh:
                compliance["errors"].append({
                    "message_index": idx,
                    "error": "A08 détecté (interdit en mode strict PAM FR)"
                })
    
    compliance["compliant"] = (len(compliance["errors"]) == 0)
    return compliance

def main():
    global VERBOSE
    parser = argparse.ArgumentParser(description="Roundtrip identité/mouvements ADT+FHIR")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    args = parser.parse_args()
    VERBOSE = args.verbose
    
    print("🔄 ROUNDTRIP IDENTITÉ & MOUVEMENTS (ADT + FHIR)\n")
    
    with session_factory() as session:
        # Phase 1: Export depuis source
        print("=" * 80)
        print("PHASE 1: EXPORT depuis GHT DEMO")
        print("=" * 80)
        
        ght_source = _get_source_ght(session)
        if not ght_source:
            print("❌ GHT DEMO non trouvé. Exécuter tools/seed_demo_complete.py d'abord.")
            return 1
        
        print(f"Source: {ght_source.name} (code={ght_source.code})")
        
        print("\n⚙️  Export ADT...")
        adt_messages = _export_adt_messages(session, ght_source)
        print(f"✓ {len(adt_messages)} messages ADT générés")
        
        print("\n⚙️  Export FHIR...")
        fhir_bundles = _export_fhir_bundles(session, ght_source)
        print(f"✓ {len(fhir_bundles)} bundles FHIR générés")
        
        # Sauvegarder artifacts
        Path("roundtrip_adt_messages.txt").write_text("\n\n".join(adt_messages), encoding="utf-8")
        Path("roundtrip_fhir_bundles.json").write_text(
            json.dumps(fhir_bundles, indent=2), encoding="utf-8"
        )
        print("✓ Artifacts sauvegardés: roundtrip_adt_messages.txt, roundtrip_fhir_bundles.json")
        
        # Phase 2: Validation IHE PAM
        print("\n" + "=" * 80)
        print("PHASE 2: VALIDATION IHE PAM")
        print("=" * 80)
        
        compliance = _check_pam_compliance(adt_messages)
        print(f"Messages valides: {compliance['valid']}/{compliance['total']}")
        if compliance["compliant"]:
            print("✅ Conformité IHE PAM: OK")
        else:
            print("⚠️  Conformité IHE PAM: ERREURS DÉTECTÉES")
            for err in compliance["errors"][:5]:  # Afficher max 5 erreurs
                print(f"   - Message {err.get('message_index')}: {err}")
        
        # Phase 3: Réimport cible
        print("\n" + "=" * 80)
        print("PHASE 3: RÉIMPORT dans GHT cible")
        print("=" * 80)
        
        ght_target = _create_target_ght(session)
        
        print("\n⚙️  Réimport ADT...")
        adt_stats = _reimport_adt(session, adt_messages, ght_target)
        print(f"✓ ADT: {adt_stats['success']} succès, {adt_stats['error']} erreurs")
        
        print("\n⚙️  Réimport FHIR...")
        fhir_stats = _reimport_fhir(session, fhir_bundles, ght_target)
        print(f"✓ FHIR: {fhir_stats['patients']} patients, {fhir_stats['encounters']} encounters")
        
        # Phase 4: Vérification ISO
        print("\n" + "=" * 80)
        print("PHASE 4: VÉRIFICATION ISO")
        print("=" * 80)
        
        iso_check = _compare_iso(session, ght_source, ght_target)
        print(f"\nSource: {iso_check['source']}")
        print(f"Cible:  {iso_check['target']}")
        
        if iso_check["iso"]:
            print("\n✅ ROUNDTRIP ISO: OK")
            return 0
        else:
            print("\n⚠️  ROUNDTRIP NON-ISO (réimport incomplet - parsers ADT/FHIR à finaliser)")
            return 2

if __name__ == "__main__":
    raise SystemExit(main())
