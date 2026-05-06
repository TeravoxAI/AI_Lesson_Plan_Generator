# Code Style and Conventions

## Python
- **Type hints**: Used on function signatures throughout (`Optional`, `Dict`, `List`, `Any` from `typing`)
- **Docstrings**: Short one-line docstrings on classes and public methods; multi-line for complex args
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants/prompts
- **Singletons**: `db = DatabaseClient()` in `src/db/client.py`, `router = ContextRouter()` in `src/generation/router.py`, `generator = LessonGenerator()` in `src/generation/lesson_generator.py`
- **Error handling**: Generators catch all exceptions, print traceback, return `GenerateResponse(success=False, error=str(e))`
- **No ORM**: Raw Supabase client queries via `src/db/client.py`
- **Enums**: `LessonType`, `Subject`, `BookType` are `str, Enum` for JSON serialisation

## Frontend (React)
- Functional components with hooks only (no class components)
- No TypeScript — plain `.jsx` / `.js`
- No separate CSS files per component — `index.css` only
- jsPDF used for PDF export (`pdfExport.js`)

## LLM Prompts (`src/prompts/templates.py`)
- All system prompts are module-level string constants
- Subject-specific prompts: `ENG_SYSTEM_PROMPT`, `MATHS_SYSTEM_PROMPT`, `ART_SYSTEM_PROMPT`, `CS_SYSTEM_PROMPT`, `ISLAMIAT_SYSTEM_PROMPT`, `NAZRA_SYSTEM_PROMPT`
- Base user prompt: `LESSON_ARCHITECT_PROMPT` (formatted with grade, subject, book_content, sow_strategy, etc.)
- When adding a new subject: add system prompt here, add to `LessonGenerator._get_system_prompt()`, add `Subject` enum value, add `LessonType` values if needed

## Adding a New Lesson Type (English)
1. `src/models.py` → `LessonType` enum
2. `src/prompts/templates.py` → `LESSON_TYPE_PROMPTS` dict
3. `src/generation/book_selector.py` → book selection logic
4. `frontend/src/App.jsx` → UI lesson type selector
