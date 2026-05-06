# Codebase Architecture

## Backend Structure
```
main.py                  — FastAPI app, CORS, router includes, audio endpoint, frontend mount
api/index.py             — Vercel serverless entry point (imports main:app)
routers/
  generate.py            — POST /generate/lesson-plan and lesson-type/section endpoints
  ingest.py              — POST /ingest/textbook, /ingest/sow
  authentication.py      — login, logout, signup
  authorization.py       — RBAC logic
src/
  models.py              — All Pydantic models (GenerateRequest, GenerateResponse, LessonType, Subject, SOW models)
  config.py              — Env var loading
  db/client.py           — DatabaseClient singleton (db) — all Supabase queries
  generation/
    lesson_generator.py  — LessonGenerator class: generate(), generate_math(), generate_art(), generate_cs(), generate_islamiat(), generate_nazra()
    router.py            — ContextRouter class: retrieve_context(), retrieve_math_context(), retrieve_art_context(), retrieve_cs_context(), retrieve_generalized_context()
    sow_matcher.py       — SOW parsing/lookup helpers, format_*_for_prompt() functions
    book_selector.py     — Book type validation and selection logic
  ingestion/
    pdf_processor.py     — PDFProcessor: Vision LLM OCR for textbooks
    ade_processor.py     — ADEProcessor: LandingAI document extraction
    sow_parser.py        — SOWParser: Vision LLM SOW parsing
  prompts/templates.py   — All LLM system prompts (ENG, MATHS, ART, CS, ISLAMIAT, NAZRA) + LESSON_ARCHITECT_PROMPT
utils/                   — Standalone ingestion scripts (ingest_book.py, universal_sow_extractor.py, etc.)
```

## Frontend Structure
```
frontend/src/
  App.jsx          — Main app: Generate / Upload / History tabs
  Login.jsx        — Supabase auth
  Signup.jsx       — User registration
  History.jsx      — Saved lesson plan browser
  UsageIndicator.jsx — Cost/token metrics display
  pdfExport.js     — Client-side PDF generation (jsPDF)
```

## Database Tables
- `textbooks` — OCR'd pages as JSONB, grade stored as `"2"` (numeric string)
- `sow_entries` — Structured SOW JSON, grade stored as `"Grade 2"`
- `lesson_plans` — Generated HTML + usage metrics in `metadata` JSONB column
- `users` — Profiles linked to Supabase auth.users

## Critical Grade Format Note
SOW uses `"Grade 2"`, textbooks use `"2"`. `ContextRouter.normalize_grade()` converts between them.

## Generation Flow
1. `POST /generate/lesson-plan` → router dispatches by Subject
2. `LessonGenerator.generate_*()` → `ContextRouter.retrieve_*_context()` → DB fetch SOW + textbook pages
3. `_build_prompt()` → `_call_llm()` (OpenRouter, 180s timeout, 8000 max_tokens)
4. `_inject_exercises()` for English new-format SOW
5. `db.insert_lesson_plan()` → return `GenerateResponse`

## Vite Dev Proxy (port 3000 → 8000)
Routes: `/ingest`, `/generate`, `/health`, `/audio`, `/authentication`
