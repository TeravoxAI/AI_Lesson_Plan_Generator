# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered lesson plan generator that creates curriculum-aligned lesson plans using LLM. Processes textbooks (PDF OCR) and Scheme of Work (SOW) documents to generate structured lesson plans with embedded resources.

**Tech Stack:**
- Backend: FastAPI + Python 3.10+
- Frontend: React + Vite
- Database: Supabase (PostgreSQL)
- LLM: OpenRouter API (GPT-4, Claude, etc.)
- Deployment: Vercel (serverless)

## Development Commands

### Backend
```bash
# Activate virtual environment
source venv/bin/activate

# Run development server (with hot reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run production server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend
```bash
cd frontend
npm install              # Install dependencies
npm run dev              # Development server (port 3000)
npm run build            # Production build
npm run preview          # Preview production build
```

### Environment Setup
Required `.env` variables:
- `SUPABASE_URL`, `SUPABASE_KEY` - Database connection
- `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `LLM_MODEL` - LLM configuration
- `VERCEL_BLOB_BASE_URL` - Audio storage (production only)

## Architecture

### Backend Structure
```
routers/          - API route handlers
├── generate.py   - Lesson plan generation endpoints
├── ingest.py     - Document upload/processing endpoints
├── authentication.py - User auth
└── authorization.py  - RBAC logic

src/
├── generation/   - Core lesson generation logic
│   ├── lesson_generator.py - LLM prompt construction and generation
│   ├── sow_matcher.py      - SOW context retrieval and matching
│   ├── book_selector.py    - Textbook selection logic
│   └── router.py           - Context routing for generation
├── ingestion/    - Document processing
│   ├── pdf_processor.py    - PDF OCR extraction
│   ├── ade_processor.py    - ADE (AI Document Extraction) for SOW
│   └── sow_parser.py       - SOW document parsing
├── prompts/      - LLM system prompts and templates
├── db/           - Database client and schema
├── models.py     - Pydantic models
└── config.py     - Configuration settings
```

### Frontend Structure
```
frontend/src/
├── App.jsx              - Main application component (tabs: Generate, Upload, History)
├── Login.jsx, Signup.jsx - Authentication
└── UsageIndicator.jsx   - Token/cost metrics display
```

### Database Schema
- **textbooks** - Stores PDF content (OCR extracted) as JSONB with page-level granularity
- **sow_entries** - Stores complete SOW extraction as structured JSONB
- **lesson_plans** - Generated plans with usage metadata (cost, tokens, time) in JSONB
- **users** - User profiles linked to auth.users

## Key Concepts

### Grade Normalization
**Critical:** Different parts of the system use different grade formats:
- SOW database: `"Grade 2"`
- Textbook database: `"2"` (numeric string)
- Routers normalize automatically - be aware when querying directly

### Subject Workflows

**English:**
- Uses `lesson_type` + `lesson_number` (page_start)
- Lesson types: recall, vocabulary, listening, reading, reading_comprehension, grammar, oral_speaking, creative_writing
- Automatically selects appropriate textbooks (LB, AB, ORT, TR) based on lesson type
- Book references in SOW use tags: LB (Learner's Book), AB (Activity Book), ORT (Oxford Reading Tree), TR (Teacher Resource)

**Mathematics:**
- Uses `unit_number` + `course_book_pages` + optional `workbook_pages`
- Lesson types: concept, practice
- Different SOW structure (simplified, no lessons, just units)

### Document Processing Flow

1. **Textbook Ingestion:**
   - Upload PDF → OCR extraction (pdfplumber) → Store as JSONB with page numbers
   - Each page stored with metadata: `{"page": 1, "text": "...", "images": []}`

2. **SOW Ingestion:**
   - Upload DOCX → ADE extraction (landingai-ade) → Parse structured JSON → Store in database
   - English: Hierarchical (units → lessons → lesson_plan_types)
   - Math: Flat (units → content)

3. **Lesson Generation:**
   - Fetch SOW context for lesson/unit
   - Retrieve referenced textbook pages
   - Extract external resources (YouTube videos, audio tracks)
   - Build prompt with system prompt + SOW + textbook content
   - Call LLM via OpenRouter
   - Save to database with usage metrics

### Audio Track Handling

Audio files must be in folders: `Grade_{number}_{subject}_Tracks/`
- File naming: `GE{grade}_Track_{number:02d}.mp3`
- Example: Grade 2, Track 70 → `Grade_2_English_Tracks/GE2_Track_70.mp3`
- Production: Redirects to Vercel Blob Storage
- Development: Serves from local filesystem

## Vercel Deployment

- Entry point: `api/index.py` (imports `main:app`)
- Frontend build: `frontend/dist/` served at `/app`
- URL rewrites defined in `vercel.json`
- Audio files uploaded to Vercel Blob Storage (binary files not supported in serverless)

## Important Notes

### When Adding New Lesson Types
1. Add to `src/models.py` → `LessonType` enum
2. Create prompt template in `src/prompts/templates.py`
3. Update `src/generation/book_selector.py` for book selection logic
4. Update frontend lesson type selection in `App.jsx`

### When Querying Database
- Use `src/db/client.py` (`db` singleton) - it handles connection pooling
- SOW and textbook content are JSONB - use PostgreSQL JSON operators
- Always check grade format when joining tables

### Common Patterns
- **Usage tracking:** All generation metrics stored in `lesson_plans.metadata` JSONB column
- **Resource extraction:** YouTube video IDs extracted from URLs, audio tracks mapped from SOW references
- **Error handling:** Routers return structured error responses with `success: false` and `error` field
- **CORS:** Configured in `main.py` for frontend proxy during development

## Testing & Debugging

- Check SOW context: Use `check_sow.py` utility script
- Database migrations: See `MIGRATION_NEEDED.md` for schema updates
- Frontend dev server proxies API calls to `localhost:8000` (configured in `vite.config.js`)
- Check logs for audio path resolution issues (multiple fallback paths attempted)
