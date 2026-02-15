"""
Deep verification script to check if generated lesson plan content
actually matches the SOW and book page content
"""
import sys
import os
import re
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.generation.lesson_generator import generator
from src.models import LessonType
from src.generation.router import router
from src.models import Subject as SubjectEnum


def similarity_ratio(a, b):
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def extract_slos_from_html(html_content):
    """Extract SLOs from generated HTML"""
    slos = []
    # Find SLO section
    slo_match = re.search(r'<h2>SLO\(s\):.*?</h2>(.*?)<h2>', html_content, re.DOTALL | re.IGNORECASE)
    if slo_match:
        slo_section = slo_match.group(1)
        # Extract list items
        li_items = re.findall(r'<li>(.*?)</li>', slo_section, re.DOTALL)
        slos = [re.sub(r'<.*?>', '', item).strip() for item in li_items]
    return slos


def extract_vocabulary_from_html(html_content):
    """Extract vocabulary words mentioned in the lesson plan"""
    # Look for common vocabulary patterns
    vocab_words = set()

    # Look in resources, explanation, activities
    text = html_content.lower()

    # Common vocabulary indicators
    vocab_patterns = [
        r'vocabulary:?\s*([^<\.]+)',
        r'words?:?\s*([^<\.]+)',
        r'target words?:?\s*([^<\.]+)'
    ]

    for pattern in vocab_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            # Split by common separators
            words = re.split(r'[,;]', match)
            for word in words:
                clean_word = re.sub(r'[^a-z\s-]', '', word.strip())
                if clean_word and len(clean_word) > 2:
                    vocab_words.add(clean_word)

    return vocab_words


def extract_page_references(html_content):
    """Extract book page references from HTML"""
    pages = set()

    # Look for patterns like "LB pg.110", "AB pg.88", "pg 110-111"
    patterns = [
        r'(?:LB|AB|CB|WB|ORT)\s*(?:pg\.?|page)\s*(\d+)',
        r'pg\.?\s*(\d+)',
        r'page\s+(\d+)'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        pages.update(matches)

    return pages


def verify_content_alignment():
    """
    Verify that the generated lesson plan actually uses SOW and book content
    """
    print("=" * 80)
    print("DEEP CONTENT ALIGNMENT VERIFICATION")
    print("=" * 80)
    print()

    # Parameters for test
    grade = "Grade 2"
    subject = "English"
    lesson_type = LessonType.VOCABULARY
    lesson_number = 1

    print("Step 1: Retrieving SOW and Book Context")
    print("-" * 80)

    # Get the context that would be used for generation
    subject_enum = SubjectEnum(subject)
    context = router.retrieve_context(
        grade=grade,
        subject=subject_enum,
        lesson_type=lesson_type,
        page_start=lesson_number,
        page_end=lesson_number,
        topic=None
    )

    sow_context = context.get("sow_context", {})
    book_content = context.get("book_content", [])

    # Extract SOW data
    sow_slos = sow_context.get("student_learning_outcomes", [])
    sow_skills = sow_context.get("skills", [])
    sow_strategies = sow_context.get("learning_strategies", [])
    sow_lesson_title = sow_context.get("lesson_title", "")

    # Extract vocabulary from SOW
    sow_vocab = set()
    for lpt in sow_context.get("lesson_plan_types", []):
        content = lpt.get("content", "")
        # Look for vocabulary in SOW content
        vocab_match = re.search(r'Vocabulary:?\s*([^\n]+)', content, re.IGNORECASE)
        if vocab_match:
            vocab_text = vocab_match.group(1)
            words = re.split(r'[,;]', vocab_text)
            for word in words:
                clean_word = re.sub(r'[^a-z\s-]', '', word.strip().lower())
                if clean_word and len(clean_word) > 2:
                    sow_vocab.add(clean_word)

    # Extract book pages
    book_pages_provided = set()
    for book_entry in book_content:
        for page in book_entry.get("pages", []):
            book_pages_provided.add(str(page.get("page", "")))

    print(f"✓ SOW SLOs: {len(sow_slos)}")
    for i, slo in enumerate(sow_slos, 1):
        print(f"  {i}. {slo[:80]}...")
    print()
    print(f"✓ SOW Skills: {', '.join(sow_skills)}")
    print(f"✓ SOW Strategies: {', '.join(sow_strategies)}")
    print(f"✓ SOW Vocabulary: {', '.join(sorted(sow_vocab))}")
    print(f"✓ Book Pages Provided: {', '.join(sorted(book_pages_provided))}")
    print()

    print("Step 2: Generating Lesson Plan")
    print("-" * 80)

    result = generator.generate(
        grade=grade,
        subject=subject,
        lesson_type=lesson_type,
        page_start=lesson_number,
        page_end=lesson_number,
        topic=None,
        created_by_id=None,
        save_to_db=False
    )

    if not result.success:
        print(f"❌ Generation failed: {result.error}")
        return

    html_content = result.html_content

    print("✓ Lesson plan generated")
    print()

    print("Step 3: Extracting Content from Generated Lesson Plan")
    print("-" * 80)

    generated_slos = extract_slos_from_html(html_content)
    generated_vocab = extract_vocabulary_from_html(html_content)
    generated_pages = extract_page_references(html_content)

    print(f"✓ Generated SLOs: {len(generated_slos)}")
    for i, slo in enumerate(generated_slos, 1):
        print(f"  {i}. {slo[:80]}...")
    print()
    print(f"✓ Generated Vocabulary: {', '.join(sorted(generated_vocab))}")
    print(f"✓ Generated Page References: {', '.join(sorted(generated_pages))}")
    print()

    print("Step 4: Comparing SOW vs Generated Content")
    print("=" * 80)
    print()

    # Check 1: SLO Alignment
    print("CHECK 1: SLO Alignment")
    print("-" * 80)

    slo_matches = []
    for gen_slo in generated_slos:
        best_match = None
        best_ratio = 0
        for sow_slo in sow_slos:
            ratio = similarity_ratio(gen_slo, sow_slo)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = sow_slo

        slo_matches.append({
            "generated": gen_slo,
            "sow_match": best_match,
            "similarity": best_ratio
        })

    total_slo_similarity = sum(m["similarity"] for m in slo_matches) / len(slo_matches) if slo_matches else 0

    for match in slo_matches:
        status = "✅" if match["similarity"] >= 0.6 else "⚠️" if match["similarity"] >= 0.4 else "❌"
        print(f"{status} Generated: {match['generated'][:60]}...")
        print(f"   SOW Match: {match['sow_match'][:60] if match['sow_match'] else 'None'}...")
        print(f"   Similarity: {match['similarity']:.1%}")
        print()

    slo_pass = total_slo_similarity >= 0.6
    print(f"{'✅' if slo_pass else '❌'} Average SLO Similarity: {total_slo_similarity:.1%}")
    print(f"{'✅ PASS' if slo_pass else '❌ FAIL'} - SLOs {'are' if slo_pass else 'are NOT'} aligned with SOW")
    print()

    # Check 2: Vocabulary Alignment
    print("CHECK 2: Vocabulary Alignment")
    print("-" * 80)

    vocab_overlap = generated_vocab.intersection(sow_vocab)
    vocab_coverage = len(vocab_overlap) / len(sow_vocab) if sow_vocab else 0

    print(f"SOW Vocabulary ({len(sow_vocab)}): {', '.join(sorted(sow_vocab))}")
    print(f"Generated Vocabulary ({len(generated_vocab)}): {', '.join(sorted(generated_vocab))}")
    print(f"Overlap ({len(vocab_overlap)}): {', '.join(sorted(vocab_overlap))}")
    print()

    vocab_pass = vocab_coverage >= 0.5
    print(f"{'✅' if vocab_pass else '❌'} Vocabulary Coverage: {vocab_coverage:.1%}")
    print(f"{'✅ PASS' if vocab_pass else '❌ FAIL'} - Vocabulary {'is' if vocab_pass else 'is NOT'} aligned with SOW")
    print()

    # Check 3: Skills Alignment
    print("CHECK 3: Skills Alignment")
    print("-" * 80)

    html_lower = html_content.lower()
    skills_mentioned = []
    for skill in sow_skills:
        if skill.lower() in html_lower:
            skills_mentioned.append(skill)

    skills_coverage = len(skills_mentioned) / len(sow_skills) if sow_skills else 0

    print(f"SOW Skills: {', '.join(sow_skills)}")
    print(f"Skills Mentioned in LP: {', '.join(skills_mentioned)}")
    print()

    skills_pass = skills_coverage >= 0.6
    print(f"{'✅' if skills_pass else '❌'} Skills Coverage: {skills_coverage:.1%}")
    print(f"{'✅ PASS' if skills_pass else '❌ FAIL'} - Skills {'are' if skills_pass else 'are NOT'} aligned with SOW")
    print()

    # Check 4: Learning Strategies Alignment
    print("CHECK 4: Learning Strategies Alignment")
    print("-" * 80)

    strategies_mentioned = []
    for strategy in sow_strategies:
        if strategy.lower() in html_lower:
            strategies_mentioned.append(strategy)

    strategies_coverage = len(strategies_mentioned) / len(sow_strategies) if sow_strategies else 0

    print(f"SOW Strategies: {', '.join(sow_strategies)}")
    print(f"Strategies Mentioned in LP: {', '.join(strategies_mentioned)}")
    print()

    strategies_pass = strategies_coverage >= 0.5
    print(f"{'✅' if strategies_pass else '❌'} Strategies Coverage: {strategies_coverage:.1%}")
    print(f"{'✅ PASS' if strategies_pass else '❌ FAIL'} - Strategies {'are' if strategies_pass else 'are NOT'} aligned with SOW")
    print()

    # Check 5: Book Page References
    print("CHECK 5: Book Page References")
    print("-" * 80)

    pages_overlap = generated_pages.intersection(book_pages_provided)
    pages_coverage = len(pages_overlap) / len(book_pages_provided) if book_pages_provided else 0

    print(f"Book Pages Provided: {', '.join(sorted(book_pages_provided))}")
    print(f"Pages Referenced in LP: {', '.join(sorted(generated_pages))}")
    print(f"Overlap: {', '.join(sorted(pages_overlap))}")
    print()

    pages_pass = pages_coverage >= 0.5
    print(f"{'✅' if pages_pass else '❌'} Page Reference Coverage: {pages_coverage:.1%}")
    print(f"{'✅ PASS' if pages_pass else '❌ FAIL'} - Page references {'are' if pages_pass else 'are NOT'} aligned")
    print()

    # Final Summary
    print("=" * 80)
    print("FINAL ALIGNMENT SCORE")
    print("=" * 80)
    print()

    all_checks = {
        "SLO Alignment": (slo_pass, total_slo_similarity),
        "Vocabulary Alignment": (vocab_pass, vocab_coverage),
        "Skills Alignment": (skills_pass, skills_coverage),
        "Strategies Alignment": (strategies_pass, strategies_coverage),
        "Page References": (pages_pass, pages_coverage)
    }

    for check_name, (passed, score) in all_checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}: {score:.1%}")

    total_passed = sum(1 for passed, _ in all_checks.values() if passed)
    total_checks = len(all_checks)

    print()
    print(f"Overall: {total_passed}/{total_checks} checks passed")
    print()

    if total_passed == total_checks:
        print("🎉 EXCELLENT - Lesson plan is fully aligned with SOW and book content!")
    elif total_passed >= total_checks * 0.8:
        print("✅ GOOD - Lesson plan is well-aligned with SOW and book content")
    elif total_passed >= total_checks * 0.6:
        print("⚠️  FAIR - Lesson plan has some alignment but needs improvement")
    else:
        print("❌ POOR - Lesson plan is not sufficiently aligned with SOW and book content")

    print()
    print("=" * 80)


if __name__ == "__main__":
    verify_content_alignment()
