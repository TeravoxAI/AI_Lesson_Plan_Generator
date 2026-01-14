"""
Lesson Plan Generator - FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from routers import ingest, generate

# Create FastAPI app
app = FastAPI(
    title="Lesson Plan Generator API",
    description="AI-powered curriculum-aware lesson plan generation system",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ingest.router, prefix="/ingest")
app.include_router(generate.router, prefix="/generate")


@app.get("/")
async def root():
    """API root - provides basic info"""
    return {
        "name": "Lesson Plan Generator API",
        "version": "1.0.0",
        "endpoints": {
            "ingest": {
                "POST /ingest/textbook": "Upload and process a textbook PDF",
                "POST /ingest/sow": "Upload and process a Scheme of Work document",
                "GET /ingest/books": "List all ingested textbooks",
                "GET /ingest/sow": "List SOW entries"
            },
            "generate": {
                "POST /generate/lesson-plan": "Generate a lesson plan",
                "GET /generate/lesson-types": "Get available lesson types",
                "GET /generate/lesson-types/{subject}": "Get lesson types for a subject"
            }
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from src.db.client import db
    
    return {
        "status": "healthy",
        "database_connected": db.is_connected()
    }


# Mount frontend static files (if frontend directory exists)
frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
