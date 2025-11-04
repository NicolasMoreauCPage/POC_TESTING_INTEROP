from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/guide", tags=["guide"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def user_guide(request: Request):
    return templates.TemplateResponse(
        "user_guide.html",
        {"request": request},
    )
