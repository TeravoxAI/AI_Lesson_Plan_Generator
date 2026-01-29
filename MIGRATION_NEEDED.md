# Database Migration Required

## Quick Fix

Run this **ONE command** in your **Supabase SQL Editor**:

```sql
ALTER TABLE lesson_plans ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
```

That's it! This will fix the error you're seeing.

## What This Does

Adds a `metadata` column to store usage metrics as JSON:
- Generation time
- Cost
- Token counts

## Why This Approach?

Instead of adding 5 separate columns (`generation_time`, `cost`, `input_tokens`, `output_tokens`, `total_tokens`), we use a single flexible JSON column. This is:
- ✅ Cleaner
- ✅ More flexible for future metrics
- ✅ Easier to maintain

## Optional: Add Index

For better performance when querying metadata:

```sql
CREATE INDEX IF NOT EXISTS idx_lesson_plans_metadata ON lesson_plans USING GIN(metadata);
```

## Full Migration Script

If you want to run the complete migration with comments:

```bash
# View the full migration
cat src/db/migrations/add_metadata_column.sql

# Or use the helper script
python3 scripts/run_migration.py
```

## Metadata Structure

After the migration, usage metrics are stored like this:

```json
{
  "generation_time": 3.45,
  "cost": 0.002341,
  "input_tokens": 1234,
  "output_tokens": 567,
  "total_tokens": 1801
}
```

## Querying Metadata

Example queries:

```sql
-- Get plans with cost > $0.01
SELECT * FROM lesson_plans
WHERE (metadata->>'cost')::float > 0.01;

-- Average generation time
SELECT AVG((metadata->>'generation_time')::float)
FROM lesson_plans
WHERE metadata->>'generation_time' IS NOT NULL;

-- Total cost
SELECT SUM((metadata->>'cost')::float)
FROM lesson_plans;
```

## After Migration

Restart your server and test:
```bash
uvicorn main:app --reload
```

The usage metrics will now be saved and displayed in the frontend!
