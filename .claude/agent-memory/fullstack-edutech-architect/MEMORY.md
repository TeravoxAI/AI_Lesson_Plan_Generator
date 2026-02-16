# fullstack-edutech-architect - Agent Memory

## Project Overview
AI Lesson Plan Generator for Pakistani students - FastAPI backend, React frontend, Supabase PostgreSQL, OpenRouter LLM integration.

## Database Schema Patterns

### Textbooks Table
```
- id (uuid)
- subject (text)
- grade (text) - stores as "2" not "Grade 2"
- book_type (text) - "LB", "AB", "ORT", "TR"
- content (jsonb) - array of {page: int, text: string, images: []}
```
**Pattern**: Page-level JSONB for granular retrieval

### SOW Entries Table
```
- id (uuid)
- grade (text) - stores as "Grade 2"
- subject (text)
- content (jsonb) - hierarchical structure (units → lessons)
```
**Critical**: Grade format differs from textbooks!

### Lesson Plans Table
```
- id (uuid)
- user_id (uuid, FK to users)
- grade, subject, lesson_type, lesson_number
- content (text) - generated markdown
- metadata (jsonb) - {cost, tokens, time, model}
```
**Pattern**: Usage tracking in JSONB for analytics

### Users Table
```
- id (uuid, FK to auth.users)
- role (text) - for RBAC
- created_at, updated_at
```

## Frontend Architecture

### Component Structure
```
frontend/src/
├── App.jsx - Main tabs (Generate, History, Upload, Library)
├── History.jsx - User lesson plan history view (NEW - 2026-02-16)
├── Login.jsx, Signup.jsx - Auth
└── UsageIndicator.jsx - Token metrics
```
**Pattern**: Separate components for major features, integrate via App.jsx

### State Management
- React useState for local state
- Supabase client for auth state
- No global state library (keep it simple)

### API Integration
- Development: Vite proxy to `localhost:8000`
- Production: Vercel serves frontend + API from same domain
- Fetch API with async/await pattern

## Backend Code Organization

### Router Pattern
```
routers/
├── generate.py - POST /generate/lesson-plan, GET /generate/history
├── ingest.py - POST /ingest/textbook, /ingest/sow
├── authentication.py - Login/signup
└── authorization.py - RBAC middleware
```
**Key Endpoints**:
- `GET /generate/history` - User-specific lesson plan history (auth required)

### Service Layer
```
src/generation/
├── lesson_generator.py - Core LLM logic
├── sow_matcher.py - Context retrieval
├── book_selector.py - Textbook selection
└── router.py - Context routing
```

### Data Processing
```
src/ingestion/
├── pdf_processor.py - OCR with pdfplumber
├── ade_processor.py - AI Document Extraction
└── sow_parser.py - Parse structured JSON
```

## Key Implementation Patterns

### Grade Normalization
```python
# In routers - always normalize before DB queries
if subject == "Mathematics":
    grade_for_textbook = str(grade).replace("Grade ", "")
    grade_for_sow = f"Grade {grade_for_textbook}"
```

### Book Selection Logic (English)
- **Recall/Vocabulary/Grammar**: Learner's Book (LB)
- **Listening**: Audio tracks + Teacher Resource (TR)
- **Reading/Reading Comprehension**: Oxford Reading Tree (ORT)
- **Oral Speaking/Creative Writing**: Activity Book (AB) + LB

### Audio File Resolution
```python
# Pattern: Grade_{grade}_{subject}_Tracks/GE{grade}_Track_{number:02d}.mp3
# Example: Grade_2_English_Tracks/GE2_Track_70.mp3
```
**Production**: Redirect to Vercel Blob URL

### Error Handling Pattern
```python
return {"success": False, "error": "message"}
# vs
return {"success": True, "data": {...}}
```

## Database Query Patterns

### JSONB Queries
```python
# Retrieve SOW for specific lesson
sow = db.table("sow_entries").select("content").eq("grade", grade).eq("subject", subject).single()
# Access nested JSONB
lesson_data = sow['content']['units'][0]['lessons'][0]
```

### Textbook Page Retrieval
```python
# Get specific pages from JSONB array
pages = db.table("textbooks").select("content").eq("grade", grade).eq("book_type", "LB").single()
relevant_pages = [p for p in pages['content'] if p['page'] in [1,2,3]]
```

## Performance Optimization

### Database Indexing
- Create GIN index on JSONB columns for fast queries
- Index on (grade, subject, book_type) for textbooks

### Caching Strategy
- Textbook content rarely changes - good candidate for caching
- SOW content versioned - cache with version key
- Generated lesson plans - cache by (grade, subject, lesson_type, lesson_number)

## UI/UX Patterns

### Loading States
- Show spinner during LLM generation (can take 30-60 seconds)
- Streaming responses for better perceived performance

### Error Display
- Toast notifications for API errors
- Inline validation for form fields
- Clear error messages for missing resources (e.g., "Textbook not found for Grade 2 English")

## Development Workflow

### Local Development
```bash
# Backend
source venv/bin/activate
uvicorn main:app --reload

# Frontend
cd frontend && npm run dev
```

### Environment Variables
- `.env` for backend (Supabase, OpenRouter, Vercel Blob)
- Frontend uses `import.meta.env` for Vite

## Common Issues & Solutions

### Grade Format Mismatch
**Problem**: Queries fail when mixing "Grade 2" and "2"
**Solution**: Normalize at router level before DB queries

### Audio Track Not Found
**Problem**: Multiple possible path formats
**Solution**: Try fallback paths in order (see `src/generation/router.py`)

### CORS Issues
**Problem**: Frontend can't reach backend in dev
**Solution**: Configure CORS in `main.py` and Vite proxy in `vite.config.js`

## Recent Features

### History Tab Feature (2026-02-16)
**Implementation**: User-specific lesson plan history with viewing and copying functionality
- **Layout**: List view (table-like rows) instead of card grid
- **Features**: Color-coded subject badges (green=#10b981 for English, orange=#f97316 for Math), hover effects
- **UI**: Shows grade, lesson type, lesson number, and date - metadata (cost/tokens) removed from list view
- **Modal Rendering**: View modal uses `.lesson-plan` CSS class (from index.css) for consistent formatting with generation view
  - Same HTML rendering as `App.jsx` generation display (lines 984-991)
  - Applies proper typography, headings, lists, and spacing from global `.lesson-plan` styles (lines 446-504 in index.css)
- See [history-feature.md](history-feature.md) for full implementation details
- See [list-layout-update.md](list-layout-update.md) for list layout pattern
- Backend: `GET /generate/history` with authentication
- Frontend: `History.jsx` component with responsive grid, modal viewer, clipboard copy
- Database: `list_lesson_plans_by_user()` method filters by `created_by_id`

### Book Type Selection for Mathematics (2026-02-15)
**Implementation**: Checkboxes to select which textbooks to use (Course Book, Activity Book, or both)
- See [book-type-selection-feature.md](book-type-selection-feature.md) for full details
- Frontend: Checkboxes in Mathematics form section (between Chapter/Unit and Course Book Pages)
- Backend: `book_types: ["CB", "AB"]` parameter filters textbook fetching
- Default: Both books selected (backward compatible)
- Validation: At least one book type must be selected

### History Tab (2026-02-15)
**Implementation**: User-specific lesson plan history with view/copy functionality

**Backend**:
- `GET /generate/history` - Returns user's lesson plans (filtered by `created_by_id`)
- `db.list_user_lesson_plans()` - Database query method for user-specific filtering

**Frontend**:
- `History.jsx` - Standalone component for history view
- Grid layout with metadata cards
- Modal view for full lesson plan content
- Copy to clipboard functionality
- Empty state handling

**Authorization**: Only authenticated users, filtered by user_id

**Database**: Uses existing `lesson_plans` table (no schema changes)

---

## Memory Update Protocol

**CRITICAL**: After completing any implementation task:
1. ✅ Update this MEMORY.md with new patterns discovered
2. ✅ Document database query patterns that proved efficient
3. ✅ Record UI/UX patterns for educational interfaces
4. ✅ Note performance optimizations applied
5. ✅ Create separate topic files for complex implementations

**What to save:**
- Database schema changes and migration patterns
- API endpoint patterns and best practices
- Frontend component patterns for educational UIs
- Performance optimization strategies
- Common bugs/issues and their solutions
- Integration patterns with external APIs

**What NOT to save:**
- One-off bug fixes (unless they reveal a pattern)
- Feature-specific implementation details (code is self-documenting)
- Experimental code that didn't make it to production

**Topic file suggestions:**
- `database-patterns.md` - Complex query patterns, schema evolutions
- `api-design.md` - Endpoint design patterns, error handling
- `ui-patterns.md` - Educational interface components, accessibility
- `debugging.md` - Common issues and troubleshooting steps

---
*Last updated: 2026-02-16*
