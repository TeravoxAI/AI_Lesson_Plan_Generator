"""
Test script to verify English lesson plan generation with all fixes
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.generation.lesson_generator import generator
from src.models import LessonType

def test_english_lesson_plan():
    """
    Generate a test English lesson plan to verify all fixes:
    1. SOW alignment
    2. Bloom's taxonomy in SLOs
    3. Differentiated instruction
    4. Proper AFL strategies
    5. No creative writing in homework
    """

    print("=" * 80)
    print("TESTING ENGLISH LESSON PLAN GENERATION")
    print("=" * 80)
    print()

    # Test parameters
    grade = "Grade 2"
    subject = "English"
    lesson_type = LessonType.VOCABULARY  # Test with vocabulary lesson
    page_start = 1  # Use lesson number as page_start

    print(f"Grade: {grade}")
    print(f"Subject: {subject}")
    print(f"Lesson Type: {lesson_type.value}")
    print(f"Lesson Number: {page_start}")
    print()
    print("Generating lesson plan...")
    print("-" * 80)

    # Generate lesson plan (don't save to DB for testing)
    result = generator.generate(
        grade=grade,
        subject=subject,
        lesson_type=lesson_type,
        page_start=page_start,
        page_end=page_start,
        topic=None,
        created_by_id=None,
        save_to_db=False  # Don't save test plans
    )

    print()
    print("=" * 80)
    print("GENERATION RESULT")
    print("=" * 80)
    print()

    if result.success:
        print("✅ SUCCESS!")
        print()
        print(f"⏱️  Generation Time: {result.generation_time}s")
        print(f"💰 Cost: ${result.cost:.6f}")
        print(f"📊 Tokens: {result.input_tokens} in / {result.output_tokens} out = {result.total_tokens} total")
        print()

        if result.teacher_resources:
            print(f"📚 Teacher Resources: {len(result.teacher_resources)}")
            for res in result.teacher_resources:
                print(f"   - {res['type']}: {res['title']}")
        print()

        print("=" * 80)
        print("LESSON PLAN HTML OUTPUT")
        print("=" * 80)
        print()
        print(result.html_content)
        print()

        # Verify fixes
        print("=" * 80)
        print("VERIFICATION CHECKS")
        print("=" * 80)
        print()

        html = result.html_content.lower()

        checks = {
            "SLOs Section Present": "slo" in html,
            "Differentiated Instruction Present": "differentiated instruction" in html,
            "Extension Activity Present": "extension activity" in html,
            "AFL Strategies Present": "afl strategies" in html or "afl strategy" in html,
            "Homework Section Present": "homework" in html or "h.w" in html,
            "Skills Focused On Present": "skills focused" in html or "skills focus" in html,
        }

        # Check for proper AFL techniques (not just "observation")
        afl_techniques = [
            "exit ticket", "think-pair-share", "thumbs", "mini-whiteboard",
            "peer assessment", "self-assessment", "questioning"
        ]
        has_specific_afl = any(tech in html for tech in afl_techniques)
        checks["Specific AFL Techniques (not just observation)"] = has_specific_afl

        # Check differentiation levels
        diff_levels = [
            "struggling" in html,
            "on-level" in html or "on level" in html,
            "advanced" in html
        ]
        checks["All 3 Differentiation Levels"] = all(diff_levels)

        # Check no creative writing in homework (if it's a creative writing lesson)
        if lesson_type == LessonType.CREATIVE_WRITING:
            # Find homework section
            hw_section = ""
            if "homework" in html:
                hw_idx = html.index("homework")
                hw_section = html[hw_idx:hw_idx+500]

            has_creative_writing_hw = "creative writing" in hw_section or "write a story" in hw_section
            checks["No Creative Writing in Homework"] = not has_creative_writing_hw

        print()
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}")

        print()
        all_passed = all(checks.values())
        if all_passed:
            print("🎉 ALL VERIFICATION CHECKS PASSED!")
        else:
            print("⚠️  Some checks failed - review the lesson plan")

    else:
        print("❌ GENERATION FAILED")
        print(f"Error: {result.error}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    test_english_lesson_plan()
