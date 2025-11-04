from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.models_endpoints import SystemEndpoint
from app.models_scenarios import InteropScenario, InteropScenarioStep
from app.services.scenario_runner import ScenarioExecutionError, get_scenario, send_scenario, send_step
from app.utils.flash import flash

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_class=HTMLResponse)
def list_scenarios(request: Request, session: Session = Depends(get_session)):
    scenarios = session.exec(select(InteropScenario).order_by(InteropScenario.name)).all()
    rows = []
    for sc in scenarios:
        rows.append(
            {
                "cells": [
                    sc.name,
                    sc.protocol,
                    len(sc.steps or []),
                    sc.category or "",
                    sc.tags or "",
                ],
                "detail_url": f"/scenarios/{sc.id}",
            }
        )

    ctx = {
        "request": request,
        "title": "Scénarios d'interopération",
        "breadcrumbs": [{"label": "Scénarios", "url": "/scenarios"}],
        "headers": ["Nom", "Protocole", "Étapes", "Catégorie", "Tags"],
        "rows": rows,
        "show_actions": False,
    }
    return templates.TemplateResponse(request, "list.html", ctx)


@router.get("/{scenario_id}", response_class=HTMLResponse)
def scenario_detail(scenario_id: int, request: Request, session: Session = Depends(get_session)):
    scenario = get_scenario(session, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scénario introuvable")

    endpoints = session.exec(
        select(SystemEndpoint)
        .where(SystemEndpoint.is_enabled == True)
        .where(SystemEndpoint.role.in_(["sender", "both"]))
        .order_by(SystemEndpoint.name)
    ).all()

    steps = sorted(scenario.steps, key=lambda s: s.order_index)

    ctx = {
        "request": request,
        "scenario": scenario,
        "steps": steps,
        "endpoints": endpoints,
        "breadcrumbs": [
            {"label": "Scénarios", "url": "/scenarios"},
            {"label": scenario.name, "url": f"/scenarios/{scenario.id}"},
        ],
    }
    return templates.TemplateResponse(request, "scenario_detail.html", ctx)


@router.post("/{scenario_id}/send")
async def scenario_send(
    scenario_id: int,
    request: Request,
    endpoint_id: int = Form(...),
    step_id: Optional[int] = Form(None),
    session: Session = Depends(get_session),
):
    scenario = get_scenario(session, scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scénario introuvable")

    endpoint = session.get(SystemEndpoint, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint introuvable")

    try:
        if step_id:
            step = session.get(InteropScenarioStep, step_id)
            if not step:
                raise HTTPException(status_code=404, detail="Étape introuvable")
            log = await send_step(session, step, endpoint)
            if log.status == "sent":
                level = "success"
            elif log.status == "skipped":
                level = "info"
            else:
                level = "warning"
            flash(
                request,
                f"Étape #{step.order_index} envoyée vers {endpoint.name} (statut {log.status}).",
                level=level,
            )
        else:
            logs = await send_scenario(session, scenario, endpoint)
            errors = [log for log in logs if log.status not in {"sent", "skipped"}]
            skipped = [log for log in logs if log.status == "skipped"]
            if errors:
                flash(
                    request,
                    f"Scénario {scenario.name} envoyé avec {len(errors)} messages en anomalie.",
                    level="warning",
                )
            elif skipped:
                flash(
                    request,
                    f"Scénario {scenario.name} exécuté ({len(logs)} messages, {len(skipped)} ignorés car Zxx).",
                    level="info",
                )
            else:
                flash(
                    request,
                    f"Scénario {scenario.name} envoyé avec succès ({len(logs)} messages).",
                    level="success",
                )
    except ScenarioExecutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RedirectResponse(url=f"/scenarios/{scenario_id}?sent=1", status_code=303)
