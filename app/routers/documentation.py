"""Router pour l'interface de documentation."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
import markdown
from markdown.extensions.toc import TocExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.tables import TableExtension
from markdown.extensions.codehilite import CodeHiliteExtension

router = APIRouter(prefix="/documentation", tags=["documentation"])

DOC_ROOT = Path(__file__).parent.parent.parent / "Doc"


def get_doc_structure():
    """Retourne la structure de la documentation."""
    return {
        "01-Getting-Started": {
            "icon": "🚀",
            "title": "Démarrage Rapide",
            "files": ["CONTRIBUTING.md"]
        },
        "02-Validation": {
            "icon": "✅",
            "title": "Validation HL7 v2.5",
            "files": [
                "INDEX_VALIDATION_PAM.md",
                "RESUME_VALIDATION_DATATYPES.md",
                "REGLES_VALIDATION_HL7v25.md",
                "REGLES_DATATYPES_COMPLEXES_HL7v25.md",
                "VALIDATION_ORDRE_SEGMENTS.md"
            ]
        },
        "03-IHE-PAM": {
            "icon": "🏥",
            "title": "IHE PAM",
            "files": [
                "conformite_zbe.md",
                "namespaces_mouvement_finess.md"
            ]
        },
        "04-Patient-Management": {
            "icon": "👤",
            "title": "Gestion Patients",
            "files": [
                "PATIENT_IMPROVEMENTS_RECAP.md",
                "formulaire_patient_rgpd.md",
                "spec_patient_identifiers_addresses.md"
            ]
        },
        "05-Architecture": {
            "icon": "⚙️",
            "title": "Architecture",
            "files": [
                "architecture_workflows_proposal.md",
                "dossier_types.md",
                "STANDARDS.md"
            ]
        },
        "06-Integration": {
            "icon": "🔗",
            "title": "Intégration",
            "files": [
                "INTEGRATION_HL7v25_RECAP.md",
                "INTEGRATION_DATATYPES_COMPLEXES_RECAP.md",
                "FILE_IMPORT_README.md",
                "file_based_import.md",
                "endpoints_hierarchical_organization.md"
            ]
        },
        "07-Emission": {
            "icon": "📤",
            "title": "Émission",
            "files": [
                "emission_automatique.md",
                "emission_automatique_debug.md",
                "etat_reel_emission.md",
                "correction_a31_emission.md"
            ]
        },
        "08-Scenarios": {
            "icon": "🧪",
            "title": "Scénarios",
            "files": [
                "scenario_date_update.md"
            ]
        }
    }


def render_markdown(content: str) -> str:
    """Convertit Markdown en HTML avec extensions."""
    md = markdown.Markdown(extensions=[
        TocExtension(baselevel=1, toc_depth=3),
        FencedCodeExtension(),
        TableExtension(),
        CodeHiliteExtension(css_class='highlight', linenums=False),
        'nl2br',
        'sane_lists'
    ])
    return md.convert(content)


@router.get("/", response_class=HTMLResponse)
async def documentation_home(request: Request):
    """Page d'accueil de la documentation."""
    structure = get_doc_structure()
    
    # Lire INDEX.md
    index_path = DOC_ROOT / "INDEX.md"
    index_content = ""
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            index_content = render_markdown(f.read())
    
    return request.app.state.templates.TemplateResponse(
        "documentation.html",
        {
            "request": request,
            "structure": structure,
            "index_content": index_content,
            "current_doc": None
        }
    )


@router.get("/{category}/{filename:path}", response_class=HTMLResponse)
async def view_document(request: Request, category: str, filename: str):
    """Affiche un document de la documentation."""
    structure = get_doc_structure()
    
    # Construire le chemin du fichier
    doc_path = DOC_ROOT / category / filename
    
    if not doc_path.exists():
        # Fallback: chercher à la racine du projet
        doc_path = DOC_ROOT.parent / filename
    
    if not doc_path.exists() or not doc_path.is_file():
        return request.app.state.templates.TemplateResponse(
            "documentation.html",
            {
                "request": request,
                "structure": structure,
                "error": f"Document non trouvé : {category}/{filename}",
                "current_doc": None
            }
        )
    
    # Lire et convertir le document
    with open(doc_path, 'r', encoding='utf-8') as f:
        content = render_markdown(f.read())
    
    # Extraire le titre du premier h1
    title = filename.replace('.md', '').replace('_', ' ').replace('-', ' ').title()
    
    return request.app.state.templates.TemplateResponse(
        "documentation.html",
        {
            "request": request,
            "structure": structure,
            "doc_content": content,
            "doc_title": title,
            "current_doc": {"category": category, "filename": filename}
        }
    )


@router.get("/search", response_class=HTMLResponse)
async def search_documentation(request: Request, q: str = ""):
    """Recherche dans la documentation."""
    structure = get_doc_structure()
    results = []
    
    if q and len(q) >= 3:
        query_lower = q.lower()
        
        # Parcourir tous les fichiers
        for category, info in structure.items():
            for filename in info["files"]:
                doc_path = DOC_ROOT / category / filename
                if doc_path.exists():
                    try:
                        with open(doc_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if query_lower in content.lower():
                                # Extraire un snippet
                                lines = content.split('\n')
                                matching_lines = [
                                    (i, line) for i, line in enumerate(lines)
                                    if query_lower in line.lower()
                                ]
                                
                                snippet = ""
                                if matching_lines:
                                    line_idx, line = matching_lines[0]
                                    start = max(0, line_idx - 2)
                                    end = min(len(lines), line_idx + 3)
                                    snippet = '\n'.join(lines[start:end])
                                
                                title = filename.replace('.md', '').replace('_', ' ').replace('-', ' ').title()
                                results.append({
                                    "category": category,
                                    "filename": filename,
                                    "title": title,
                                    "snippet": snippet,
                                    "matches": len(matching_lines)
                                })
                    except Exception:
                        pass
    
    return request.app.state.templates.TemplateResponse(
        "documentation.html",
        {
            "request": request,
            "structure": structure,
            "search_query": q,
            "search_results": results,
            "current_doc": None
        }
    )
