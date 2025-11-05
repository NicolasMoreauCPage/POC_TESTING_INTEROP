# Standards d'Interopérabilité Supportés

## Table des matières
1. [Standards HL7v2](#standards-hl7v2)
   - [IHE PAM (Patient Administration Management)](#ihe-pam)
   - [IHE PIX (Patient Identifier Cross-referencing)](#ihe-pix)
   - [IHE PDQ (Patient Demographics Query)](#ihe-pdq)
2. [Standards FHIR](#standards-fhir)
   - [PIXm](#pixm)
   - [PDQm](#pdqm)
   - [Patient Administration](#patient-administration)
3. [Interface d'Injection de Messages](#interface-dinjection)

## Standards HL7v2

### IHE PAM
**Version supportée**: HL7v2.5 FR
**Profil IHE**: PAMv2.10

#### Messages supportés
- **ADT^A01**: Admission d'un patient
- **ADT^A02**: Transfert d'un patient
- **ADT^A03**: Sortie d'un patient
- **ADT^A04**: Inscription d'un patient
- **ADT^A05**: Pré-admission
- **ADT^A06**: Changement de lieu
- **ADT^A07**: Changement de lieu pendant l'absence
- **ADT^A08**: Mise à jour des informations patient
- **ADT^A11**: Annulation d'admission
- **ADT^A12**: Annulation de transfert
- **ADT^A13**: Annulation de sortie
- **ADT^A14**: Admission en attente
- **ADT^A16**: Admission en attente avec lit
- **ADT^A25**: Annulation d'admission en attente
- **ADT^A38**: Annulation de pré-admission
- **ADT^A44**: Passage en externe
- **ADT^A45**: Fusion de mouvements
- **ADT^Z99**: Mise à jour du mouvement

#### Format des messages
```
MSH|^~\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20251101000000||ADT^A01|MSG00001|P|2.5
EVN|A01|20251101000000|||APPLI^IHE
PID|||123456^^^HOPITAL||DUPONT^JEAN||19800101|M
PV1||I|CARDIO^101^1|||||||||||||||||1|||||||||||||||||||||||||20251101000000
```

#### Points d'injection
- POST `/transport/hl7`: Point d'entrée principal pour les messages HL7v2
- POST `/ihe/pam/event`: Point d'entrée spécifique PAM

### IHE PIX
**Version**: HL7v2.5
**Transaction**: ITI-9, ITI-10

#### Messages supportés
- **QBP^Q23**: Requête PIX (ITI-9)
- **ADT^***: Alimentation PIX (ITI-8)

#### Format requête PIX
```
MSH|^~\&|SENDING_APP|SENDING_FAC|PIX_MGR|PIX_FAC|20251101000000||QBP^Q23^QBP_Q21|MSG00001|P|2.5
QPD|IHE PIX Query|QRY123|123456^^^HOPITAL
RCP|I
```

#### Points d'injection
- POST `/ihe/pix/query`: Requête PIX
- POST `/ihe/pix/feed`: Alimentation PIX

### IHE PDQ
**Version**: HL7v2.5
**Transaction**: ITI-21

#### Messages supportés
- **QBP^Q22**: Requête PDQ
- **RSP^K22**: Réponse PDQ

#### Format requête PDQ
```
MSH|^~\&|SENDING_APP|SENDING_FAC|PDQ_MGR|PDQ_FAC|20251101000000||QBP^Q22^QBP_Q21|MSG00001|P|2.5
QPD|IHE PDQ Query|QRY123|@PID.5.1^DUPONT~@PID.5.2^JEAN~@PID.7^19800101
RCP|I
```

#### Points d'injection
- POST `/ihe/pdq/query`: Requête PDQ

## Standards FHIR

### PIXm
**Version FHIR**: R4
**Profil IHE**: PIXm

#### Opérations supportées
- `$ihe-pix`: Recherche d'identifiants croisés

#### Format requête PIXm
```http
POST /ihe/pixm/$ihe-pix
Accept: application/fhir+json
Content-Type: application/fhir+json

{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "sourceIdentifier",
      "valueIdentifier": {
        "system": "http://hopital-a.fr/id",
        "value": "123456"
      }
    }
  ]
}
```

### PDQm
**Version FHIR**: R4
**Profil IHE**: PDQm

#### Opérations supportées
- Recherche Patient (`GET /Patient`)
- Recherche Patient avec critères multiples

#### Critères de recherche supportés
- `family`: Nom de famille
- `given`: Prénom
- `birthdate`: Date de naissance (format YYYY-MM-DD)
- `gender`: Genre (male/female/other/unknown)
- `identifier`: Identifiant avec système
- `_lastUpdated`: Date de dernière mise à jour

#### Exemple de requête PDQm
```http
GET /ihe/pdqm/Patient?family=DUPONT&birthdate=1980-01-01
Accept: application/fhir+json
```

### Patient Administration
**Version FHIR**: R4

#### Resources supportées
- Patient
- Encounter
- EpisodeOfCare
- Location

#### Points d'accès FHIR
- `/fhir/Patient`: CRUD Patient
- `/fhir/Encounter`: CRUD Encounter
- `/fhir/Location`: CRUD Location

## Interface d'Injection de Messages

### Interface Web
L'interface web d'injection de messages est accessible à `/transport/injection` et propose :

1. **Injection HL7v2**
   - Sélection du type de message
   - Templates pré-remplis pour chaque type
   - Validation syntaxique en temps réel
   - Affichage de l'ACK reçu

2. **Injection FHIR**
   - Sélection du type de ressource
   - Templates JSON pour chaque resource
   - Validation des profils IHE
   - Affichage de la réponse

### Endpoints de Test
Pour faciliter les tests, plusieurs endpoints sont disponibles :

1. **HL7v2**
```bash
# Test PIX Query
curl -X POST http://localhost:8000/ihe/pix/query \
  -H "Content-Type: text/plain" \
  -d 'MSH|^~\&|...'

# Test PDQ Query
curl -X POST http://localhost:8000/ihe/pdq/query \
  -H "Content-Type: text/plain" \
  -d 'MSH|^~\&|...'
```

2. **FHIR**
```bash
# Test PIXm
curl -X POST http://localhost:8000/ihe/pixm/\$ihe-pix \
  -H "Accept: application/fhir+json" \
  -H "Content-Type: application/fhir+json" \
  -d '{"resourceType": "Parameters",...}'

# Test PDQm
curl -X GET "http://localhost:8000/ihe/pdqm/Patient?family=DUPONT" \
  -H "Accept: application/fhir+json"
```

### Variables d'Environnement
- `MLLP_TRACE=1`: Active les logs détaillés MLLP
- `LOG_LEVEL=DEBUG`: Active les logs détaillés pour tous les messages
- `VALIDATE_HL7=1`: Active la validation stricte des messages HL7

### Validation
1. **HL7v2**
   - Validation syntaxique (segments, champs)
   - Validation sémantique (contenu des champs)
   - Validation des triggers events
   - Validation des acquittements

2. **FHIR**
   - Validation JSON Schema
   - Validation des profils IHE
   - Validation des ValueSets
   - Validation des références

### Logs et Monitoring
Tous les messages sont journalisés dans :
1. Base de données (table `message_log`)
2. Fichiers logs avec rotation
3. Interface d'administration `/admin/messages`

### Tests Automatisés
Des scripts de test sont disponibles dans `tests/`:
- `test_ihe_integration.py`: Tests IHE PAM
- `test_ihe_pix_pdq.py`: Tests PIX/PDQ
- `test_transport_inbound.py`: Tests MLLP