"""
Test minimal de rendu du template endpoint_detail.html
"""
from fastapi.templating import Jinja2Templates
from fastapi import Request
from sqlmodel import Session, create_engine, select
from app.models_transport import SystemEndpoint
from app.models_structure_fhir import GHTContext, EntiteJuridique
from app.routers.endpoints import registry

templates = Jinja2Templates(directory="app/templates")
engine = create_engine("sqlite:///poc.db")

# Mock request
class MockRequest:
    def __init__(self):
        self.url = type('obj', (object,), {'path': '/endpoints/1'})()
        self.state = type('obj', (object,), {'ght_context': None, 'ej_context': None})()
        self.session = {}
        
    @property
    def headers(self):
        return {}

with Session(engine) as session:
    endpoint_id = 1
    e = session.get(SystemEndpoint, endpoint_id)
    
    if not e:
        print("✗ Endpoint not found")
    else:
        print(f"✓ Endpoint found: {e.name}")
        
        ghts = session.exec(select(GHTContext).where(GHTContext.is_active == True)).all()
        ejs = session.exec(select(EntiteJuridique).where(EntiteJuridique.is_active == True)).all()
        is_running = endpoint_id in set(registry.running_ids())
        
        print(f"✓ GHTs: {len(ghts)}")
        print(f"✓ EJs: {len(ejs)}")
        print(f"✓ is_running: {is_running}")
        
        try:
            request = MockRequest()
            result = templates.TemplateResponse("endpoint_detail.html", {
                "request": request,
                "e": e,
                "is_running": is_running,
                "ghts": ghts,
                "ejs": ejs
            })
            print(f"✓ Template rendered successfully")
            print(f"  Status: {result.status_code}")
        except Exception as ex:
            print(f"✗ Template rendering error: {ex}")
            import traceback
            traceback.print_exc()
