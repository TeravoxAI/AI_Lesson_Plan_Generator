# Task Completion Checklist

When completing any coding task in this project:

1. **If prompts were changed** (`src/prompts/templates.py`):
   - Run `python3 verify_prompts.py` to validate prompt engineering requirements
   - Check the Art system prompt mandatory rules are still intact if Art was touched

2. **If generation logic changed** (`src/generation/`):
   - Run `python3 test_generation.py` to smoke-test English generation (requires DB connection + env vars)
   - Check `LessonGenerator._get_system_prompt()` dispatches correctly for all subjects

3. **If DB schema changed**:
   - Update `MIGRATION_NEEDED.md` with the migration SQL
   - Update `src/db/client.py` methods accordingly

4. **If a new subject or lesson type was added**:
   - `src/models.py` → add to `LessonType` or `Subject` enum
   - `src/prompts/templates.py` → add system prompt and/or type prompt
   - `src/generation/book_selector.py` → add book selection logic
   - `src/generation/lesson_generator.py` → add `generate_*()` method
   - `src/generation/router.py` → add `retrieve_*_context()` method
   - `routers/generate.py` → add dispatch branch
   - `frontend/src/App.jsx` → add to UI

5. **Always commit** with a clear message summarising what changed and why.
   - The graphify hook runs automatically on commit and rebuilds the knowledge graph.

6. **Grade format reminder**: SOW queries use `"Grade 2"`, textbook queries use `"2"`. Always use `normalize_grade()` when switching between them.
