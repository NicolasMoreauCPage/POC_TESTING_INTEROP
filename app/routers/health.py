from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    """Health check endpoint for tests"""
    return {"status": "ok"}