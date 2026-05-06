# Suggested Commands

## Run Both Servers (recommended)
```bash
cd /home/taha/APS/AI_Lesson_Plan_Generator
./dev.sh
# Backend: http://localhost:8000  Frontend: http://localhost:3000
# Ctrl+C stops both
```

## Backend Only
```bash
source /home/taha/APS/.venv/bin/activate
cd /home/taha/APS/AI_Lesson_Plan_Generator
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend Only
```bash
cd /home/taha/APS/AI_Lesson_Plan_Generator/frontend
npm run dev        # dev server on port 3000
npm run build      # production build → frontend/dist/
npm run preview    # preview production build
```

## Virtual Environment
```bash
source /home/taha/APS/.venv/bin/activate   # shared APS venv
# Note: no local venv/ in project dir — venv is one level up at /home/taha/APS/.venv
```

## Utility / Debug Scripts
```bash
python3 check_sow.py               # inspect SOW entries in DB
python3 test_generation.py         # test English lesson plan generation
python3 verify_prompts.py          # verify prompt engineering requirements
python3 verify_content_alignment.py # verify SOW content alignment
```

## Linting / Formatting
No linting or formatting config present in the project (no ruff/flake8/black config).
No test runner configured (pytest not in requirements).

## Git
```bash
git log --oneline -5
git diff
git add <file> && git commit -m "message"
# Note: graphify hook auto-rebuilds graph on commit
```

## Vercel Deployment
Entry point: `api/index.py` (imports `main:app`)
Frontend served from `frontend/dist/` at `/app`
