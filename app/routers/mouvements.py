from fastapi import APIRouter, Depends, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select
from datetime import datetime
from typing import Optional
from app.db import get_session, get_next_sequence, peek_next_sequence
from app.models import Mouvement, Venue, Dossier
from app.services.emit_on_create import emit_to_senders
from app.dependencies.ght import require_ght_context
from app.state_transitions import ALLOWED_TRANSITIONS, INITIAL_EVENTS, SUPPORTED_WORKFLOW_EVENTS

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(
    prefix="/mouvements", 
    tags=["mouvements"],
    dependencies=[Depends(require_ght_context)]
)

def get_status_badge(status):
    colors = {
        'active': 'bg-green-100 text-green-800',
        'completed': 'bg-blue-100 text-blue-800',
        'cancelled': 'bg-red-100 text-red-800',
        'pending': 'bg-yellow-100 text-yellow-800'
    }
    # Guard against None status
    if status is None:
        status = 'inconnu'
    class_name = colors.get(status, 'bg-slate-100 text-slate-800')
    return f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {class_name}">{status.title()}</span>'

def get_type_badge(movement_type: str | None) -> str:
    if not movement_type:
        return '—'
    colors = {
        'admission': 'bg-blue-100 text-blue-800',
        'registration': 'bg-indigo-100 text-indigo-800',
        'preadmission': 'bg-sky-100 text-sky-800',
        'class-change': 'bg-violet-100 text-violet-800',
        'transfer': 'bg-amber-100 text-amber-800',
        'transfer-cancel': 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
        'discharge': 'bg-red-100 text-red-800',
        'discharge-cancel': 'bg-orange-100 text-orange-800',
        'leave-out': 'bg-yellow-100 text-yellow-800',
        'leave-return': 'bg-green-100 text-green-800',
        'doctor-change': 'bg-teal-100 text-teal-800',
        'doctor-change-cancel': 'bg-teal-50 text-teal-700 ring-1 ring-teal-200',
        'update': 'bg-slate-100 text-slate-800',
    }
    label_map = {
        'admission': 'Admission',
        'registration': 'Consultation',
        'preadmission': 'Pré-admission',
        'class-change': 'Mutation',
        'transfer': 'Transfert',
        'transfer-cancel': 'Annul. transfert',
        'discharge': 'Sortie',
        'discharge-cancel': 'Annul. sortie',
        'leave-out': 'Permission',
        'leave-return': 'Retour perm.',
        'doctor-change': 'Change. médecin',
        'doctor-change-cancel': 'Annul. médecin',
        'update': 'MàJ identité',
    }
    class_name = colors.get(movement_type, 'bg-slate-100 text-slate-800')
    label = label_map.get(movement_type, movement_type.title())
    return f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {class_name}">{label}</span>'

@router.get("", response_class=HTMLResponse)
def list_mouvements(
    request: Request,
    venue_id: Optional[int] = Query(None, description="ID de la venue dont on veut voir les mouvements"),
    dossier_id: Optional[int] = Query(None, description="ID du dossier dont on veut voir les mouvements"),
    include_cancelled: bool = Query(False, description="Inclure les mouvements annulés dans la liste"),
    order: str = Query("asc", pattern="^(asc|desc)$", description="Ordre de tri par date"),
    session=Depends(get_session)
):
    venue = None
    dossier = None
    
    # Si venue_id est fourni, on filtre par venue
    if venue_id:
        venue = session.get(Venue, venue_id)
        if not venue:
            return templates.TemplateResponse(
                request,
                "error.html",
                {
                    "request": request,
                    "title": "Venue introuvable",
                    "message": "La venue spécifiée n'existe pas. Veuillez sélectionner une venue valide.",
                    "back_url": "/dossiers"
                },
                status_code=404
            )
        
        # Charger le contexte complet pour le fil d'Ariane
        session.refresh(venue, ['dossier'])
        if venue.dossier:
            session.refresh(venue.dossier, ['patient'])
            dossier = venue.dossier
        
        # Construction de la requête filtrée par venue
        stmt = select(Mouvement).where(Mouvement.venue_id == venue_id)
        if not include_cancelled:
            stmt = stmt.where((Mouvement.status.is_(None)) | (Mouvement.status != "cancelled"))
        # Tri
        if order == "asc":
            stmt = stmt.order_by(Mouvement.when.asc(), Mouvement.id.asc())
        else:
            stmt = stmt.order_by(Mouvement.when.desc(), Mouvement.id.desc())
    
    # Si dossier_id est fourni (et pas de venue_id), on filtre par dossier
    elif dossier_id:
        dossier = session.get(Dossier, dossier_id)
        if not dossier:
            return templates.TemplateResponse(
                request,
                "error.html",
                {
                    "request": request,
                    "title": "Dossier introuvable",
                    "message": "Le dossier spécifié n'existe pas. Veuillez sélectionner un dossier valide.",
                    "back_url": "/dossiers"
                },
                status_code=404
            )
        
        # Charger le patient pour le fil d'Ariane
        session.refresh(dossier, ['patient'])
        
        # Construction de la requête filtrée par dossier (via les venues)
        stmt = select(Mouvement).join(Venue).where(Venue.dossier_id == dossier_id)
        if not include_cancelled:
            stmt = stmt.where((Mouvement.status.is_(None)) | (Mouvement.status != "cancelled"))
        # Tri
        if order == "asc":
            stmt = stmt.order_by(Mouvement.when.asc(), Mouvement.id.asc())
        else:
            stmt = stmt.order_by(Mouvement.when.desc(), Mouvement.id.desc())
    
    # Sinon, erreur : au moins un paramètre requis
    else:
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "request": request,
                "title": "Paramètre manquant",
                "message": "Vous devez spécifier soit un dossier_id soit un venue_id pour voir les mouvements.",
                "back_url": "/dossiers"
            },
            status_code=400
        )

    # Exécuter la requête
    mouvements = session.exec(stmt).all()

    # Préparer les lignes avec les actions détaillées
    def _type_cell(m: Mouvement) -> str:
        badge = get_type_badge(getattr(m, 'movement_type', None))
        seq_note = ""
        if getattr(m, 'cancelled_movement_seq', None):
            seq_note = f"<span class='ml-2 text-xs text-slate-500'>(annule #{m.cancelled_movement_seq})</span>"
        return badge + seq_note
    
    def _uf_cell(uf: str | None, color: str = "emerald") -> str:
        if not uf:
            return "<span class='text-slate-400 text-xs'>—</span>"
        return f"<span class='inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-{color}-50 text-{color}-700 border border-{color}-200'>{uf}</span>"
    
    def _uf_medicale_cell(m: Mouvement) -> str:
        return _uf_cell(getattr(m, 'uf_medicale', None), "blue")
    
    def _uf_hebergement_cell(m: Mouvement) -> str:
        return _uf_cell(getattr(m, 'uf_hebergement', None), "emerald")
    
    def _uf_soins_cell(m: Mouvement) -> str:
        return _uf_cell(getattr(m, 'uf_soins', None), "purple")
    
    def _nature_cell(m: Mouvement) -> str:
        nature = getattr(m, 'movement_nature', None)
        if not nature:
            return "<span class='text-slate-400 text-xs'>—</span>"
        return f"<span class='inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200'>{nature}</span>"

    rows = [
        {
            "cells": [
                m.mouvement_seq,
                m.id,
                m.venue_id,
                _type_cell(m),
                get_status_badge(getattr(m, 'status', 'pending')),
                m.when.strftime("%d/%m/%Y %H:%M") if m.when else None,
                _uf_medicale_cell(m),
                _uf_hebergement_cell(m),
                _uf_soins_cell(m),
                _nature_cell(m),
                m.location,
                m.performer,
            ],
            "detail_url": f"/mouvements/{m.id}",
            "edit_url": f"/mouvements/{m.id}/edit",
            "delete_url": f"/mouvements/{m.id}/delete",
        }
        for m in mouvements
    ]

    # Construire le fil d'Ariane
    breadcrumbs = [{"label": "Mouvements", "url": "#"}]
    
    if venue_id and venue:
        # Cas 1 : Filtrage par venue spécifique
        breadcrumbs.insert(0, {"label": f"Venue #{venue.venue_seq}", "url": f"/venues/{venue_id}"})
        if venue.dossier:
            breadcrumbs.insert(0, {"label": f"Dossier #{venue.dossier.dossier_seq}", "url": f"/dossiers/{venue.dossier.id}"})
            if venue.dossier.patient:
                breadcrumbs.insert(0, {
                    "label": f"Patient: {venue.dossier.patient.family} {venue.dossier.patient.given}",
                    "url": f"/patients/{venue.dossier.patient.id}"
                })
    elif dossier_id and dossier:
        # Cas 2 : Filtrage par dossier (tous les mouvements du dossier)
        breadcrumbs.insert(0, {"label": f"Dossier #{dossier.dossier_seq}", "url": f"/dossiers/{dossier.id}"})
        if dossier.patient:
            breadcrumbs.insert(0, {
                "label": f"Patient: {dossier.patient.family} {dossier.patient.given}",
                "url": f"/patients/{dossier.patient.id}"
            })

    # Définir les filtres de recherche
    filters = [
        {
            "label": "Type",
            "name": "type",
            "type": "select",
            "placeholder": "Tous les types",
            "options": [
                {"value": "ADT^A01", "label": "Admission"},
                {"value": "ADT^A02", "label": "Transfert"},
                {"value": "ADT^A03", "label": "Sortie"},
                {"value": "ADT^A04", "label": "Urgences / consultation externe"}
            ]
        },
        {
            "label": "Statut",
            "name": "status",
            "type": "select",
            "placeholder": "Tous les statuts",
            "options": [
                {"value": "pending", "label": "En attente"},
                {"value": "active", "label": "En cours"},
                {"value": "completed", "label": "Terminé"},
                {"value": "cancelled", "label": "Annulé"}
            ]
        },
        {
            "label": "Localisation",
            "name": "location",
            "type": "text",
            "placeholder": "Filtrer par localisation"
        }
    ]

    # Définir les actions disponibles
    # Ajouter une action pour inclure/masquer les annulés
    toggle_cancel_url = None
    context_query = f"venue_id={venue_id}" if venue_id else (f"dossier_id={dossier_id}" if dossier_id else "")
    if context_query:
        if include_cancelled:
            toggle_cancel_url = f"/mouvements?{context_query}&include_cancelled=0&order={order}"
        else:
            toggle_cancel_url = f"/mouvements?{context_query}&include_cancelled=1&order={order}"

    actions = [
        # Vues explicites
        ({
            "type": "link",
            "label": "Vue état actuel",
            "url": f"/mouvements/etat?{context_query}" if context_query else "/mouvements/etat"
        } if context_query else None),
        ({
            "type": "link",
            "label": "Vue historique",
            "url": f"/mouvements/historique?{context_query}" if context_query else "/mouvements/historique"
        } if context_query else None),
        {
            "type": "link",
            "label": "Export FHIR",
            "url": "/mouvements/export/fhir"
        },
        {
            "type": "link",
            "label": "Export HL7",
            "url": "/mouvements/export/hl7"
        }
    ]

    # Nettoyer actions None
    actions = [a for a in actions if a]

    if toggle_cancel_url:
        actions.insert(0, {
            "type": "link",
            "label": ("Masquer les annulés" if include_cancelled else "Afficher les annulés"),
            "url": toggle_cancel_url
        })

    # Toggle tri
    if context_query:
        if order == "asc":
            toggle_order_url = f"/mouvements?{context_query}&include_cancelled={'1' if include_cancelled else '0'}&order=desc"
            actions.insert(0, {"type": "link", "label": "Trier: plus récent → plus ancien", "url": toggle_order_url})
        else:
            toggle_order_url = f"/mouvements?{context_query}&include_cancelled={'1' if include_cancelled else '0'}&order=asc"
            actions.insert(0, {"type": "link", "label": "Trier: plus ancien → plus récent", "url": toggle_order_url})

    # Construire le contexte complet
    if venue_id and venue:
        base = f"de la venue #{venue.venue_seq}"
    elif dossier_id and dossier:
        base = f"du dossier #{dossier.dossier_seq}"
    else:
        base = ""

    if include_cancelled:
        title = f"Historique des mouvements {base}".strip()
    else:
        title = f"Mouvements (état actuel) {base}".strip()
    
    # Tabs ergonomiques pour basculer entre vues
    tabs = None
    if context_query:
        tabs = [
            {
                "label": "État actuel",
                "url": f"/mouvements/etat?{context_query}",
                "active": not include_cancelled,
            },
            {
                "label": "Historique",
                "url": f"/mouvements/historique?{context_query}",
                "active": include_cancelled,
            },
        ]

    ctx = {
        "request": request,
        "title": title,
        "breadcrumbs": breadcrumbs,
        "tabs": tabs,
    "headers": ["Seq", "ID", "Venue", "Type", "Status", "Date/Heure", "UF Méd.", "UF Héb.", "UF Soins", "Nature", "Localisation", "Intervenant"],
        "rows": rows,
    "context": {"venue_id": venue_id, "include_cancelled": include_cancelled, "order": order},
    "new_url": f"/mouvements/new?venue_id={venue_id}" if venue_id else (f"/mouvements/new?dossier_id={dossier_id}" if dossier_id else "/mouvements/new"),
        "filters": filters,
        "actions": actions,
        "show_actions": True
    }

    return templates.TemplateResponse(request, "list.html", ctx)


@router.get("/historique")
def mouvements_historique(
    request: Request,
    venue_id: Optional[int] = Query(None),
    dossier_id: Optional[int] = Query(None),
):
    """Redirige vers la liste en mode historique (inclut les annulés)."""
    if venue_id:
        return RedirectResponse(f"/mouvements?venue_id={venue_id}&include_cancelled=1", status_code=303)
    if dossier_id:
        return RedirectResponse(f"/mouvements?dossier_id={dossier_id}&include_cancelled=1", status_code=303)
    return RedirectResponse("/mouvements?include_cancelled=1", status_code=303)


@router.get("/etat")
def mouvements_etat(
    request: Request,
    dossier_id: Optional[int] = Query(None, description="ID du dossier concerné"),
    venue_id: Optional[int] = Query(None, description="ID de la venue concernée"),
):
    """Redirige vers la liste 'état actuel' (sans annulés)."""
    if dossier_id:
        return RedirectResponse(f"/mouvements?dossier_id={dossier_id}&include_cancelled=0", status_code=303)
    if venue_id:
        return RedirectResponse(f"/mouvements?venue_id={venue_id}&include_cancelled=0", status_code=303)
    return RedirectResponse("/mouvements", status_code=303)

@router.get("/new", response_class=HTMLResponse)
def new_mouvement(
    request: Request,
    venue_id: int | None = Query(None, description="ID de la venue pour laquelle créer un mouvement (pré-rempli si fourni)"),
    dossier_id: int | None = Query(None, description="ID du dossier pour filtrer les venues disponibles"),
    session=Depends(get_session)
):
    from app.form_config import MovementType, MouvementStatus
    from app.models_structure import UniteHebergement, Chambre, Lit, UniteFonctionnelle
    
    # Déterminer le dossier de filtrage
    filter_dossier_id = dossier_id
    if filter_dossier_id is None and hasattr(request.state, 'dossier_context') and request.state.dossier_context:
        filter_dossier_id = request.state.dossier_context.id
    
    # Récupérer les venues disponibles (filtrées par dossier si fourni)
    if filter_dossier_id:
        stmt = select(Venue).where(Venue.dossier_id == filter_dossier_id).order_by(Venue.venue_seq.desc())
    else:
        stmt = select(Venue).order_by(Venue.venue_seq.desc()).limit(100)
    
    venues = session.exec(stmt).all()
    
    if not venues:
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "request": request,
                "title": "Aucune venue disponible",
                "message": "Impossible de créer un mouvement : aucune venue n'est disponible. Créez d'abord une venue.",
                "back_url": "/venues/new" if filter_dossier_id else "/dossiers"
            },
            status_code=404
        )
    
    # Déterminer la venue présélectionnée
    prefill_venue_id = venue_id
    if prefill_venue_id is None and hasattr(request.state, 'venue_context') and request.state.venue_context:
        prefill_venue_id = request.state.venue_context.id
    if prefill_venue_id is None:
        prefill_venue_id = venues[0].id  # Première venue par défaut
    
    next_seq = peek_next_sequence(session, "mouvement")

    # Déterminer le dernier événement et la date par défaut en fonction de la venue présélectionnée
    # ainsi que la liste des événements autorisés à proposer dans le sélecteur
    allowed_events_codes = None
    default_when_str = None
    try:
        if prefill_venue_id:
            last = session.exec(
                select(Mouvement)
                .where(Mouvement.venue_id == prefill_venue_id)
                .order_by(Mouvement.when)
            ).all()
            if last:
                last_event = last[-1].type.split('^')[-1] if last[-1].type else None
                allowed_events_codes = ALLOWED_TRANSITIONS.get(last_event, set())
                # Appliquer les contraintes métier UI:
                # - A01/A04 uniquement si None, A05, A03 (ici: pas None, donc A01/A04 autorisés uniquement si last_event ∈ {A05, A03})
                if last_event not in {None, "A05", "A03"}:
                    allowed_events_codes = {e for e in allowed_events_codes if e not in {"A01", "A04"}}
                # - A06/A07 en contexte INSERT: nécessitent une admission active
                admitted_context = {"A01", "A02", "A21", "A22", "A44", "A54", "A55", "A06", "A07"}
                if last_event not in admitted_context:
                    allowed_events_codes = {e for e in allowed_events_codes if e not in {"A06", "A07"}}
                # 1 minute après le dernier mouvement
                from datetime import timedelta
                default_when_str = (last[-1].when + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M")
            else:
                # État initial
                allowed_events_codes = {e for e in INITIAL_EVENTS if e != "A38"}
                default_when_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
        else:
            # Si pas de venue présélectionnée, ne filtre pas (l'utilisateur choisira une venue)
            default_when_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    except Exception:
        # En cas de problème, fallback raisonnable
        allowed_events_codes = None
        default_when_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    
    # Préparer la liste déroulante des venues
    venue_options = []
    for v in venues:
        session.refresh(v, ['dossier'])
        label = f"Venue #{v.venue_seq}"
        if v.dossier:
            session.refresh(v.dossier, ['patient'])
            if v.dossier.patient:
                label += f" - {v.dossier.patient.family} {v.dossier.patient.given}"
            label += f" (Dossier #{v.dossier.dossier_seq})"
        venue_options.append({"value": str(v.id), "label": label})
    
    # Récupérer les Unités Fonctionnelles disponibles
    uf_options = []
    try:
        ufs = session.exec(select(UniteFonctionnelle).order_by(UniteFonctionnelle.name)).all()
        for uf in ufs:
            label = f"{uf.identifier} — {uf.name}"
            uf_options.append({"value": str(uf.id), "label": label})
    except Exception:
        # En cas d'erreur de lecture, on laisse la liste vide
        uf_options = []
    # Construire les options de type avec affichage des contraintes (désactivation + info-bulle)
    from app.form_config import MovementType
    all_type_options = MovementType.choices()
    # Mapping aligné avec le workflow pour déterminer les exigences de localisation
    event_mapping = {
        "A01": ("admission", True),
        "A02": ("transfer", True),
        "A03": ("discharge", False),
        "A04": ("consultation_out", False),
        "A05": ("preadmission", False),
        "A06": ("class_change", True),
        "A07": ("from_consult", True),
        "A11": ("cancel_admission", False),
        "A12": ("cancel_transfer", False),
        "A13": ("cancel_discharge", False),
        "A21": ("temporary_leave", False),
        "A22": ("return", True),
        "A38": ("cancel_preadmission", False),
    }

    # Détermination des options autorisées et désactivées avec raison
    last_event = None
    try:
        if prefill_venue_id:
            last_movs = session.exec(
                select(Mouvement)
                .where(Mouvement.venue_id == prefill_venue_id)
                .order_by(Mouvement.when)
            ).all()
            if last_movs:
                last_event = last_movs[-1].type.split('^')[-1] if last_movs[-1].type else None
    except Exception:
        last_event = None

    # Ensemble autorisé par le graphe
    if last_event:
        allowed_by_graph = ALLOWED_TRANSITIONS.get(last_event, set())
    else:
        allowed_by_graph = {e for e in INITIAL_EVENTS if e != "A38"}

    admitted_context = {"A01", "A02", "A21", "A22", "A44", "A54", "A55", "A06", "A07"}

    def disabled_reason_for(evt: str) -> str | None:
        # Règles métier explicites
        if evt in {"A01", "A04"} and last_event not in (None, "A05", "A03"):
            return "Autorisé uniquement en début, après A05 (préadmission) ou après A03 (sortie)."
        if evt in {"A06", "A07"} and last_event not in admitted_context:
            return "Nécessite une admission active (patient admis)."
        # Graphe de transitions
        if evt not in allowed_by_graph:
            return f"Transition non autorisée depuis {last_event or 'début'}."
        return None

    # Construire la liste finale en enrichissant chaque option (requires_location, disabled, title)
    type_options = []
    for opt in all_type_options:
        if isinstance(opt, dict):
            code = str(opt.get("value", ""))
            evt = code.split("^")[-1] if "^" in code else code
            requires = bool(event_mapping.get(evt, (None, False))[1])
            reason = disabled_reason_for(evt) if evt else None
            enriched = {**opt, "requires_location": requires}
            if reason:
                enriched["disabled"] = True
                enriched["title"] = reason
            type_options.append(enriched)
        else:
            # fallback, should not happen avec MovementType.choices
            type_options.append(opt)

    fields = [
        {
            "label": "Venue (Séjour) *",
            "name": "venue_id",
            "type": "select",
            "options": venue_options,
            "value": str(prefill_venue_id),
            "required": True,
            "help": "Sélectionnez la venue concernée par ce mouvement"
        },
        {
            "label": "Type de mouvement *",
            "name": "type",
            "type": "select",
            "options": type_options,
            "required": True,
            "help": "Options autorisées selon l'état actuel. Certaines options sont grisées avec une explication (info-bulle).",
            "legend": [
                "A01/A04: autorisé uniquement en début, après A05 (préadmission) ou après A03 (sortie).",
                "A06/A07: nécessite une admission active (patient admis)."
            ]
        },
        {
            "label": "Date et heure *",
            "name": "when",
            "type": "datetime-local",
            "value": default_when_str,
            "required": True,
            "help": "Date et heure du mouvement"
        },
        {
            "label": "Unité Fonctionnelle (UF)",
            "name": "uf_id",
            "type": "select",
            "options": uf_options,
            "help": "Sélectionnez l'UF concernée"
        },
        {
            "label": "Unité d'Hébergement (UH)",
            "name": "uh_id",
            "type": "select",
            "options": [],
            "help": "Sélectionnez d'abord une UF",
            "depends_on": "uf_id"
        },
        {
            "label": "Chambre",
            "name": "chambre_id",
            "type": "select",
            "options": [],
            "help": "Sélectionnez d'abord une UH",
            "depends_on": "uh_id"
        },
        {
            "label": "Lit",
            "name": "lit_id",
            "type": "select",
            "options": [],
            "help": "Sélectionnez d'abord une chambre",
            "depends_on": "chambre_id"
        },
        {
            "label": "Localisation complète",
            "name": "location",
            "type": "text",
            "help": "Code de localisation (ex: SERV-A^LIT-101) - généré automatiquement si structure sélectionnée"
        },
        {
            "label": "Depuis (départ)",
            "name": "from_location",
            "type": "text",
            "help": "Pour les transferts : lieu de départ"
        },
        {
            "label": "Vers (arrivée)",
            "name": "to_location",
            "type": "text",
            "help": "Pour les transferts : lieu d'arrivée"
        },
        {
            "label": "Raison / Motif",
            "name": "reason",
            "type": "text",
            "help": "Motif du mouvement"
        },
        {
            "label": "Intervenant",
            "name": "performer",
            "type": "text",
            "help": "Nom de la personne ayant effectué le mouvement"
        },
        {
            "label": "Rôle de l'intervenant",
            "name": "performer_role",
            "type": "text",
            "help": "Fonction de l'intervenant (ex: IDE, Médecin)"
        },
        {
            "label": "Statut",
            "name": "status",
            "type": "select",
            "options": MouvementStatus.choices(),
            "help": "État actuel du mouvement"
        },
        {
            "label": "Note / Commentaire",
            "name": "note",
            "type": "textarea",
            "help": "Remarque libre"
        },
        {
            "label": "Numéro de séquence",
            "name": "mouvement_seq",
            "type": "number",
            "value": next_seq,
            "help": "Généré automatiquement - ne modifier que si nécessaire"
        },
    ]

    back_url = f"/mouvements?dossier_id={filter_dossier_id}" if filter_dossier_id else "/venues"
    title = "Nouveau mouvement"
    if filter_dossier_id:
        dossier = session.get(Dossier, filter_dossier_id)
        if dossier:
            title += f" pour le dossier #{dossier.dossier_seq}"

    return templates.TemplateResponse(
        request,
        "form.html",
        {
            "request": request,
            "title": title,
            "fields": fields,
            "back_url": back_url
        }
    )


@router.post("/new")
def create_mouvement(
    request: Request,
    venue_id: int = Form(...),
    type: str = Form(...),
    when: str = Form(...),
    uf_id: int = Form(None),
    uh_id: int = Form(None),
    chambre_id: int = Form(None),
    lit_id: int = Form(None),
    location: str = Form(None),
    from_location: str = Form(None),
    to_location: str = Form(None),
    reason: str = Form(None),
    performer: str = Form(None),
    status: str = Form(None),
    note: str = Form(None),
    mouvement_seq: int | None = Form(None),
    movement_type: str = Form(None),
    movement_reason: str = Form(None),
    performer_role: str = Form(None),
    session=Depends(get_session),
):
    # Parse date/time
    when_dt = datetime.fromisoformat(when)
    # Determine event code (A01, A02, ...)
    trigger_event = None
    if type:
        parts = type.split("^", 1)
        if len(parts) == 2:
            trigger_event = parts[1]

    # Server-side validation: ensure transition is allowed from current state
    if venue_id and trigger_event:
        last = session.exec(
            select(Mouvement)
            .where(Mouvement.venue_id == venue_id)
            .order_by(Mouvement.when)
        ).all()
        last_event = last[-1].type.split('^')[-1] if last else None
        allowed = (ALLOWED_TRANSITIONS.get(last_event, set()) if last_event else {e for e in INITIAL_EVENTS if e != "A38"})
        if trigger_event not in allowed:
            raise HTTPException(status_code=400, detail=f"L'événement {trigger_event} n'est pas autorisé dans l'état actuel")
        # Business constraints:
        # - A01/A04 only if initial, after A05 or after A03
        if trigger_event in {"A01", "A04"} and last_event not in (None, "A05", "A03"):
            raise HTTPException(status_code=400, detail=f"ADT^{trigger_event} interdit: autorisé uniquement en début de dossier, après A05 (préadmission) ou après une sortie définitive A03 (dernier événement: {last_event}).")
        # - A06/A07 in INSERT context (UI create) only if admission is active
        if trigger_event in {"A06", "A07"}:
            admitted_context = {"A01", "A02", "A21", "A22", "A44", "A54", "A55", "A06", "A07"}
            if last_event not in admitted_context:
                raise HTTPException(status_code=400, detail=f"ADT^{trigger_event} (INSERT) interdit: patient non admis ou venue non active (dernier événement: {last_event or 'aucun'}).")

    # Map movement_type for downstream systems (align with workflow router)
    event_mapping = {
        "A01": ("admission", True),
        "A02": ("transfer", True),
        "A03": ("discharge", False),
        "A04": ("consultation_out", False),
        "A05": ("preadmission", False),
        "A06": ("class_change", True),
        "A07": ("from_consult", True),
        "A11": ("cancel_admission", False),
        "A12": ("cancel_transfer", False),
        "A13": ("cancel_discharge", False),
        "A21": ("temporary_leave", False),
        "A22": ("return", True),
        "A38": ("cancel_preadmission", False),
    }

    # Enforce location requirement according to mapping (kept consistent with workflow router)
    requires_location = bool(event_mapping.get(trigger_event, (None, False))[1])
    if requires_location and not location:
        raise HTTPException(status_code=400, detail="La localisation est obligatoire pour ce type de mouvement")

    # Sequence generation (fallback when not provided)
    seq = mouvement_seq or get_next_sequence(session, "mouvement")
    mapped_movement_type = movement_type
    if trigger_event in event_mapping:
        mapped_movement_type = event_mapping[trigger_event][0]
    m = Mouvement(
        venue_id=venue_id,
        type=type,
        when=when_dt,
        location=location,
        from_location=from_location,
        to_location=to_location,
        reason=reason,
        performer=performer,
        status=status,
        note=note,
        mouvement_seq=seq,
        movement_type=mapped_movement_type,
        movement_reason=movement_reason,
        performer_role=performer_role,
        trigger_event=trigger_event,
    )
    session.add(m)
    session.commit()
    emit_to_senders(m, "mouvement", session)
    return RedirectResponse(url=f"/mouvements?venue_id={venue_id}", status_code=303)

@router.get("/{mouvement_id}", response_class=HTMLResponse)
def mouvement_detail(mouvement_id: int, request: Request, session=Depends(get_session)):
    m = session.get(Mouvement, mouvement_id)
    if not m:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Mouvement introuvable"}, status_code=404)
    # Compute display helpers
    # Type: prefer explicit HL7 type, fallback to trigger_event, else use movement_type badge label
    type_display = None
    if getattr(m, 'type', None):
        type_display = m.type
    elif getattr(m, 'trigger_event', None):
        type_display = f"ADT^{m.trigger_event}"
    else:
        type_display = None
    type_badge = get_type_badge(getattr(m, 'movement_type', None))

    # Status: default to 'pending' when missing (consistent with list view)
    status_badge = get_status_badge(getattr(m, 'status', 'pending'))

    return templates.TemplateResponse(
        request,
        "mouvement_detail.html",
        {
            "request": request,
            "mouvement": m,
            "type_display": type_display,
            "type_badge": type_badge,
            "status_badge": status_badge,
        }
    )


@router.get("/{mouvement_id}/edit", response_class=HTMLResponse)
def edit_mouvement(mouvement_id: int, request: Request, session=Depends(get_session)):
    m = session.get(Mouvement, mouvement_id)
    if not m:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Mouvement introuvable"}, status_code=404)
    # Fallback: derive display value if legacy 'type' is missing
    type_value = m.type if getattr(m, 'type', None) else (f"ADT^{m.trigger_event}" if getattr(m, 'trigger_event', None) else None)
    fields = [
        {"label": "Venue ID", "name": "venue_id", "type": "number", "value": m.venue_id},
        {"label": "Type (ex: ADT^A01)", "name": "type", "type": "select", "options": ["ADT^A01", "ADT^A02", "ADT^A03", "ADT^A04"], "value": type_value},
        {"label": "Quand", "name": "when", "type": "datetime-local", "value": m.when.strftime('%Y-%m-%dT%H:%M') if m.when else ''},
        {"label": "Localisation", "name": "location", "type": "text", "value": m.location},
        {"label": "Depuis (from_location)", "name": "from_location", "type": "text", "value": getattr(m,'from_location',None)},
        {"label": "Vers (to_location)", "name": "to_location", "type": "text", "value": getattr(m,'to_location',None)},
        {"label": "Raison", "name": "reason", "type": "text", "value": getattr(m,'reason',None)},
        {"label": "Intervenant", "name": "performer", "type": "text", "value": getattr(m,'performer',None)},
        {"label": "Statut", "name": "status", "type": "select", "options": ["active", "completed", "cancelled", "pending"], "value": getattr(m,'status',None)},
        {"label": "Note", "name": "note", "type": "text", "value": getattr(m,'note',None)},
        {"label": "Numéro de séquence", "name": "mouvement_seq", "type": "number", "value": m.mouvement_seq},
        {"label": "Type de mouvement", "name": "movement_type", "type": "text", "value": getattr(m, "movement_type", None)},
        {"label": "Raison du mouvement", "name": "movement_reason", "type": "text", "value": getattr(m, "movement_reason", None)},
        {"label": "Rôle de l'intervenant", "name": "performer_role", "type": "text", "value": getattr(m, "performer_role", None)},
    ]
    session.refresh(m, ["venue"])
    return templates.TemplateResponse(
        request, 
        "form.html", 
        {
            "request": request, 
            "title": "Modifier mouvement", 
            "fields": fields, 
            "action_url": f"/mouvements/{mouvement_id}/edit",
            "back_url": f"/mouvements?venue_id={m.venue_id}",
        }
    )


@router.post("/{mouvement_id}/edit")
def update_mouvement(
    mouvement_id: int,
    venue_id: int = Form(...),
    type: str = Form(...),
    when: str = Form(...),
    location: str = Form(None),
    from_location: str = Form(None),
    to_location: str = Form(None),
    reason: str = Form(None),
    performer: str = Form(None),
    status: str = Form(None),
    note: str = Form(None),
    mouvement_seq: int = Form(...),
    movement_type: str = Form(None),
    movement_reason: str = Form(None),
    performer_role: str = Form(None),
    session=Depends(get_session),
    request: Request = None,
):
    m = session.get(Mouvement, mouvement_id)
    if not m:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Mouvement introuvable"}, status_code=404)
    m.venue_id = venue_id
    m.type = type
    # Keep trigger_event in sync with the selected type
    if type:
        parts = type.split('^', 1)
        m.trigger_event = parts[1] if len(parts) == 2 else None
    else:
        m.trigger_event = None
    m.when = datetime.fromisoformat(when)
    m.location = location
    m.from_location = from_location
    m.to_location = to_location
    m.reason = reason
    m.performer = performer
    m.status = status
    m.note = note
    m.mouvement_seq = mouvement_seq
    m.movement_type = movement_type
    m.movement_reason = movement_reason
    m.performer_role = performer_role
    session.add(m); session.commit()
    emit_to_senders(m, "mouvement", session)
    return RedirectResponse(url="/mouvements", status_code=303)


@router.post("/{mouvement_id}/delete")
def delete_mouvement(mouvement_id: int, request: Request, session=Depends(get_session)):
    m = session.get(Mouvement, mouvement_id)
    if not m:
        return templates.TemplateResponse(request, "not_found.html", {"request": request, "title": "Mouvement introuvable"}, status_code=404)
    session.delete(m); session.commit()
    emit_to_senders(m, "mouvement", session)
    return RedirectResponse(url="/mouvements", status_code=303)

