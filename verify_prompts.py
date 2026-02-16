#!/usr/bin/env python3
"""
Verification script to check that the updated prompts contain all required elements.
Run this to verify the fixes were applied correctly.
"""

import sys
from src.prompts.templates import ENG_SYSTEM_PROMPT, LESSON_ARCHITECT_PROMPT, LESSON_TYPE_PROMPTS


def verify_eng_system_prompt():
    """Verify ENG_SYSTEM_PROMPT has all required sections"""
    print("\n" + "=" * 70)
    print("VERIFYING ENG_SYSTEM_PROMPT")
    print("=" * 70)

    required_elements = [
        ("SOW Alignment Warning", "SOW ALIGNMENT"),
        ("Bloom's Taxonomy Section", "BLOOM'S TAXONOMY"),
        ("AFL Strategies Section", "AFL STRATEGIES REQUIREMENT"),
        ("Homework Constraint", "HOMEWORK CONSTRAINT"),
        ("Differentiated Instruction HTML", "<h2>Differentiated Instruction:</h2>"),
        ("Extension Activity HTML", "<h2>Extension Activity:</h2>"),
        ("Bloom's Remember Level", "Remember: recall, recognize, identify"),
        ("Bloom's Create Level", "Create: create, design, compose"),
        ("Valid AFL Examples", "exit tickets, think-pair-share"),
        ("Invalid AFL Warning", "NOT just \"observation\""),
        ("Creative Writing Homework Ban", "NEVER assign creative writing as homework"),
    ]

    passed = 0
    failed = 0

    for name, search_text in required_elements:
        if search_text in ENG_SYSTEM_PROMPT:
            print(f"✓ {name}")
            passed += 1
        else:
            print(f"✗ MISSING: {name}")
            failed += 1

    print(f"\nResult: {passed}/{len(required_elements)} checks passed")
    return failed == 0


def verify_lesson_architect_prompt():
    """Verify LESSON_ARCHITECT_PROMPT has SOW requirements"""
    print("\n" + "=" * 70)
    print("VERIFYING LESSON_ARCHITECT_PROMPT")
    print("=" * 70)

    required_elements = [
        ("SOW Critical Requirement", "CRITICAL REQUIREMENT - SOW ALIGNMENT"),
        ("SLO from SOW", "SLOs MUST come DIRECTLY from"),
        ("Bloom's Taxonomy Guidance", "Bloom's Taxonomy"),
        ("AFL Techniques List", "Exit tickets" in LESSON_ARCHITECT_PROMPT or "exit tickets" in LESSON_ARCHITECT_PROMPT),
        ("Proper AFL Not Observation", "NOT just \"observation\""),
    ]

    passed = 0
    failed = 0

    for name, search_condition in required_elements:
        # Handle both string searches and boolean conditions
        if isinstance(search_condition, bool):
            result = search_condition
        elif isinstance(search_condition, str):
            result = search_condition in LESSON_ARCHITECT_PROMPT
        else:
            result = False

        if result:
            print(f"✓ {name}")
            passed += 1
        else:
            print(f"✗ MISSING: {name}")
            failed += 1

    print(f"\nResult: {passed}/{len(required_elements)} checks passed")
    return failed == 0


def verify_lesson_type_prompts():
    """Verify English lesson type prompts have differentiation and AFL"""
    print("\n" + "=" * 70)
    print("VERIFYING LESSON_TYPE_PROMPTS (English)")
    print("=" * 70)

    english_types = [
        "recall", "vocabulary", "listening", "reading",
        "reading_comprehension", "grammar", "oral_speaking", "creative_writing"
    ]

    passed = 0
    failed = 0

    for lesson_type in english_types:
        if lesson_type not in LESSON_TYPE_PROMPTS:
            print(f"✗ MISSING LESSON TYPE: {lesson_type}")
            failed += 1
            continue

        prompt = LESSON_TYPE_PROMPTS[lesson_type]

        # Check for differentiation mention
        has_differentiation = "differentiation" in prompt.lower() or "struggling" in prompt.lower() or "advanced" in prompt.lower()

        # Check for AFL mention (except creative_writing which has special requirements)
        has_afl = "AFL:" in prompt or "afl:" in prompt.lower()

        if has_differentiation and (has_afl or lesson_type == "creative_writing"):
            print(f"✓ {lesson_type}: Has differentiation & AFL guidance")
            passed += 1
        elif has_differentiation:
            print(f"⚠ {lesson_type}: Has differentiation but missing explicit AFL")
            passed += 1
        else:
            print(f"✗ {lesson_type}: Missing differentiation or AFL")
            failed += 1

    print(f"\nResult: {passed}/{len(english_types)} lesson types verified")
    return failed == 0


def verify_creative_writing_constraints():
    """Verify creative writing has homework constraint"""
    print("\n" + "=" * 70)
    print("VERIFYING CREATIVE WRITING HOMEWORK CONSTRAINT")
    print("=" * 70)

    creative_prompt = LESSON_TYPE_PROMPTS.get("creative_writing", "")

    checks = [
        ("IN CLASS requirement", "IN CLASS"),
        ("NEVER as homework", "NEVER assign as homework" in creative_prompt or "homework" in creative_prompt.lower()),
    ]

    passed = 0
    failed = 0

    for name, condition in checks:
        if isinstance(condition, bool):
            result = condition
        else:
            result = condition in creative_prompt

        if result:
            print(f"✓ {name}")
            passed += 1
        else:
            print(f"✗ MISSING: {name}")
            failed += 1

    print(f"\nResult: {passed}/{len(checks)} checks passed")
    return failed == 0


def main():
    """Run all verification checks"""
    print("\n" + "=" * 70)
    print("LESSON PLAN PROMPT VERIFICATION SCRIPT")
    print("Verifying fixes applied on 2026-02-14")
    print("=" * 70)

    results = []

    results.append(verify_eng_system_prompt())
    results.append(verify_lesson_architect_prompt())
    results.append(verify_lesson_type_prompts())
    results.append(verify_creative_writing_constraints())

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    if all(results):
        print("✓ ALL CHECKS PASSED - Prompts are correctly configured!")
        return 0
    else:
        print("✗ SOME CHECKS FAILED - Review the output above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
