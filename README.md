# Lesson Plan Generator

AI-powered curriculum-aware lesson plan generation system that creates structured lesson plans based on textbooks and Scheme of Work (SOW) documents.

## Features

- 📚 **Curriculum-Aware**: Generates lesson plans aligned with SOW curriculum guidelines
- 🎯 **Multi-Type Lessons**: Supports various lesson types (recall, vocabulary, listening, speaking, writing, reading)
- 📖 **Textbook Integration**: OCR-based textbook content extraction and referencing
- 🎥 **Teacher Resources**: Embedded YouTube videos and audio tracks from curriculum materials
- 💰 **Usage Tracking**: Tracks generation cost, time, and token usage
- 🎨 **Modern UI**: Clean, responsive interface built with React

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL database (Supabase recommended)
- OpenRouter API key for LLM access

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd LessonPlan_Generator
```

### 2. Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the root directory:

```bash
# Database (Supabase)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# LLM Configuration
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-4o

# Optional: Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 4. Database Setup

Run the database migration to create required tables:

```sql
-- Run this in your Supabase SQL Editor or PostgreSQL client
-- See src/db/schema.sql for the complete schema

-- Quick fix to add metadata column if upgrading from older version:
ALTER TABLE lesson_plans ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
CREATE INDEX IF NOT EXISTS idx_lesson_plans_metadata ON lesson_plans USING GIN(metadata);
```

### 5. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 6. Audio Tracks Setup (REQUIRED)

**IMPORTANT**: You must have audio track folders for audio playback to work.

Create audio track folders in the project root with this naming pattern:
```
Grade_{grade_number}_{subject}_Tracks/
```

Example structure:
```
LessonPlan_Generator/
├── Grade_2_English_Tracks/
│   ├── GE2_Track_01.mp3
│   ├── GE2_Track_02.mp3
│   └── GE2_Track_70.mp3
├── Grade_3_English_Tracks/
│   ├── GE3_Track_01.mp3
│   └── ...
└── ...
```

**File naming convention**: `GE{grade}_Track_{number}.mp3`

Example:
- Grade 2, Track 70 → `GE2_Track_70.mp3`
- Grade 3, Track 15 → `GE3_Track_15.mp3`

> **Note**: Without these audio folders, audio playback features will not work, but lesson plan generation will still function normally.

## Running the Application

### Start Backend Server

```bash
# From project root
source venv/bin/activate  # Activate virtual environment
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

### Start Frontend Development Server

```bash
# In a new terminal
cd frontend
npm run dev
```

Frontend will be available at: `http://localhost:3000`

## Usage

### 1. Upload Documents

**Upload Textbooks:**
1. Go to "Upload" tab
2. Select "Textbook" type
3. Fill in grade, subject, book type (Learner's Book, Activity Book, etc.)
4. Upload PDF file
5. Wait for OCR processing

**Upload Scheme of Work (SOW):**
1. Go to "Upload" tab
2. Select "Scheme of Work" type
3. Fill in grade and subject
4. Upload Word document (.docx)
5. Wait for processing

### 2. Generate Lesson Plans

1. Go to "Generate" tab
2. Select:
   - Grade level
   - Subject
   - Lesson number
   - Lesson type(s) (can select multiple)
3. Click "Generate Lesson Plan"
4. View generated lesson plan with:
   - Teacher resources (videos and audio)
   - Learning objectives
   - Activities and assessments
   - Usage metrics (cost, time, tokens)

### 3. Download & Copy

- **Download**: Export lesson plan as HTML file
- **Copy**: Copy lesson plan HTML to clipboard

## Project Structure

```
AI_Lesson_Plan_Generator/
├── docs/                 # Documentation files
├── frontend/             # React/Vite frontend application
│   ├── src/              # Frontend source code
│   ├── public/           # Static assets
│   └── vite.config.js    # Vite configuration
├── routers/              # API Route definitions
│   ├── authentication.py # Auth endpoints
│   ├── authorization.py  # RBAC logic
│   ├── generate.py       # Lesson generation endpoints
│   └── ingest.py         # Content ingestion endpoints
├── src/                  # Core application logic
│   ├── db/               # Database client and schema
│   ├── generation/       # Lesson generation logic (LLM)
│   ├── ingestion/        # Document processing logic
│   ├── prompts/          # LLM system prompts
│   ├── config.py         # Configuration settings
│   └── models.py         # Pydantic data models
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

## API Endpoints

### Generate
- `POST /generate/lesson-plan` - Generate a lesson plan
- `GET /generate/lesson-types` - Get available lesson types
- `GET /generate/lesson-types/{subject}` - Get lesson types for subject

### Ingest
- `POST /ingest/textbook` - Upload textbook PDF
- `POST /ingest/sow` - Upload SOW document
- `GET /ingest/books` - List uploaded textbooks
- `GET /ingest/sow` - List SOW entries

### Media
- `GET /audio/{grade}/{subject}/{track_number}` - Stream audio track

### Health
- `GET /health` - Health check endpoint

## How It Works

### Lesson Generation Flow

1. **Context Retrieval**:
   - Fetches SOW curriculum data for the specified lesson number
   - Extracts relevant textbook pages based on SOW references
   - Identifies external resources (videos, audio tracks)

2. **Prompt Construction**:
   - Combines SOW guidelines, textbook content, and lesson type requirements
   - Uses subject-specific system prompts (Math vs English)

3. **LLM Generation**:
   - Sends prompt to OpenRouter LLM (GPT-4, Claude, etc.)
   - Generates structured HTML lesson plan

4. **Resource Processing**:
   - Extracts YouTube video IDs for embedding
   - Constructs audio track URLs from local files
   - Returns teacher resources alongside lesson plan

5. **Storage**:
   - Saves lesson plan to database
   - Tracks usage metrics (cost, tokens, time)

## Grade Normalization

The system handles different grade formats:
- **SOW Database**: `"Grade 2"`
- **Textbook Database**: `"2"`
- **Router**: Automatically normalizes for correct lookups

## Troubleshooting

### Audio Not Playing
- ✅ Ensure audio track folders exist with correct naming
- ✅ Restart Vite dev server after adding `/audio` proxy
- ✅ Check browser console for 404 errors
- ✅ Verify track numbers match file names

### No SOW Context Found
- Check grade format matches database (`"Grade 2"` in SOW table)
- Verify lesson number exists in uploaded SOW
- Check lesson type matching (e.g., "listening" matches "listening_audio_video")

### No Book Content Found
- Upload textbook PDFs first
- Check book type tags (LB, AB, ORT, TR) match SOW references
- Verify page numbers are within uploaded textbook range

### Database Errors
- Run database migration script (see `MIGRATION_NEEDED.md`)
- Check Supabase connection in `.env`
- Verify tables exist: `textbooks`, `sow_entries`, `lesson_plans`

## Development

### Adding New Lesson Types

1. Add to `src/models.py` → `LessonType` enum
2. Create prompt template in `src/prompts/templates.py`
3. Update frontend lesson type selection

### Adding Audio for New Grades

1. Create folder: `Grade_{number}_{subject}_Tracks/`
2. Add MP3 files with naming: `GE{grade}_Track_{number}.mp3`
3. Update SOW to reference tracks

## Production Deployment

### Build Frontend

```bash
cd frontend
npm run build
cd ..
```

Built files will be in `frontend/dist/` and served at `/app` by FastAPI.

### Run Production Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Environment Variables

Update production `.env`:
- Set secure database credentials
- Use production OpenRouter API key
- Configure CORS origins in `main.py`

## Cost Management

Generation costs are tracked per lesson plan:
- View cost in frontend after generation
- Query total costs:
  ```sql
  SELECT SUM((metadata->>'cost')::float) FROM lesson_plans;
  ```
- Average generation time:
  ```sql
  SELECT AVG((metadata->>'generation_time')::float) FROM lesson_plans;
  ```

## License

[Add your license here]

## Support

For issues and questions, please open an issue in the repository.
