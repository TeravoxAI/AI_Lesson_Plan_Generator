# lesson-plan-architect - Agent Memory

## Project Context
AI Lesson Plan Generator for Pakistani students - Creates curriculum-aligned lesson plans using LLM based on SOW and textbook content.

## Pakistani Curriculum Context

### Supported Boards
- Punjab Board, Sindh Board, Federal Board (primary focus)
- Cambridge International (secondary)
- Edexcel, AKU-EB (less common)

### Grade Levels
Currently supporting elementary grades (Grade 1-8) with focus on:
- **English**: 8 lesson types across multiple textbooks
- **Mathematics**: 2 lesson types (concept, practice)

### Subject-Specific Workflows

**English Lesson Types:**
1. Recall
2. Vocabulary
3. Listening
4. Reading
5. Reading Comprehension
6. Grammar
7. Oral Speaking
8. Creative Writing

**Mathematics Lesson Types:**
1. Concept (introducing new mathematical ideas)
2. Practice (applying and reinforcing concepts)

## Pedagogical Framework Applied

### Bloom's Taxonomy Integration
All generated lesson plans scaffold across cognitive levels:
- **Remembering**: Recall vocabulary, facts, formulas
- **Understanding**: Explain concepts, summarize stories
- **Applying**: Solve problems, use grammar rules
- **Analyzing**: Compare/contrast, identify patterns
- **Evaluating**: Critique arguments, assess solutions
- **Creating**: Write stories, design projects

**Pattern**: Start with lower-order (remembering/understanding), progress to higher-order (analyzing/creating)

### Assessment for Learning (AfL) Strategies

Commonly embedded strategies:
- **Exit tickets**: Quick formative checks at lesson end
- **Think-pair-share**: Collaborative discussion protocol
- **Traffic light system**: Self-assessment of understanding
- **Mini-whiteboards**: Immediate feedback during practice
- **Peer assessment**: Students evaluate each other's work
- **Questioning**: Higher-order questions throughout

**Pattern**: At least 2-3 AfL strategies per lesson

### Differentiation Approaches

**Struggling Learners:**
- Simplified language and instructions
- Visual aids and concrete examples
- Peer buddy support
- Chunked tasks with frequent checks
- Scaffolded worksheets

**Average Learners:**
- Balanced support and challenge
- Collaborative activities
- Guided practice with gradual release

**Advanced Learners:**
- Extension activities and open-ended tasks
- Leadership roles (peer tutoring)
- Deeper inquiry questions
- Creative project options

**Pattern**: Explicit differentiation for at least 2 groups per lesson

## Lesson Plan Structure

### Standard Format (5-Part Lesson)
1. **Introduction/Warm-up** (5-10 min)
2. **Development** (15-20 min)
3. **Presentation** (10-15 min)
4. **Practice** (15-20 min)
5. **Evaluation/Closure** (5-10 min)

### Alternative: 5E Model
- Engage → Explore → Explain → Elaborate → Evaluate

**Pattern**: Time allocations based on 40-45 min class period (standard in Pakistan)

## LLM Prompt Engineering Patterns

### System Prompt Structure
```
Role: Master educator for Pakistani students
Context: Grade, subject, curriculum board
Task: Generate lesson plan for [topic]
Requirements: Bloom's taxonomy, AfL strategies, differentiation
Format: Structured sections with clear headings
Constraints: Age-appropriate, culturally relevant, resource-conscious
```

### Context Injection
1. **SOW Content**: Curriculum objectives and standards
2. **Textbook Pages**: Actual content from referenced books
3. **Resources**: Audio tracks, YouTube videos, activity materials

**Pattern**: More context = better alignment with curriculum

### Quality Criteria in Prompts
- Clear, measurable learning objectives (SMART)
- At least 3 Bloom's levels represented
- 2-3 AfL strategies embedded
- Differentiation for struggling/advanced learners
- Culturally responsive examples (Pakistani context)
- Realistic resource requirements

## Resource Constraints

### Common Classroom Realities
- Limited technology access (no 1:1 devices)
- Large class sizes (30-50 students)
- Basic supplies (paper, pencils, whiteboard)
- Shared textbooks in some schools
- Limited multimedia equipment

### Practical Solutions
- Use mini-whiteboards (low-cost alternative to tablets)
- Gallery walks instead of digital presentations
- Peer work to manage large classes
- Audio tracks (low-tech but effective for listening)
- Printable worksheets over digital activities

**Pattern**: Always provide low-resource alternatives

## Subject-Specific Patterns

### English Lessons
- **Vocabulary**: Pre-teach words, use in context, practice
- **Reading**: Pre-reading (predictions), during-reading (comprehension checks), post-reading (analysis)
- **Grammar**: Explicit instruction → guided practice → independent application
- **Writing**: Model → shared writing → guided → independent
- **Listening**: Pre-listening (activate prior knowledge) → while-listening (guided tasks) → post-listening (discussion)

### Mathematics Lessons
- **Concept**: Concrete → Pictorial → Abstract (CPA approach)
- **Practice**: Worked examples → guided practice → independent practice
- **Problem-solving**: Read → Plan → Solve → Check
- **Mental math**: Regular warm-ups and quick-fire questions

## Cultural Responsiveness

### Context Adaptation
- Use Pakistani names in examples (Ahmed, Fatima, Hassan, Ayesha)
- Reference local contexts (bazaar, masjid, Eid, cricket)
- Include Urdu/regional language code-switching where natural
- Respect Islamic values in content examples
- Consider regional diversity (urban/rural, linguistic)

### Inclusive Practices
- Gender-balanced examples and roles
- Diverse family structures
- Accessible language for English learners
- Sensitivity to economic diversity

## Common Lesson Plan Gaps (to probe for)

When requests are incomplete, ask about:
1. **Grade level** (critical for age-appropriateness)
2. **Curriculum board** (affects standards alignment)
3. **Class duration** (affects activity planning)
4. **Available resources** (tech, materials, space)
5. **Student diversity** (language levels, learning needs)
6. **Prior knowledge** (what students already know)
7. **Preferred lesson structure** (5-part, 5E, other)

## Effective Prompt Templates

### Basic Lesson Plan Prompt
```
Create a [duration]-minute lesson plan for Grade [X] [Subject] on [Topic].
- Board: [curriculum board]
- Learning objectives: [aligned to standards]
- Include: 3+ Bloom's levels, 2+ AfL strategies, differentiation
- Resources: [list available materials]
- Format: [5-part/5E/other]
```

### Differentiated Lesson Prompt
```
Design a differentiated lesson for Grade [X] [Subject] on [Topic].
- Learner groups: struggling, average, advanced
- Provide 3 activity variations for main practice task
- Include scaffolding strategies and extension activities
- [other requirements]
```

### AfL-Focused Prompt
```
Create a lesson plan emphasizing formative assessment for [topic].
- Integrate at least 4 AfL strategies throughout
- Include specific questioning techniques
- Design exit ticket with clear success criteria
- [other requirements]
```

## Quality Checklist

Before finalizing lesson plans, verify:
- [ ] Clear, measurable learning objectives (SMART format)
- [ ] Bloom's Taxonomy: at least 3 levels represented
- [ ] AfL strategies: at least 2-3 embedded throughout
- [ ] Differentiation: explicit for at least 2 learner groups
- [ ] Time allocations: realistic for standard class period
- [ ] Resources: listed with practical alternatives
- [ ] Cultural relevance: Pakistani context and examples
- [ ] Age-appropriate: language and activities suitable
- [ ] Clear instructions: actionable for teachers
- [ ] Assessment: both formative and summative included

---

## Memory Update Protocol

**CRITICAL**: After completing any lesson planning or prompt engineering task:
1. ✅ Update this MEMORY.md with effective pedagogical patterns
2. ✅ Document successful prompt templates that generated quality lessons
3. ✅ Record subject-specific patterns discovered
4. ✅ Note common lesson plan gaps and how to address them
5. ✅ Create separate topic files for curriculum-specific requirements

**What to save:**
- Effective lesson plan structures for different subjects/grades
- Successful prompt engineering templates
- Pedagogical frameworks that work well in Pakistani context
- AfL strategies that proved effective for specific lesson types
- Differentiation approaches for diverse classrooms
- Common curriculum alignment challenges and solutions

**What NOT to save:**
- Individual lesson plan content (unless it exemplifies a pattern)
- One-off teacher requests (unless they reveal a common need)
- Subject-specific content details (focus on pedagogical structure)

**Topic file suggestions:**
- `prompt-templates.md` - Proven LLM prompt templates for lesson generation
- `curriculum-alignment.md` - Board-specific requirements and patterns
- `differentiation-strategies.md` - Effective approaches for diverse learners
- `afl-techniques.md` - Assessment for Learning strategies catalog

---
*Last updated: 2026-02-16*
