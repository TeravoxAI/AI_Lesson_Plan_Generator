"""
Lesson Plan Generator - FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from routers import ingest, generate, authentication, authorization

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
app.include_router(authentication.router, prefix="/authentication")
app.include_router(authorization.router, prefix="/authorization")


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
            },
            "media": {
                "GET /audio/{grade}/{subject}/{track_number}": "Serve audio track files"
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


@app.get("/audio/{grade}/{subject}/{track_number}")
async def serve_audio(grade: str, subject: str, track_number: int):
    """
    Serve audio files for a specific grade, subject, and track number.

    Args:
        grade: Grade level (e.g., "Grade 2" or "2")
        subject: Subject name (e.g., "English")
        track_number: Track number (e.g., 70)

    Returns:
        Audio file as MP3
    """
    from fastapi import HTTPException

    # Normalize grade to extract number only
    grade_num = grade.replace("Grade ", "").replace("grade ", "").strip()

    # Construct audio folder path: Grade_2_English_Tracks
    audio_folder = f"Grade_{grade_num}_{subject}_Tracks"

    # File naming pattern: GE2_Track_70.mp3
    audio_filename = f"GE{grade_num}_Track_{track_number:02d}.mp3"

    # Try multiple paths (for local dev and Vercel deployment)
    base_dir = os.path.dirname(__file__)
    possible_paths = [
        os.path.join(base_dir, "api", "audio_tracks", audio_folder, audio_filename),  # Vercel
        os.path.join(base_dir, audio_folder, audio_filename),  # Local dev
    ]

    audio_path = None
    for path in possible_paths:
        if os.path.exists(path):
            audio_path = path
            break

    # If not found, try alternative naming without leading zero
    if not audio_path:
        audio_filename = f"GE{grade_num}_Track_{track_number}.mp3"
        possible_paths = [
            os.path.join(base_dir, "api", "audio_tracks", audio_folder, audio_filename),
            os.path.join(base_dir, audio_folder, audio_filename),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                audio_path = path
                break

    if not audio_path:
        raise HTTPException(
            status_code=404,
            detail=f"Audio track {track_number} not found for Grade {grade_num} {subject}"
        )

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'inline; filename="{audio_filename}"',
            "Accept-Ranges": "bytes"
        }
    )


# Mount frontend static files (if frontend directory exists)
frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
