"""
Middleware de gestion des contextes (GHT, Patient, Dossier).

Objectif
- Exposer, pour chaque requête, le contexte courant dans `request.state` afin que
    les vues/routeurs puissent l'utiliser (affichage d'un badge, filtrage, etc.).
- Centraliser la récupération depuis la session (cookie) et éviter de répéter
    cette logique dans chaque route.

Notes d'implémentation
- Les fonctions `get_active_*_context` lisent l'identifiant en session puis
    recharge l'entité depuis la base pour disposer d'un objet complet.
- Le middleware ajoute ces objets sur `request.state` avant d'appeler la suite.
- En mode tests (env TESTING=1), aucune redirection n'est déclenchée ici pour ne
    pas perturber la navigation des tests UI. L'application peut afficher une
    bannière invitant l'utilisateur à choisir un contexte.
"""

from typing import Optional
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.db import get_session
from app.models_structure_fhir import GHTContext
from app.models import Patient, Dossier
import os


async def get_active_ght_context(request: Request) -> Optional[GHTContext]:
    """
    Récupère le contexte GHT actif depuis la session et renvoie l'objet complet.

    Processus
    - Lit `ght_context_id` dans la session (cookies signés Starlette).
    - Si présent, ouvre une session DB courte pour recharger `GHTContext`.
    - Renvoie l'entité ou None si rien n'est défini/accessible.
    """
    try:
        context_id = request.session.get("ght_context_id")
        if context_id:
            session = next(get_session())
            try:
                return session.get(GHTContext, context_id)
            finally:
                session.close()
    except Exception:
        pass
    return None


async def get_active_patient_context(request: Request) -> Optional[Patient]:
    """Récupère le patient courant depuis la session et le charge si possible."""
    try:
        patient_id = request.session.get("patient_id")
        if patient_id:
            session = next(get_session())
            try:
                return session.get(Patient, patient_id)
            finally:
                session.close()
    except Exception:
        pass
    return None


async def get_active_dossier_context(request: Request) -> Optional[Dossier]:
    """Récupère le dossier courant depuis la session et le charge si possible."""
    try:
        dossier_id = request.session.get("dossier_id")
        if dossier_id:
            session = next(get_session())
            try:
                return session.get(Dossier, dossier_id)
            finally:
                session.close()
    except Exception:
        pass
    return None


class GHTContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour injecter les contextes (GHT, Patient, Dossier) sur `request.state`.

    - Utilise BaseHTTPMiddleware pour être installé via `app.add_middleware(...)`.
    - Ajoute systématiquement `request.state.ght_context`, `patient_context`,
      `dossier_context` pour les templates et les dépendances.
    - Ne force pas la redirection ici (comportement non intrusif) — les routes
      peuvent imposer un contexte via les dépendances (ex: `require_ght_context`).
    """

    API_PATH_PREFIXES = (
        "/structure",
        "/fhir",
        "/api",
        "/messages",
    )
    ALLOWED_PATHS = {
        "/",
        "/guide",
        "/guide/",
        "/api-docs",
        "/api-docs/",
    }
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    async def dispatch(self, request: Request, call_next):
        # Ajouter le contexte GHT aux attributs de la requête
        request.state.ght_context = await get_active_ght_context(request)
        # Ajouter les contextes Patient/Dossier si présents
        request.state.patient_context = await get_active_patient_context(request)
        request.state.dossier_context = await get_active_dossier_context(request)

        # En tests, on évite les redirections automatiques pour ne pas casser
        # les scénarios Playwright. Les pages peuvent afficher un message doux.
        if os.getenv("TESTING", "0") in ("1", "true", "True"):
            return await call_next(request)

        # Historique: une redirection globale vers /admin/ght était effectuée
        # lorsqu'aucun contexte n'était défini. Cela surprenait la navigation.
        # On préfère maintenant une approche "douce" avec bannière dans la base.html.

        return await call_next(request)
