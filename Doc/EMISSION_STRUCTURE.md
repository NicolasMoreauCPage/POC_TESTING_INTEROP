# Émission Automatique des Messages Structure (MFN/FHIR)

## État Actuel

### ✅ Fonctionnel

#### Entités de Structure (Location FHIR)
Les émissions automatiques **fonctionnent** pour :
- **EntiteGeographique** → FHIR Location + MFN M05
- **Pole** → FHIR Location + MFN M05
- **Service** → FHIR Location + MFN M05
- **UniteFonctionnelle** → FHIR Location + MFN M05
- **UniteHebergement** → FHIR Location + MFN M05
- **Chambre** → FHIR Location + MFN M05
- **Lit** → FHIR Location + MFN M05

**Déclenchement** : Automatique via événements SQLAlchemy (`after_insert`, `after_update`, `after_delete`)

**Fichiers impliqués** :
- `app/services/entity_events_structure.py` : Enregistrement des listeners
- `app/services/structure_emit.py` : Émission FHIR (Bundle PUT/DELETE) + MFN (snapshot complet)
- `app/services/fhir_structure.py` : Conversion entités → FHIR Location
- `app/services/mfn_structure.py` : Génération messages MFN M05

### ⚠️ Non Fonctionnel

#### EntiteJuridique (Organization FHIR)

**Problème** : L'EntiteJuridique doit être émise comme **FHIR Organization**, pas Location.

**État actuel** :
- ✅ Événements SQLAlchemy enregistrés (ajouté dans ce commit)
- ❌ Génération FHIR Organization pas implémentée
- ❌ Génération MFN pour Organization pas implémentée
- ✅ Log informatif généré lors de création/modification

**Message actuel** :
```
[structure_emit] EntiteJuridique créée/modifiée (id=X, name=Y) - 
Émission automatique Organization FHIR/MFN pas encore supportée
```

## Modifications Apportées

### 1. Ajout EntiteJuridique aux événements automatiques

**Fichier** : `app/services/entity_events_structure.py`

```python
# Ajout de l'import
from app.models_structure_fhir import EntiteJuridique

# Ajout à la liste des modèles surveillés
for model in (EntiteJuridique, EntiteGeographique, Pole, Service, ...):
    event.listen(model, "after_insert", _after_insert)
    event.listen(model, "after_update", _after_update)
    event.listen(model, "after_delete", _after_delete)
```

### 2. Gestion spéciale pour EntiteJuridique

**Fichier** : `app/services/structure_emit.py`

```python
async def emit_structure_change(entity, session: Session, operation: str = "update") -> None:
    """Émet FHIR (PUT) + HL7 MFN snapshot après création/mise à jour.
    
    Note: EntiteJuridique est traitée comme Organization (pas Location) 
    et n'est pas encore supportée pour l'émission automatique FHIR/MFN.
    """
    from app.models_structure_fhir import EntiteJuridique
    
    # EntiteJuridique doit être émise comme Organization, pas Location
    if isinstance(entity, EntiteJuridique):
        logger.info(
            "[structure_emit] EntiteJuridique créée/modifiée (id=%s, name=%s) - "
            "Émission automatique Organization FHIR/MFN pas encore supportée",
            entity.id,
            entity.name
        )
        session.commit()
        return
    
    # Traitement normal pour les autres entités
    await _emit_fhir_upsert(entity, session)
    await _emit_mfn_snapshot(session)
    session.commit()
```

## Configuration Requise

### Endpoints "Sender"

Pour que les émissions fonctionnent, il faut configurer des **endpoints "sender"** dans la base de données :

```sql
-- Exemple : Endpoint FHIR sender
INSERT INTO systemendpoint (name, kind, role, is_enabled, host, port) 
VALUES ('FHIR Server External', 'FHIR', 'sender', 1, 'http://external-fhir.hospital.fr', 8080);

-- Exemple : Endpoint MLLP sender
INSERT INTO systemendpoint (name, kind, role, is_enabled, host, port) 
VALUES ('HL7 MLLP External', 'MLLP', 'sender', 1, 'external-hl7.hospital.fr', 2575);
```

**Vérification** :
```python
from app.db import Session, engine
from app.models_endpoints import SystemEndpoint
from sqlmodel import select

session = Session(engine)
senders = session.exec(
    select(SystemEndpoint).where(SystemEndpoint.role == "sender")
).all()

for s in senders:
    print(f"- {s.name} ({s.kind}): {s.host}:{s.port} - {'✓' if s.is_enabled else '✗'}")
```

## Roadmap : Support EntiteJuridique

### Étape 1 : FHIR Organization

**Créer** : `app/services/fhir_organization.py`

```python
def entity_to_fhir_organization(ej: EntiteJuridique, session: Session) -> Dict[str, Any]:
    """Convertit une EntiteJuridique en FHIR Organization.
    
    Profil : http://interop-sante.fr/fhir/StructureDefinition/fr-organization
    """
    return {
        "resourceType": "Organization",
        "id": str(ej.id),
        "meta": {
            "profile": ["http://interop-sante.fr/fhir/StructureDefinition/fr-organization"]
        },
        "identifier": [
            {
                "system": "http://finess.sante.gouv.fr",
                "value": ej.finess_ej
            }
        ],
        "name": ej.name,
        "alias": [ej.short_name] if ej.short_name else [],
        "type": [
            {
                "coding": [
                    {
                        "system": "https://mos.esante.gouv.fr/NOS/TRE_R66-CategorieEtablissement/FHIR/TRE-R66-CategorieEtablissement",
                        "code": "EJ"
                    }
                ]
            }
        ],
        # Ajouter adresse, télécom, etc.
    }
```

### Étape 2 : MFN Organization

**Modifier** : `app/services/mfn_structure.py`

Ajouter support pour messages MFN M02 (Master File - Staff Practitioner) ou créer un nouveau type de message pour Organizations.

**Alternative** : Utiliser MFN M05 avec un type différent (org au lieu de loc).

### Étape 3 : Émission Organization

**Modifier** : `app/services/structure_emit.py`

```python
async def emit_structure_change(entity, session: Session, operation: str = "update") -> None:
    from app.models_structure_fhir import EntiteJuridique
    
    if isinstance(entity, EntiteJuridique):
        await _emit_organization_upsert(entity, session)
        await _emit_organization_mfn(session)
        session.commit()
        return
    
    # Traitement normal pour Location
    await _emit_fhir_upsert(entity, session)
    await _emit_mfn_snapshot(session)
    session.commit()

async def _emit_organization_upsert(ej: EntiteJuridique, session: Session) -> None:
    """Émet FHIR Organization vers les endpoints sender."""
    from app.services.fhir_organization import entity_to_fhir_organization
    
    resource = entity_to_fhir_organization(ej, session)
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "resource": resource,
                "request": {"method": "PUT", "url": f"Organization/{ej.id}"}
            }
        ]
    }
    # Envoi vers endpoints FHIR...
```

## Tests

### Test Manuel via UI

1. Configurer un endpoint "sender" (FHIR ou MLLP)
2. Créer une nouvelle EJ via l'interface admin
3. Vérifier les logs : `[structure_emit] EntiteJuridique créée/modifiée`
4. Vérifier la table `messagelog` pour les émissions

### Test Automatique

Créer `test_ej_organization_emit.py` une fois l'implémentation terminée.

## Notes Techniques

### Pourquoi Organization et pas Location ?

**FHIR Specification** :
- **Location** : Emplacement physique (bâtiment, service, chambre, lit)
- **Organization** : Entité légale/administrative (hôpital, clinique, groupe hospitalier)

**Hiérarchie** :
```
Organization (EntiteJuridique)
  └─ Location (EntiteGeographique)
      └─ Location (Pole)
          └─ Location (Service)
              └─ Location (UniteFonctionnelle)
```

### MFN Messages

**MFN M05** : Master File Notification - Location  
→ Utilisé pour EG, Pole, Service, UF, etc.

**MFN M02** : Master File - Staff Practitioner  
→ Pourrait être adapté pour Organizations ?

**Alternative** : Utiliser MFN M05 avec discriminant `type=org`

## Conclusion

L'infrastructure d'émission automatique est en place et **fonctionne pour toutes les entités de type Location** (EG, Pole, Service, UF, UH, Chambre, Lit).

Pour **EntiteJuridique**, l'événement est maintenant **détecté et loggé**, mais l'émission n'est **pas encore implémentée** car elle nécessite :
1. Génération FHIR Organization (profil fr-organization)
2. Génération MFN appropriée pour Organization
3. Intégration dans le pipeline d'émission

**Prochaine étape** : Implémenter les 3 points ci-dessus pour activer l'émission automatique des EntiteJuridique.
