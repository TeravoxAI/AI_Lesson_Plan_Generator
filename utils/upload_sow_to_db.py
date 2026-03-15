"""
Upload a extracted SOW JSON file into the sow_entries table.

Usage:
    python utils/upload_sow_to_db.py \
        --file Demo_docs/sow_comp.json \
        --grade "Grade 2" \
        --subject "Computer Studies" \
        --term "Full Year" \
        --title "Computer Studies Grade 2 SOW"
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.client import db


def main():
    parser = argparse.ArgumentParser(description="Upload SOW JSON to sow_entries table")
    parser.add_argument("--file",    required=True, help="Path to the extracted SOW JSON file")
    parser.add_argument("--grade",   required=True, help='Grade level e.g. "Grade 2"')
    parser.add_argument("--subject", required=True, help='Subject e.g. "Computer Studies"')
    parser.add_argument("--term",    required=True, help='Term e.g. "Full Year" or "Term 1"')
    parser.add_argument("--title",   required=True, help="Human-readable title for this SOW entry")
    args = parser.parse_args()

    if not db.is_connected():
        print("❌ Database not connected. Check SUPABASE_PROJECT_URL and SUPABASE_ANON_KEY in .env")
        sys.exit(1)

    with open(args.file, "r", encoding="utf-8") as f:
        extraction = json.load(f)

    units = extraction.get("curriculum", {}).get("units", [])
    total_lessons = sum(len(u.get("lessons", [])) for u in units)
    print(f"📄 Loaded: {len(units)} unit(s), {total_lessons} lesson(s)")

    sow_id = db.insert_sow_entry(
        grade_level=args.grade,
        subject=args.subject,
        term=args.term,
        title=args.title,
        extraction=extraction,
    )

    if sow_id:
        print(f"✅ Inserted SOW entry with id={sow_id}")
    else:
        print("❌ Insert failed — no ID returned")
        sys.exit(1)


if __name__ == "__main__":
    main()
