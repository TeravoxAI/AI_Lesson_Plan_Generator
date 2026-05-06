# AI Lesson Plan Generator — Project Overview

## Purpose
AI-powered lesson plan generator for APSACS (Army Public Schools & Colleges System Secretariat) Pakistan.
Teachers select grade, subject, lesson/unit, and page numbers → system fetches Scheme of Work (SOW) context + OCR'd textbook pages → calls LLM via OpenRouter → returns a formatted HTML lesson plan.

## Tech Stack
- **Backend**: FastAPI + Python 3.10+ (`main.py`, `routers/`, `src/`)
- **Frontend**: React 18 + Vite 5 (`frontend/src/`)
- **Database**: Supabase (PostgreSQL) — textbooks, sow_entries, lesson_plans, users tables
- **LLM**: OpenRouter API (model configurable via `LLM_MODEL` env var)
- **Deployment**: Vercel serverless (`api/index.py` entry point, `vercel.json`)
- **Audio storage**: Vercel Blob Storage (production) / local filesystem (dev)

## Subjects Supported
English, Mathematics, Art, Computer Studies, Islamiat, Nazra, Urdu

## Key Env Vars (`.env`)
- `SUPABASE_URL`, `SUPABASE_KEY`
- `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `LLM_MODEL`
- `VERCEL_BLOB_BASE_URL` (production only)
