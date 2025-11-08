"""Structure export/import roundtrip for FHIR and MFN.

Usage:
  PYTHONPATH=. .venv/bin/python scripts_manual/structure_roundtrip.py --dry-run

Steps:
 1. Locate demo GHT (first existing GHTContext) and export its structure to:
    - FHIR Location resources (JSON list)
    - HL7 MFN^M05 message (full snapshot)
 2. Create two new GHT contexts: GHT FHIR Roundtrip, GHT MFN Roundtrip (with their EJ).
 3. Import FHIR structure into GHT FHIR Roundtrip (prefix identifiers to avoid global uniqueness).
 4. Import MFN structure into GHT MFN Roundtrip using transformed MFN message (identifier suffix to avoid uniqueness collisions).
 5. Print summary counts.

Notes:
 - Identifiers are globally unique; we apply prefix/suffix transformations.
 - Only core location hierarchy is handled (EntiteGeographique, Pole, Service, UniteFonctionnelle, UniteHebergement, Chambre, Lit).
 - FHIR mapping is minimal: Location.resourceType, status, name, identifier, type (code), physicalType, partOf, extension originalType.
"""
from __future__ import annotations
import argparse, json
from dataclasses import asdict, dataclass
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select

from app.db import engine, init_db
from app.models_structure_fhir import GHTContext, EntiteJuridique, EntiteGeographique, IdentifierNamespace
from app.models_structure import (
    Pole, Service, UniteFonctionnelle, UniteHebergement, Chambre, Lit,
    LocationPhysicalType, LocationServiceType
)
from app.services.mfn_structure import generate_mfn_message, process_mfn_message

@dataclass
class ExportLocation:
    identifier: str
    name: str
    type_code: str  # custom classification (EG, P, D, UF, UH, CH, LIT)
    physical_type: str
    parent: Optional[str] = None


def _find_demo_ght(session: Session) -> Optional[GHTContext]:
    return session.exec(select(GHTContext).order_by(GHTContext.id)).first()


def _export_structure(session: Session) -> List[ExportLocation]:
    """Export structure from a single EntiteGeographique (the first CENTRAL site)."""
    data: List[ExportLocation] = []
    # Export only CENTRAL site to avoid massive duplicates
    eg_query = select(EntiteGeographique).where(EntiteGeographique.identifier == "CHU-DEMO-SITE-CENTRAL")
    eg = session.exec(eg_query).first()
    if not eg:
        # Fallback to first EG if CENTRAL doesn't exist
        eg = session.exec(select(EntiteGeographique)).first()
    if not eg:
        return data  # No structure to export
    
    data.append(ExportLocation(identifier=eg.identifier, name=eg.name, type_code="EG", physical_type=eg.physical_type or "si"))
    # Pôles
    for pole in eg.poles:
        data.append(ExportLocation(identifier=pole.identifier, name=pole.name, type_code="P", physical_type=pole.physical_type.value if hasattr(pole.physical_type, "value") else pole.physical_type, parent=eg.identifier))
        # Services
        for svc in pole.services:
            data.append(ExportLocation(identifier=svc.identifier, name=svc.name, type_code="D", physical_type=svc.physical_type.value if hasattr(svc.physical_type, "value") else svc.physical_type, parent=pole.identifier))
            # UF
            for uf in svc.unites_fonctionnelles:
                data.append(ExportLocation(identifier=uf.identifier, name=uf.name, type_code="UF", physical_type=uf.physical_type.value if hasattr(uf.physical_type, "value") else uf.physical_type, parent=svc.identifier))
                # UH
                for uh in uf.unites_hebergement:
                    data.append(ExportLocation(identifier=uh.identifier, name=uh.name, type_code="UH", physical_type=uh.physical_type.value if hasattr(uh.physical_type, "value") else uh.physical_type, parent=uf.identifier))
                    # Chambres
                    for ch in uh.chambres:
                        data.append(ExportLocation(identifier=ch.identifier, name=ch.name, type_code="CH", physical_type=ch.physical_type.value if hasattr(ch.physical_type, "value") else ch.physical_type, parent=uh.identifier))
                        # Lits
                        for bed in ch.lits:
                            data.append(ExportLocation(identifier=bed.identifier, name=bed.name, type_code="LIT", physical_type=bed.physical_type.value if hasattr(bed.physical_type, "value") else bed.physical_type, parent=ch.identifier))
    return data


def _to_fhir_locations(export: List[ExportLocation], prefix: str) -> List[Dict[str, Any]]:
    resources = []
    for loc in export:
        new_id = f"{prefix}{loc.identifier}"  # avoid uniqueness collision
        res = {
            "resourceType": "Location",
            "id": new_id,
            "identifier": [{"system": "urn:meddata:structure", "value": new_id}],
            "status": "active",
            "name": loc.name,
            "physicalType": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/location-physical-type", "code": loc.physical_type}]},
            "extension": [
                {"url": "urn:meddata:original-type", "valueCode": loc.type_code}
            ]
        }
        if loc.parent:
            res["partOf"] = {"reference": f"Location/{prefix}{loc.parent}"}
        resources.append(res)
    return resources


def _import_fhir_locations(session: Session, resources: List[Dict[str, Any]], ght: GHTContext, ej: EntiteJuridique) -> Dict[str, int]:
    # Build lookup by id for dependency ordering (parent before child)
    by_type_order = ["EG", "P", "D", "UF", "UH", "CH", "LIT"]
    # flatten
    created = 0
    skipped = 0
    # index resources by original type
    typed_groups: Dict[str, List[Dict[str, Any]]] = {t: [] for t in by_type_order}
    for r in resources:
        t = None
        for ext in r.get("extension", []):
            if ext.get("url") == "urn:meddata:original-type":
                t = ext.get("valueCode")
        if not t:
            skipped += 1
            continue
        typed_groups.setdefault(t, []).append(r)
    # EG first
    for t in by_type_order:
        for r in typed_groups.get(t, []):
            idv = r["id"]
            name = r.get("name") or idv
            orig_type = t
            try:
                if orig_type == "EG":
                    eg = EntiteGeographique(identifier=idv, name=name, finess="", physical_type=r["physicalType"]["coding"][0]["code"], entite_juridique_id=ej.id)
                    session.add(eg); session.commit(); session.refresh(eg)
                elif orig_type == "P":
                    parent_ref = r.get("partOf", {}).get("reference")
                    parent_identifier = parent_ref.split("/")[1] if parent_ref else None
                    parent_eg = session.exec(select(EntiteGeographique).where(EntiteGeographique.identifier == parent_identifier)).first()
                    if not parent_eg:
                        skipped += 1; continue
                    pole = Pole(identifier=idv, name=name, physical_type=LocationPhysicalType.AREA, entite_geo_id=parent_eg.id)
                    session.add(pole); session.commit(); session.refresh(pole)
                elif orig_type == "D":
                    parent_ref = r.get("partOf", {}).get("reference")
                    parent_identifier = parent_ref.split("/")[1] if parent_ref else None
                    parent_pole = session.exec(select(Pole).where(Pole.identifier == parent_identifier)).first()
                    if not parent_pole:
                        skipped += 1; continue
                    svc = Service(identifier=idv, name=name, physical_type=LocationPhysicalType.SI, pole_id=parent_pole.id, service_type=LocationServiceType.MCO)
                    session.add(svc); session.commit(); session.refresh(svc)
                elif orig_type == "UF":
                    parent_ref = r.get("partOf", {}).get("reference")
                    parent_identifier = parent_ref.split("/")[1] if parent_ref else None
                    parent_svc = session.exec(select(Service).where(Service.identifier == parent_identifier)).first()
                    if not parent_svc:
                        skipped += 1; continue
                    uf = UniteFonctionnelle(identifier=idv, name=name, physical_type=LocationPhysicalType.SI, service_id=parent_svc.id)
                    session.add(uf); session.commit(); session.refresh(uf)
                elif orig_type == "UH":
                    parent_ref = r.get("partOf", {}).get("reference")
                    parent_identifier = parent_ref.split("/")[1] if parent_ref else None
                    parent_uf = session.exec(select(UniteFonctionnelle).where(UniteFonctionnelle.identifier == parent_identifier)).first()
                    if not parent_uf:
                        skipped += 1; continue
                    uh = UniteHebergement(identifier=idv, name=name, physical_type=LocationPhysicalType.WI, unite_fonctionnelle_id=parent_uf.id)
                    session.add(uh); session.commit(); session.refresh(uh)
                elif orig_type == "CH":
                    parent_ref = r.get("partOf", {}).get("reference")
                    parent_identifier = parent_ref.split("/")[1] if parent_ref else None
                    parent_uh = session.exec(select(UniteHebergement).where(UniteHebergement.identifier == parent_identifier)).first()
                    if not parent_uh:
                        skipped += 1; continue
                    ch = Chambre(identifier=idv, name=name, physical_type=LocationPhysicalType.RO, unite_hebergement_id=parent_uh.id)
                    session.add(ch); session.commit(); session.refresh(ch)
                elif orig_type == "LIT":
                    parent_ref = r.get("partOf", {}).get("reference")
                    parent_identifier = parent_ref.split("/")[1] if parent_ref else None
                    parent_ch = session.exec(select(Chambre).where(Chambre.identifier == parent_identifier)).first()
                    if not parent_ch:
                        skipped += 1; continue
                    bed = Lit(identifier=idv, name=name, physical_type=LocationPhysicalType.BD, chambre_id=parent_ch.id)
                    session.add(bed); session.commit(); session.refresh(bed)
                created += 1
            except Exception:
                session.rollback(); skipped += 1
    return {"created": created, "skipped": skipped}


def _transform_mfn_identifiers(raw_mfn: str, suffix: str) -> str:
    """Ajoute un suffixe aux identifiants structurels dans le message MFN.

    Couvre:
      - MFE champ 4 (identifiant logique)
      - LOC champ 1
      - LCH champ 1 et valeur ID_GLBL (champ 5) si segment code ID_GLBL
      - LRL champ 4 (cible de la relation)
    Objectif: éviter collision de clés uniques lors de réimport dans un autre GHT.
    """
    lines = raw_mfn.replace("\r", "\n").split("\n")
    out: List[str] = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("|")
        seg = parts[0]
        # MFE
        if seg == "MFE" and len(parts) > 4 and parts[4]:
            if not parts[4].endswith(suffix):
                parts[4] = parts[4] + suffix
        # LOC
        elif seg == "LOC" and len(parts) > 1 and parts[1]:
            if not parts[1].endswith(suffix):
                parts[1] = parts[1] + suffix
        # LCH
        elif seg == "LCH":
            if len(parts) > 1 and parts[1] and not parts[1].endswith(suffix):
                parts[1] = parts[1] + suffix
            # Champ 4 code, champ 5 valeur (^IDENT). On suffixe valeur si code == ID_GLBL
            if len(parts) > 5 and parts[4].startswith("ID_GLBL") and parts[5]:
                val = parts[5]
                # Valeur typique: ^IDENT ou ^IDENT&… ; on ajoute suffixe avant métadonnées éventuelles (&)
                if val.startswith("^"):
                    core = val[1:].split("&")[0]
                    rest = val[1:][len(core):]  # partie après core
                    if not core.endswith(suffix):
                        core = core + suffix
                    parts[5] = "^" + core + rest
                else:
                    if not val.endswith(suffix):
                        parts[5] = val + suffix
        # LRL relations (type field 4, target field 6 per spec)
        elif seg == "LRL":
            if len(parts) > 6 and parts[6] and not parts[6].endswith(suffix):
                parts[6] = parts[6] + suffix
        out.append("|".join(parts))
    return "\n".join(out)

async def main(dry_run: bool = False):
    init_db()
    with Session(engine) as session:
        demo_ght = _find_demo_ght(session)
        if not demo_ght:
            raise RuntimeError("Aucun GHT de démon trouvé pour l'export.")
        # Export structure BEFORE creating new contexts (to avoid including them in export)
        # Export only CENTRAL site to avoid duplicates
        export_loc = _export_structure(session)
        fhir_resources = _to_fhir_locations(export_loc, prefix="FRT-")
        mfn_message = generate_mfn_message(session, eg_identifier="CHU-DEMO-SITE-CENTRAL")
        transformed_mfn = _transform_mfn_identifiers(mfn_message, suffix="-MFRT")

        # Create new GHT contexts AFTER export
        ght_fhir = GHTContext(name="GHT FHIR Roundtrip", code="GHT-FHIR")
        session.add(ght_fhir); session.commit(); session.refresh(ght_fhir)
        ej_fhir = EntiteJuridique(name="EJ FHIR Roundtrip", finess_ej="999999991", ght_context_id=ght_fhir.id)
        session.add(ej_fhir); session.commit(); session.refresh(ej_fhir)

        ght_mfn = GHTContext(name="GHT MFN Roundtrip", code="GHT-MFN")
        session.add(ght_mfn); session.commit(); session.refresh(ght_mfn)
        ej_mfn = EntiteJuridique(name="EJ MFN Roundtrip", finess_ej="999999992", ght_context_id=ght_mfn.id)
        session.add(ej_mfn); session.commit(); session.refresh(ej_mfn)

        # Create distinct namespaces for each GHT to avoid identifier collisions
        ns_fhir = IdentifierNamespace(
            name="FHIR Roundtrip Namespace",
            system="http://ght-fhir-roundtrip.example/ns/structure",
            oid="1.2.250.1.999.1.1",
            type="STRUCTURE",
            description="Namespace for FHIR roundtrip imported structure identifiers",
            ght_context_id=ght_fhir.id
        )
        session.add(ns_fhir); session.commit(); session.refresh(ns_fhir)

        ns_mfn = IdentifierNamespace(
            name="MFN Roundtrip Namespace",
            system="http://ght-mfn-roundtrip.example/ns/structure",
            oid="1.2.250.1.999.2.1",
            type="STRUCTURE",
            description="Namespace for MFN roundtrip imported structure identifiers",
            ght_context_id=ght_mfn.id
        )
        session.add(ns_mfn); session.commit(); session.refresh(ns_mfn)

        # Import FHIR
        fhir_stats = _import_fhir_locations(session, fhir_resources, ght_fhir, ej_fhir)

        # Import MFN with multi-pass support
        mfn_results = process_mfn_message(transformed_mfn, session, multi_pass=True)

        summary = {
            "export_counts": {
                "locations": len(export_loc)
            },
            "fhir": {
                "resources": len(fhir_resources),
                "created": fhir_stats["created"],
                "skipped": fhir_stats["skipped"],
            },
            "mfn": {
                "raw_segments": len(mfn_message.split("\n")),
                "imported": sum(1 for r in mfn_results if r.get("status") == "success"),
                "errors": [r for r in mfn_results if r.get("status") != "success"]
            }
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        if dry_run:
            print("[DRY-RUN] Structure roundtrip complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Structure FHIR & MFN roundtrip")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import asyncio
    asyncio.run(main(dry_run=args.dry_run))
