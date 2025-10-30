# app/routers/interop.py
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import select
from app.db import get_session
from app.models_endpoints import SystemEndpoint

router = APIRouter(prefix="/interop", tags=["interop"])

@router.post("/mllp/start/{endpoint_id}")
async def start_endpoint(endpoint_id: int, request: Request, session=Depends(get_session)):
    e = session.get(SystemEndpoint, endpoint_id)
    if not e or e.kind != "MLLP":
        return JSONResponse({"error": "Endpoint non trouvé ou pas MLLP"}, status_code=400)
    await request.app.state.mllp_manager.start_endpoint(e)
    return {"message": f"MLLP '{e.name}' démarré sur {e.host}:{e.port}"}

@router.post("/mllp/stop/{endpoint_id}")
async def stop_endpoint(endpoint_id: int, request: Request):
    await request.app.state.mllp_manager.stop_endpoint(endpoint_id)
    return {"message": f"MLLP endpoint {endpoint_id} arrêté"}

@router.post("/mllp/reload")
async def reload_all(request: Request, session=Depends(get_session)):
    await request.app.state.mllp_manager.reload_all(session)
    return {"message": "Tous les serveurs MLLP ont été rechargés", "running": request.app.state.mllp_manager.running_ids()}


@router.get("/mllp/status")
def mllp_status(request: Request):
    mgr = request.app.state.mllp_manager
    running = mgr.running_ids()
    # Si tu veux aussi renvoyer les (host,port)
    bindings = []
    for eid, srv in mgr.servers.items():
        try:
            s = srv.sockets[0]
            host, port = s.getsockname()[:2]
            bindings.append({"endpoint_id": eid, "host": host, "port": port})
        except Exception:
            pass
    return {"running_ids": running, "bindings": bindings}