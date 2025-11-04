from typing import Optional, List, TYPE_CHECKING, ForwardRef
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Session

from app.models_identifiers import Identifier, IdentifierType

class DossierType(str, Enum):
    """Type de dossier patient"""
    HOSPITALISE = "hospitalise"  # Hospitalisation complète
    EXTERNE = "externe"         # Consultation externe
    URGENCE = "urgence"        # Passage aux urgences
    
# --- Générateur de séquences générique ---
class Sequence(SQLModel, table=True):
    name: str = Field(primary_key=True)   # ex: "dossier", "venue", "mouvement"
    value: int = 0

# --- Patient ---
class Patient(SQLModel, table=True):
    """
    Modèle Patient conforme aux normes françaises et RGPD.
    
    IMPORTANT RGPD France :
    - race et religion : INTERDITS en France (Article 9 RGPD + loi Informatique et Libertés)
    - Ces champs sont conservés en DB pour compatibilité legacy mais NE DOIVENT PAS être collectés
    - gender : sexe administratif unique (pas de duplication avec administrative_gender)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_seq: Optional[int] = Field(default=None, index=True, unique=True)  # Identifiant métier séquentiel (unique)
    external_id: Optional[str] = None  # Identifiant du système source externe
    identifier: Optional[str] = Field(default=None, index=True)  # Identifiant principal (peut être NIR ou autre)
    
    # Identité
    family: str = Field(alias="nom")  # Nom de famille (obligatoire)
    given: Optional[str] = None  # Prénom
    middle: Optional[str] = None  # Deuxième prénom
    prefix: Optional[str] = None  # Civilité (M./Mme/Mlle)
    suffix: Optional[str] = None  # Suffixe (Jr., III, etc.)
    birth_family: Optional[str] = None  # Nom de naissance (nom de jeune fille) - PID-5 type L
    birth_date: Optional[str] = None  # Date de naissance (AAAA-MM-JJ)
    gender: Optional[str] = None  # Sexe administratif (male/female/other/unknown)
    
    # Adresse d'habitation (PID-11)
    address: Optional[str] = None  # PID-11.1 - Adresse (numéro et rue)
    city: Optional[str] = None  # PID-11.3 - Ville
    state: Optional[str] = None  # PID-11.4 - Département/Région
    postal_code: Optional[str] = None  # PID-11.5 - Code postal
    country: Optional[str] = None  # PID-11.6 - Pays (code ISO: FR, BE, CH, etc.)
    
    # Téléphones (PID-13) - Multi-valué
    phone: Optional[str] = None  # PID-13.1 - Téléphone principal/fixe
    mobile: Optional[str] = None  # PID-13.2 - Téléphone mobile/cellulaire
    work_phone: Optional[str] = None  # PID-13.3 - Téléphone professionnel
    email: Optional[str] = None  # Email
    
    # Lieu de naissance (adresse complète) - Complément PID-23
    birth_address: Optional[str] = None  # Rue de naissance (optionnel)
    birth_city: Optional[str] = None  # Ville de naissance (PID-23 dans HL7 v2.5 - texte libre)
    birth_state: Optional[str] = None  # Département/Région de naissance
    birth_postal_code: Optional[str] = None  # Code postal de naissance
    birth_country: Optional[str] = None  # Pays de naissance (code ISO: FR, etc.)
    
    # Statut de l'identité (PID-32) - OBLIGATOIRE IHE PAM France pour INS
    identity_reliability_code: Optional[str] = None  # HL7 Table 0445: VIDE/PROV/VALI/DOUTE/FICTI
    identity_reliability_date: Optional[str] = None  # Date de validation de l'identité (AAAA-MM-JJ)
    identity_reliability_source: Optional[str] = None  # Source de validation (CNI, Passeport, Acte naissance, etc.)
    
    # Informations administratives
    nir: Optional[str] = None  # Numéro d'Inscription au Répertoire (NIR) - Numéro de sécurité sociale français (PID-3 NH)
    ssn: Optional[str] = None  # DEPRECATED: Utiliser 'nir' pour la France
    marital_status: Optional[str] = None  # Statut marital (codes HL7: S/M/D/W/P/A/U)
    mothers_maiden_name: Optional[str] = None  # Nom de jeune fille de la mère (vérification identité)
    nationality: Optional[str] = None  # Nationalité (code pays ISO, ex: FR)
    place_of_birth: Optional[str] = None  # Lieu de naissance
    primary_care_provider: Optional[str] = None  # Médecin traitant déclaré
    
    # DEPRECATED - RGPD France (conservés pour compatibilité legacy uniquement)
    race: Optional[str] = None  # ⚠️ INTERDIT EN FRANCE - Ne pas collecter (Article 9 RGPD)
    religion: Optional[str] = None  # ⚠️ INTERDIT EN FRANCE - Ne pas collecter (Article 9 RGPD)
    administrative_gender: Optional[str] = None  # ⚠️ DOUBLON - Utiliser 'gender' uniquement

    dossiers: List["Dossier"] = Relationship(back_populates="patient")
    identifiers: List["Identifier"] = Relationship(back_populates="patient")

    # Backwards-compat properties used by tests/templates expecting French names
    @property
    def nom(self) -> str:
        return self.family

    @nom.setter
    def nom(self, value: str) -> None:
        self.family = value

    @property
    def prenom(self) -> Optional[str]:
        return self.given

    @prenom.setter
    def prenom(self, value: str) -> None:
        self.given = value


# --- Dossier ---
class Dossier(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dossier_seq: int = Field(index=True, unique=True)       # identifiant métier unique
    patient_id: int = Field(foreign_key="patient.id")
    uf_responsabilite: str
    admit_time: datetime
    discharge_time: Optional[datetime] = None
    dossier_type: DossierType = Field(default=DossierType.HOSPITALISE, description="Type de dossier (hospitalisé, externe, urgence)")

    def update_type(self, new_type: DossierType, session: Session | None = None) -> None:
        """
        Met à jour le type de dossier avec validation et synchronisation de la classe.
        Lève une ValueError si le changement est invalide.
        """
        if new_type == self.dossier_type:
            return
            
        if session is None:
            from app.db import session_factory
            with session_factory() as new_session:
                new_session.add(self)
                self._validate_and_update_type(new_type, new_session)
        else:
            self._validate_and_update_type(new_type, session)
    
    def _validate_and_update_type(self, new_type: DossierType, session: Session) -> None:
        from app.utils.dossier_validators import validate_dossier_type_change
        from app.utils.dossier_helpers import sync_dossier_class
        
        can_change, warnings = validate_dossier_type_change(session, self, new_type)
        if not can_change:
            raise ValueError("\n".join(warnings))
            
        self.dossier_type = new_type
        sync_dossier_class(self)
    # Extensions / IHE PAM additions (optional)
    admission_type: Optional[str] = None
    admission_source: Optional[str] = None  # Source d'admission
    attending_provider: Optional[str] = None
    primary_diagnosis: Optional[str] = None
    discharge_disposition: Optional[str] = None
    encounter_class: Optional[str] = None
    encounter_type: Optional[str] = None  # Type de rencontre
    priority: Optional[str] = None  # Priorité de la rencontre
    reason: Optional[str] = None  # Raison de la rencontre
    current_state: Optional[str] = None  # État actuel du dossier
    patient: Patient = Relationship(back_populates="dossiers")
    venues: List["Venue"] = Relationship(back_populates="dossier")
    identifiers: List["Identifier"] = Relationship(back_populates="dossier")

# --- Venue (appartient à un Dossier) ---
class Venue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    venue_seq: int = Field(index=True, unique=True)         # identifiant métier unique
    dossier_id: int = Field(foreign_key="dossier.id")
    uf_responsabilite: str
    start_time: datetime
    code: Optional[str] = None
    label: Optional[str] = None
    # Extensions
    assigned_location: Optional[str] = None
    attending_provider: Optional[str] = None
    hospital_service: Optional[str] = None
    bed: Optional[str] = None
    room: Optional[str] = None
    discharge_disposition: Optional[str] = None
    managing_department: Optional[str] = None  # Département gestionnaire
    physical_type: Optional[str] = None  # Type physique de l'emplacement
    operational_status: Optional[str] = None  # Statut opérationnel
    dossier: Dossier = Relationship(back_populates="venues")
    mouvements: List["Mouvement"] = Relationship(back_populates="venue")
    identifiers: List["Identifier"] = Relationship(back_populates="venue")

    # Backwards-compat property expected by tests/templates
    @property
    def status(self) -> Optional[str]:
        return self.operational_status

    @status.setter
    def status(self, value: str) -> None:
        self.operational_status = value

# --- Mouvement (appartient à une Venue) ---
class Mouvement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mouvement_seq: int = Field(index=True, unique=True)     # identifiant métier unique
    venue_id: int = Field(foreign_key="venue.id")
    # Type de message HL7 (ex: "ADT^A01"). Conservé pour compat UI/ancienne donnée.
    # La logique métier doit utiliser trigger_event (A01, A03, A21, ...).
    type: Optional[str] = None
    when: datetime
    location: Optional[str] = None
    # Extensions
    from_location: Optional[str] = None
    to_location: Optional[str] = None
    reason: Optional[str] = None
    performer: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    movement_type: Optional[str] = None  # Type de mouvement (français)
    movement_reason: Optional[str] = None  # Raison du mouvement
    performer_role: Optional[str] = None  # Rôle de l'intervenant
    trigger_event: Optional[str] = None  # Code IHE PAM de l'événement (A01, A03, A21, etc.) pour validation des transitions
    # Référence au mouvement annulé (pour A12/A13) via numéro de séquence, si connu
    cancelled_movement_seq: Optional[int] = None
    venue: Venue = Relationship(back_populates="mouvements")
    identifiers: List["Identifier"] = Relationship(back_populates="mouvement")
