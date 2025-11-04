"""
Tests des flux de gestion de structure
Tests parallèles FHIR et HL7 MFN pour la structure
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from datetime import datetime

from app.models_structure import EntiteGeographique, Pole, Service, UniteFonctionnelle
from app.services.mfn_structure import process_mfn_message, generate_mfn_message

def test_import_structure_hl7(client: TestClient, session: Session):
    """Test import structure via HL7 MFN"""
    # Message MFN pour tester l'import
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    message = f"""MSH|^~\\&|STR|STR|RECEPTEUR|RECEPTEUR|{now}||MFN^M05^MFN_M05|{now}|P|2.5|||||FRA|8859/15
MFI|LOC|CPAGE_LOC_FRA|REP||{now}|AL
MFE|MAD|||^^^^^M^^^^69&CPAGE&700004591&FINEJ|PL
LOC|^^^^^M^^^^69&CPAGE&700004591&FINEJ||M|Etablissement juridique
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||ID_GLBL^Identifiant unique global^L|^69
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||CD^Code^L|^69
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||LBL^Libelle^L|^GRGAP
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||LBL_CRT^Libelle court^L|^Etab Hosp
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||FNS^Code FINESS^L|^700004591
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||ADRS_1^Adresse 1^L|^4 Avenue de la VBF
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||DT_OVRTR^Date d'ouverture^L|^20230101
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||DT_ACTVTN^Date d'activation^L|^20230115
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||DT_FRMTR^Date de fermeture^L|^20241231
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||DT_FN_ACTVTN^Date de fin d'activation^L|^20241215
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||ID_GLBL_RSPNSBL^ID responsable^L|^RESP001
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||NM_USL_RSPNSBL^Nom responsable^L|^DUPONT
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||PRNM_RSPNSBL^Prénom responsable^L|^Jean
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||RPPS_RSPNSBL^RPPS responsable^L|^10101010101
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||ADL_RSPNSBL^ADELI responsable^L|^691234567
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||CD_SPCLT_RSPNSBL^Spécialité responsable^L|^01
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||TPLG^Typologie^L|^MCO"""
    
    response = client.post("/structure/import/hl7", content=message, headers={"Content-Type": "text/plain"})
    assert response.status_code == 200
    
    # Vérification création EG
    eg = session.exec(select(EntiteGeographique).where(EntiteGeographique.finess == "700004591")).first()
    assert eg is not None
    assert eg.name == "GRGAP"
    assert eg.short_name == "Etab Hosp"
    assert eg.identifier == "69"
    
    # Vérification dates
    assert eg.opening_date == "20230101"
    assert eg.activation_date == "20230115" 
    assert eg.closing_date == "20241231"
    assert eg.deactivation_date == "20241215"
    
    # Vérification responsable
    assert eg.responsible_id == "RESP001"
    assert eg.responsible_name == "DUPONT"
    assert eg.responsible_firstname == "Jean"
    assert eg.responsible_rpps == "10101010101"
    assert eg.responsible_adeli == "691234567"
    assert eg.responsible_specialty == "01"
    
    # Vérification typologie
    assert eg.type == "MCO"

def test_export_structure_hl7(client: TestClient, session: Session):
    """Test export structure en HL7 MFN"""
    # Création structure de test
    eg = EntiteGeographique(
        identifier="69",
        name="GRGAP",
        short_name="Etab Hosp",
        finess="700004591",
        address_line1="4 Avenue de la VBF",
        physical_type="si"  # Site
    )
    session.add(eg)
    session.commit()
    
    # Export
    response = client.get("/structure/export/hl7")
    assert response.status_code == 200
    assert "MSH|^~\\&|STR|STR|RECEPTEUR|RECEPTEUR|" in response.text
    assert "FNS^Code FINESS^L|^700004591" in response.text

def test_structure_fhir_workflow(client: TestClient, session: Session):
    """Test workflow complet structure via FHIR"""
    # 1. Création EG via FHIR Location
    location_eg = {
        "resourceType": "Location",
        "status": "active",
        "mode": "instance",
        "name": "GRGAP",
        "type": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                "code": "HOSP"
            }]
        },
        "identifier": [{
            "system": "http://finess.sante.gouv.fr",
            "value": "700004591"
        }],
        "address": {
            "line": ["4 Avenue de la VBF"],
            "city": "VILLE",
            "postalCode": "70000",
            "country": "FRA"
        },
        "extension": [
            {
                "url": "https://medbridge.com/StructureFhir/location-dates",
                "extension": [
                    {
                        "url": "opening",
                        "valueDate": "2023-01-01"
                    },
                    {
                        "url": "activation", 
                        "valueDate": "2023-01-15"
                    },
                    {
                        "url": "closing",
                        "valueDate": "2024-12-31"
                    },
                    {
                        "url": "deactivation",
                        "valueDate": "2024-12-15" 
                    }
                ]
            },
            {
                "url": "https://medbridge.com/StructureFhir/location-manager",
                "extension": [
                    {
                        "url": "id",
                        "valueString": "RESP001"
                    },
                    {
                        "url": "name",
                        "valueString": "DUPONT"  
                    },
                    {
                        "url": "firstname",
                        "valueString": "Jean"
                    },
                    {
                        "url": "rpps",
                        "valueString": "10101010101"
                    },
                    {
                        "url": "adeli",
                        "valueString": "691234567"
                    },
                    {
                        "url": "specialty",
                        "valueString": "01"
                    }
                ]
            },
            {
                "url": "https://medbridge.com/StructureFhir/location-type",
                "valueString": "MCO"
            }
        ]
    }
    
    response = client.post("/fhir/Location", json=location_eg)
    assert response.status_code == 201
    location_id = response.json().get("id")
    
    # 2. Création service via FHIR Location
    location_service = {
        "resourceType": "Location",
        "status": "active",
        "mode": "instance",
        "name": "Cardiologie",
        "type": {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/service-type",
                "code": "mco"
            }]
        },
        "identifier": [{
            "value": "CARDIO_01"
        }],
        "partOf": {
            "reference": f"Location/{location_id}"
        }
    }
    
    response = client.post("/fhir/Location", json=location_service)
    assert response.status_code == 201
    service_id = response.json().get("id")
    
    # 3. Lecture service
    response = client.get(f"/fhir/Location/{service_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Cardiologie"
    
    # 4. Recherche des services de l'EG
    response = client.get("/fhir/Location", params={"partof": f"Location/{location_id}"})
    assert response.status_code == 200
    assert len(response.json()["entry"]) >= 1
    
    # 5. Mise à jour service
    location_service["name"] = "Cardiologie v2"
    response = client.put(f"/fhir/Location/{service_id}", json=location_service)
    assert response.status_code == 200
    assert response.json()["name"] == "Cardiologie v2"
    
    # 6. Suppression service
    response = client.delete(f"/fhir/Location/{service_id}")
    assert response.status_code == 204

def test_bidirectional_structure_conversion(client: TestClient, session: Session):
    """Test la conversion bidirectionnelle entre FHIR et HL7"""
    # 1. Import HL7
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    message = f"""MSH|^~\\&|STR|STR|RECEPTEUR|RECEPTEUR|{now}||MFN^M05^MFN_M05|{now}|P|2.5|||||FRA|8859/15
MFI|LOC|CPAGE_LOC_FRA|REP||{now}|AL
MFE|MAD|||^^^^^M^^^^69&CPAGE&700004591&FINEJ|PL
LOC|^^^^^M^^^^69&CPAGE&700004591&FINEJ||M|Etablissement juridique
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||ID_GLBL^Identifiant unique global^L|^69
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||LBL^Libelle^L|^GRGAP TEST
LCH|^^^^^M^^^^69&CPAGE&700004591&FINEJ|||FNS^Code FINESS^L|^700004591"""
    
    response = client.post("/structure/import/hl7", content=message, headers={"Content-Type": "text/plain"})
    assert response.status_code == 200
    
    # 2. Lecture via FHIR
    response = client.get("/fhir/Location", params={"identifier": "700004591"})
    assert response.status_code == 200
    assert len(response.json()["entry"]) == 1
    location = response.json()["entry"][0]["resource"]
    assert location["name"] == "GRGAP TEST"
    
    # 3. Mise à jour via FHIR
    location["name"] = "GRGAP TEST V2"
    response = client.put(f"/fhir/Location/{location['id']}", json=location)
    assert response.status_code == 200
    
    # 4. Export HL7 et vérification
    response = client.get("/structure/export/hl7")
    assert response.status_code == 200
    assert "LBL^Libelle^L|^GRGAP TEST V2" in response.text