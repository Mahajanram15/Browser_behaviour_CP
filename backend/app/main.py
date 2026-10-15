from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.health import router as health_router
from backend.app.api.routes import router as api_router

def create_app() -> FastAPI:
    """
    Application factory for the Behavioral Integrity Verification System.
    """
    app = FastAPI(
        title="Browser-to-Backend Behavioral Integrity Verification API",
        description="Cross-layer behavioral security system correlating browser motor dynamics with backend API access patterns.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS for frontend dashboard and client SDK
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(health_router)
    app.include_router(api_router)

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
