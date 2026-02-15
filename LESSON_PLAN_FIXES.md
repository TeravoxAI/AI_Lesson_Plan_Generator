# English Lesson Plan Generation System - Critical Fixes Applied

## Date: 2026-02-14

## Problems Identified and Fixed

### 1. ✅ SOW Alignment Issue
**Problem:** Lesson plans had nothing related to the SOW (Scheme of Work)

**Solution:**
- Updated `LESSON_ARCHITECT_PROMPT` to include explicit "CRITICAL REQUIREMENT - SOW ALIGNMENT" section
- Added mandatory instruction: "You MUST strictly follow the SOW data provided"
- Emphasized that SOW is the authoritative source, not independent generation
- Updated `ENG_SYSTEM_PROMPT` with ⚠️ warnings about SOW alignment requirements
- Added rule: "DO NOT create content independently - extract and adapt from SOW"

### 2. ✅ SLO Development with Bloom's Taxonomy
**Problem:** SLOs were NOT developed according to SOW and Bloom's taxonomy

**Solution:**
- Added explicit Bloom's Taxonomy guidance in both prompts:
  - Remember: recall, recognize, identify, list, name, define
  - Understand: explain, describe, summarize, classify, compare, interpret
  - Apply: demonstrate, use, implement, solve, apply, execute
  - Analyze: analyze, compare, contrast, distinguish, examine, categorize
  - Evaluate: evaluate, judge, critique, assess, justify, argue
  - Create: create, design, compose, construct, produce, formulate
- Mandated: "SLOs MUST come DIRECTLY from SOW's 'student_learning_outcomes'"
- Required: "SLOs MUST use Bloom's Taxonomy action verbs at appropriate levels"
- Added instruction to ensure cognitive level progression from lower to higher-order thinking

### 3. ✅ Differentiated Instruction & Extension Activities
**Problem:** Differentiated instructions and extension activities were NOT in the lesson plan according to SOW

**Solution:**
- **Added NEW section in HTML output format:**
  ```html
  <h2>Differentiated Instruction:</h2>
  <p><strong>Struggling Learners:</strong> [Scaffolded support strategy]</p>
  <p><strong>On-Level Learners:</strong> [Standard approach from SOW]</p>
  <p><strong>Advanced Learners:</strong> [Challenge/extension]</p>
  ```
- **Added NEW section:**
  ```html
  <h2>Extension Activity:</h2>
  <p>[For advanced learners - based on SOW content]</p>
  ```
- Updated all lesson-type-specific prompts to include differentiation guidance:
  - Vocabulary: Picture support for struggling; challenge words for advanced
  - Reading Comprehension: Simpler questions for struggling; deeper analysis for advanced
  - Grammar: Simplified rules with visual support; complex sentences for advanced
  - Listening: Visual supports; complex inference questions for advanced
  - Oral/Speaking: Sentence frames; open-ended prompts for advanced
  - Reading: Guided reading groups by level; challenge texts for advanced
  - Recall: Visual cues; application questions for advanced
  - Creative Writing: Sentence frames/word banks; complex vocabulary/varied structures

### 4. ✅ AFL (Assessment for Learning) Strategies
**Problem:** Incorrect/wrong AFL strategies were mentioned (often just "observation")

**Solution:**
- Added explicit list of VALID AFL techniques in `ENG_SYSTEM_PROMPT`:
  - ✓ VALID: exit tickets, think-pair-share, thumbs up/down, traffic lights, mini-whiteboards, peer assessment, self-assessment, questioning techniques, learning journals
  - ✗ INVALID: generic "observation" without specificity
- Updated `LESSON_ARCHITECT_PROMPT` with detailed AFL options:
  - Exit tickets / entrance slips
  - Think-pair-share
  - Thumbs up/down or traffic lights
  - Mini-whiteboards / response cards
  - Peer assessment / self-assessment
  - Strategic questioning (higher-order questions)
  - Learning journals / reflection prompts
- Added lesson-type-specific AFL guidance:
  - Vocabulary: Mini-whiteboards, thumbs up/down
  - Reading Comprehension: Exit tickets, think-pair-share, peer retelling
  - Grammar: Mini-whiteboards for corrections, peer assessment
  - Listening: Thumbs up/down during listening, exit tickets
  - Oral/Speaking: Peer assessment with rubrics, self-reflection
  - Reading: Running records, oral reading fluency checks, comprehension probes
  - Recall: Traffic lights (red/yellow/green), entrance slips

### 5. ✅ Homework Constraint for Creative Writing
**Problem:** Creative writing shouldn't be given as homework

**Solution:**
- Added explicit constraint in `ENG_SYSTEM_PROMPT`:
  - "⚠️ HOMEWORK CONSTRAINT: NEVER assign creative writing as homework. Creative writing MUST be done in class with teacher support."
  - "Homework can include: reading, vocabulary practice, grammar exercises, comprehension questions."
- Updated creative writing lesson type prompt:
  - "Include brainstorming and planning stages IN CLASS"
  - "Include peer review/sharing component IN CLASS"
  - "REMINDER: Creative writing MUST be done in class - NEVER assign as homework"
- Added to mandatory rules: "Homework MUST NOT include creative writing"

## SOW Data Structure Understanding

The system retrieves the following SOW data for lesson generation:

```python
{
    "student_learning_outcomes": [list of SLOs],
    "learning_strategies": [list of teaching strategies],
    "skills": [list of skills like reading, writing, speaking, listening],
    "external_resources": [
        {
            "title": "Resource title",
            "type": "video" or "audio",
            "reference": "URL or track number"
        }
    ],
    "content": "Detailed lesson content and activities",
    "book_references": [
        {
            "book_type": "LB" or "AB" or "ORT",
            "book_name": "Book title",
            "pages": [list of page numbers]
        }
    ]
}
```

## Key Changes in Template Files

### File: `/home/omen-097/Teravox/LessonPlan_Generator/src/prompts/templates.py`

#### Changes Made:
1. **LESSON_ARCHITECT_PROMPT** - Added SOW alignment requirements and Bloom's taxonomy guidance
2. **ENG_SYSTEM_PROMPT** - Complete rewrite with:
   - SOW alignment warnings
   - Bloom's taxonomy requirements
   - AFL strategy specifications
   - Differentiated instruction section
   - Extension activity section
   - Homework constraint for creative writing
   - Updated HTML output format

3. **LESSON_TYPE_PROMPTS** - Updated all English lesson types:
   - recall
   - vocabulary
   - listening
   - reading
   - reading_comprehension
   - grammar
   - oral_speaking
   - creative_writing

## Testing Recommendations

To verify these fixes work correctly:

1. **Test SOW Alignment**: Generate a lesson plan and verify:
   - SLOs match SOW's student_learning_outcomes
   - Skills match SOW's skills field
   - Activities reference SOW content
   - Strategies follow SOW's learning_strategies

2. **Test Bloom's Taxonomy**: Check that SLOs use appropriate action verbs:
   - Lower-order: identify, list, recall, recognize
   - Mid-order: explain, demonstrate, apply, analyze
   - Higher-order: evaluate, create, design

3. **Test Differentiation**: Verify lesson plans include:
   - Differentiated Instruction section with 3 levels
   - Extension Activity section for advanced learners

4. **Test AFL Strategies**: Confirm AFL section uses specific techniques:
   - NOT just "observation"
   - Valid techniques like exit tickets, think-pair-share, mini-whiteboards

5. **Test Homework Constraint**: Verify that creative writing lessons:
   - Do NOT assign creative writing as homework
   - Include acceptable homework alternatives (reading, vocabulary, grammar)

## Implementation Notes

- These changes are backward compatible - existing lesson plan generation will work
- The HTML output format is extended with 2 new sections but preserves all existing sections
- SOW data flow through the system remains unchanged
- The fixes are enforced through prompt engineering, not code changes
- All prompts maintain the "concise, bullet-point" style requirement

## Author Notes

These fixes address the fundamental pedagogical requirements for Pakistani educational contexts:
- Strict curriculum alignment (SOW adherence)
- Cognitive development through Bloom's taxonomy
- Inclusive teaching through differentiation
- Formative assessment through proper AFL
- Age-appropriate learning (no creative writing homework for young learners)

The prompts now act as strict guardrails to ensure lesson plans meet professional teaching standards.
