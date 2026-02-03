#!/usr/bin/env python3
"""Quick script to check what SOW entries exist in the database"""

from src.db.client import db

print("Checking SOW entries in database...\n")

# Get all SOW entries
result = db.client.table("sow_entries").select("id, subject, grade_level, created_at").execute()

if not result.data:
    print("❌ No SOW entries found in database!")
else:
    print(f"✅ Found {len(result.data)} SOW entries:\n")

    # Group by subject and grade
    by_subject = {}
    for entry in result.data:
        subject = entry.get('subject', 'Unknown')
        grade = entry.get('grade_level', 'Unknown')
        key = f"{subject} - {grade}"
        if key not in by_subject:
            by_subject[key] = []
        by_subject[key].append(entry['id'])

    for key, ids in sorted(by_subject.items()):
        print(f"  📚 {key}: {len(ids)} entries (IDs: {ids[:3]}{'...' if len(ids) > 3 else ''})")

print("\n" + "="*60)
print("Now checking for Grade 2 English specifically...")

# Check for English Grade 2 with various formats
test_queries = [
    ("English", "Grade 2"),
    ("english", "Grade 2"),
    ("English", "grade 2"),
    ("english", "grade 2"),
    ("English", "2"),
]

for subject, grade in test_queries:
    result = db.client.table("sow_entries").select("id").eq("subject", subject).eq("grade_level", grade).execute()
    count = len(result.data or [])
    print(f"  Query: subject='{subject}', grade_level='{grade}' → {count} results")
