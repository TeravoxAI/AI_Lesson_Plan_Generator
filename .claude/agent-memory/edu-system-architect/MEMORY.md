# edu-system-architect - Agent Memory

## Project Context
AI Lesson Plan Generator - Educational technology platform for Pakistani students using FastAPI, React, Supabase, and OpenRouter LLM.

## System Architecture Decisions

### Database Architecture
- **Schema Pattern**: JSONB storage for flexibility with structured educational data
- **Tables**: textbooks (OCR content), sow_entries (curriculum), lesson_plans (generated plans), users
- **Key Design**: Page-level granularity for textbooks enables precise content retrieval

### Technology Stack Rationale
- **FastAPI**: Chosen for async support, automatic API docs, and Python LLM ecosystem
- **Supabase**: PostgreSQL with built-in auth, real-time capabilities, JSONB support
- **OpenRouter**: Multi-model LLM access for cost optimization and fallback options
- **Vercel**: Serverless deployment for auto-scaling during peak usage

### API Design Patterns
- **Generation Endpoint**: Streams responses for better UX during LLM generation
- **Ingestion Endpoints**: Separate routes for textbooks vs SOW (different processing pipelines)
- **Authorization**: RBAC pattern with user roles for multi-tenant support

### Educational Domain Considerations
- **Grade Normalization Challenge**: SOW uses "Grade 2", textbooks use "2" - routers handle normalization
- **Subject-Specific Workflows**: English (8 lesson types) vs Math (2 lesson types) require different data models
- **Resource Integration**: Audio tracks, YouTube videos, textbook pages all linked via JSONB references

## Architectural Patterns

### Document Processing Pipeline
1. Upload (PDF/DOCX) → 2. OCR/ADE Extraction → 3. Structured JSON → 4. Database Storage
- OCR: pdfplumber for textbooks
- ADE: landingai-ade for SOW documents

### Lesson Generation Flow
1. SOW Context Retrieval → 2. Textbook Content Matching → 3. Resource Extraction → 4. LLM Prompt Construction → 5. Generation → 6. Usage Tracking

### Deployment Architecture
- **Vercel Serverless**: `api/index.py` entry point, frontend in `frontend/dist/`
- **Static Assets**: Vercel Blob Storage for audio files (serverless doesn't support large binaries)
- **URL Rewrites**: Configured in `vercel.json` for SPA routing

## Integration Points
- **OpenRouter API**: Multi-model support (GPT-4, Claude, etc.)
- **Supabase Auth**: JWT-based authentication
- **Vercel Blob**: Binary storage for audio tracks

## Scalability Considerations
- **JSONB Indexing**: Required for fast SOW/textbook queries at scale
- **Connection Pooling**: Database client handles connection management
- **Serverless Limits**: 10-second timeout for Vercel functions - generation may need async pattern

## Future Architecture Considerations
- **Real-time Collaboration**: Consider WebSocket support for multi-teacher editing
- **Content Versioning**: Curriculum changes require versioned SOW/textbook storage
- **Analytics Pipeline**: Separate analytics database for usage metrics and insights
- **Caching Layer**: Redis/CDN for frequently accessed textbook pages

---
*Last updated: 2026-02-15*
