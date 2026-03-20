The project currently generates lesson plans 
from a SOW (Scheme of Work) JSON file but has several critical data-scoping bugs. Below is 
a full breakdown of the issues, the JSON structure, and exactly what needs to be fixed.

---

## JSON STRUCTURE

The SOW JSON is structured as follows:

{
  "curriculum": {
    "total_teaching_weeks": 17,
    "weeks": [
      {
        "week": 12,
        "topics": [
          {
            "topic": "Making Patterns",
            "stream": false,
            "slos": [...],         // ⚠️ UNIT-LEVEL — contains SLOs for ALL topics in the unit
            "skills": [...],       // ⚠️ UNIT-LEVEL — contains skills for ALL topics in the unit
            "afl_strategies": [...], // ⚠️ UNIT-LEVEL — contains AFL for ALL topics in the unit
            "classwork": [...],    // ⚠️ UNIT-LEVEL — contains pages for ALL topics in the unit
            "teaching_strategy": {
              "title": "Making Patterns",
              "description": "...", // ✅ TOPIC-SPECIFIC — this is correct
              "afl_strategies": [...] // ✅ TOPIC-SPECIFIC — this is correct
            }
          },
          {
            "topic": "Drawing in Notebook",
            "stream": false,
            "teaching_strategy": { ... }
            // Note: Drawing in Notebook has NO slos/skills/afl/classwork fields
          }
        ]
      }
    ]
  }
}

The core problem is that slos, skills, afl_strategies, and classwork at the topic level are 
inherited from the parent unit and contain data for ALL topics in that unit — not just the 
topic being taught in that specific week.

---

## THE BUGS TO FIX

### BUG 1: SLOs are not filtered to the current topic

Currently the agent passes all unit-level SLOs to the lesson plan. Each SLO in the array 
corresponds to a specific topic. The agent must match each SLO to the topic it belongs to 
by using the teaching_strategy description as the source of truth.

FIX: For each week's primary topic, only include SLOs that are semantically relevant to 
that specific topic. Use the topic title and its teaching_strategy.description as context 
to filter which SLOs from the slos array actually belong to this topic. Do NOT include SLOs 
that clearly belong to other topics in the same unit.

Example: Week 12 topic is "Making Patterns". The unit slos array contains:
- "to discuss the importance of clean/ pollution free environment"  → belongs to different topic
- "complete the picture as per sample picture"                      → belongs to different topic  
- "trace, draw and colour the patterns"                             → ✅ belongs to Making Patterns
- "distinguish between different human emotions"                    → belongs to different topic
- "draw different facial expressions"                               → belongs to different topic
- "make a 3D flower"                                                → belongs to different topic

Only "trace, draw and colour the patterns" should appear in the Making Patterns lesson plan.

### BUG 2: Skills are not filtered to the current topic

The unit-level skills array contains skills that apply across all topics in the unit. Some 
skills are generic to the unit, others are specific to certain topics.

FIX: Filter skills to only those relevant to the specific topic being taught. Use the 
topic title and teaching_strategy.description to determine which skills apply. For example, 
"Sequencing" is clearly relevant to Making Patterns, but "Shading" or "3D making" related 
skills would not be. If a skill like "Creativity" appears at the unit level but is too 
generic to be topic-specific, include it only if it genuinely applies based on the 
teaching_strategy description.

### BUG 3: Classwork pages are not filtered to the current topic

The unit-level classwork array lists textbook pages for ALL topics in the unit (e.g., 
"Textbook pgs 32, 33, 34, 35"). Each page corresponds to a specific topic.

FIX: Extract only the page(s) relevant to the current topic. Use the teaching_strategy 
description to identify the correct page reference — descriptions often contain explicit 
page mentions like "textbook pg-33" or "pg 33". If no specific page is mentioned in the 
description, include the full classwork array as a fallback. Always include 
"Drawing in Notebook" in classwork if it appears as a sibling topic in the same week.

### BUG 4: AFL strategies are not scoped to the current topic

The unit-level afl_strategies is a union of all sub-activity AFL strategies. The 
teaching_strategy.afl_strategies field IS topic-specific and should be used as the 
primary source.

FIX: Always use teaching_strategy.afl_strategies as the primary AFL source for the lesson 
plan's AFL Strategies field. Only supplement with unit-level afl_strategies if the 
topic-level array is empty.

### BUG 5: Methodology field is incomplete

The Methodology field should list the named teaching strategy methods used in the lesson 
(e.g., Brainstorming, Demonstration, Independent Work, Pair Discussion). These are 
extractable from the teaching_strategy.description by identifying bolded or labelled 
method names.

FIX: Parse the teaching_strategy.description to extract all named methodology labels. 
These are typically formatted as "**MethodName**:" or "Starter Activity (MethodName):" 
in the description text. Common ones to detect: Brainstorming, Demonstration, 
Independent Work, Pair Discussion, Think Pair and Share, Group Activity, Observation, 
KWL Chart, Muddiest Point. Always include at minimum: the starter activity method + 
any explicitly named instructional methods + assessment method.

### BUG 6: Brainstorming step is missing from the teaching activity body

The teaching_strategy.description for some topics begins directly with the main activity 
without a brainstorming opener — but the AFL strategies list Brainstorming, meaning a 
brainstorming step is expected.

FIX: If "Brainstorming" appears in teaching_strategy.afl_strategies but no brainstorming 
step is present in the description, prepend a contextually appropriate brainstorming 
starter to the teaching activity. Generate this based on the topic — for example, for 
"Making Patterns" it would be about recognising basic shapes and patterns. This must be 
dynamic and topic-aware, not hardcoded.

### BUG 7: "Introduce topic and share SLOs" line is duplicated

The agent is inserting this line twice in the lesson plan body.

FIX: Ensure "Introduce the topic and share the SLOs with the students." appears exactly 
once, at the beginning of the teaching activity section, before the first methodology step.

### BUG 8: Period number is hardcoded

The Period field is being defaulted to 1 regardless of the actual period.

FIX: The SOW specifies "No of periods per week: 02". Period should not be hardcoded. 
Either derive it from context, accept it as a user input parameter, or leave it as a 
blank fill-in field if not determinable from the JSON.

---

## LESSON PLAN FIELD MAPPING (what field pulls from where)

Use this as the definitive mapping for every lesson plan generated:

| Lesson Plan Field       | Source                                                                 |
|-------------------------|------------------------------------------------------------------------|
| Week                    | weeks[].week                                                           |
| Topic                   | weeks[].topics[].topic (the primary topic, not Drawing in Notebook)   |
| SLOs                    | Filter weeks[].topics[].slos using BUG 1 logic above                  |
| Skills focused on       | Filter weeks[].topics[].skills using BUG 2 logic above                |
| Resources               | Filtered classwork pages (BUG 3) + standard materials from SOW        |
| Methodology             | Extracted from teaching_strategy.description (BUG 5)                  |
| Teaching Activity body  | teaching_strategy.description, structured into named method blocks     |
| AFL Strategies          | teaching_strategy.afl_strategies (primary), unit-level as fallback    |
| Classwork               | Filtered classwork pages (BUG 3) + Drawing in Notebook if applicable  |
| Success Criteria        | Generate dynamically based on the topic's SLOs and teaching activity  |
| Plenary / Wrap Up       | Generate dynamically — ask students to reflect on what they created   |
| HW / Online Assignment  | Default to None/Nil unless specified elsewhere                        |

---

## DYNAMIC GENERATION RULES (to prevent hardcoding)

These rules must apply generically for any topic in any week:

1. SLO filtering must be semantic — use the topic name and description as context, 
   never filter by hardcoded index positions or keyword lists.

2. Page number extraction must scan the description text for any mention of "pg", 
   "page", "textbook pg", or "pg." followed by a number — extract that number 
   dynamically.

3. Methodology extraction must scan description text for labelled method patterns 
   dynamically — do not hardcode a fixed list of methods per topic.

4. Success Criteria must be generated from the filtered SLOs and teaching activity 
   content — they should be specific to the topic, phrased as "Remember to: ..." 
   student-facing instructions.

5. Brainstorming injection (BUG 6) must be topic-aware — use the topic title and 
   SLOs to generate a relevant brainstorming prompt, never a generic placeholder.

6. The agent must handle weeks with multiple topics correctly — each topic in 
   weeks[].topics gets its own scoped data. If a week has two primary topics 
   (e.g., Week 4: Navigating a Maze + Colour the Birds), the lesson plan should 
   either generate separate plans per topic, or clearly section them, depending 
   on the user's request.

7. Drawing in Notebook topics carry no SLOs/skills/AFL of their own — they should 
   always be appended to the classwork field only, never treated as a standalone 
   lesson plan topic.

---

## EXPECTED OUTPUT QUALITY CHECK

After implementing fixes, verify the generated lesson plan for Week 12 / Making Patterns 
matches these expected values:

- SLOs: only "trace, draw and colour the patterns" (and optionally 
  "complete the picture as per sample picture" if contextually justified)
- Skills: Drawing, Colouring, Sequencing, Observing
- Resources: Textbook pg 33, whiteboard, markers, pencil, eraser, pencil colours
- Methodology: Brainstorming, Pair Discussion, Demonstration, Independent Work
- Teaching Activity: Brainstorming opener → Introduce topic + SLOs → 
  Demonstration → Independent Work → Peer/Self-Assessment
- AFL: Brainstorming, Peer/Self-Assessment
- Classwork: Textbook pg 33, Drawing in Notebook
- No duplicate lines anywhere in the output