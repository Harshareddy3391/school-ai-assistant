from fastapi import FastAPI

from app.core.config import settings
from app.api.schools import router as school_router
from app.api.documents import router as document_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)


app.include_router(school_router)
app.include_router(document_router)


@app.get("/")
def root():
    return {
        "message": "School AI Assistant API is running",
        "version": settings.APP_VERSION
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }