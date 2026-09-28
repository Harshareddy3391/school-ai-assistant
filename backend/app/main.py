from fastapi import FastAPI

from app.core.config import settings
from app.api.schools import router as school_router
from app.api.documents import router as document_router
from app.api.chat import router as chat_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(school_router)
app.include_router(document_router)
app.include_router(chat_router)


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