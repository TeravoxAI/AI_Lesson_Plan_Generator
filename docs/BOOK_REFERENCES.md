# Book Reference Codes

## Overview
The Scheme of Work (SOW) uses short codes to reference different types of textbooks. These codes are stored in the `book_references` array within each `lesson_plan_type`.

## Book Type Codes

| Code | Full Name | Description | Database book_tag |
|------|-----------|-------------|-------------------|
| **LB** | Learner's Book / Course Book | Main textbook for students | `LB` |
| **AB** | Activity Book | Practice and activity workbook | `AB` |
| **ORT** | Oxford Reading Tree | Reading comprehension books | `ORT` |
| **TR** | Teacher Resources | Teacher's guide and resources | `TR` |
| **CB** | Course Book | Alternative name for main textbook | `CB` |
| **WB** | Workbook | Practice workbook (Math) | `WB` |

## How References Work

### 1. In SOW JSON Format
```json
{
  "lesson_plan_types": [
    {
      "type": "vocabulary_word_meaning",
      "book_references": [
        {
          "book_type": "LB",
          "book_name": "Learner's Book",
          "pages": [110, 111]
        },
        {
          "book_type": "AB",
          "book_name": "Activity Book",
          "pages": [88, 89]
        }
      ]
    }
  ]
}
```

### 2. Database Lookup Process
1. System extracts `book_type` (e.g., "LB") from SOW
2. Searches `textbooks` table using `book_tag` field
3. Retrieves specific page numbers from the book's `content_text` JSON

### 3. Page Content Format
Pages are stored in `content_text` as JSON array:
```json
[
  {
    "content": "8 Home, sweet home\n\nWhat kinds of homes...",
    "pdf_page_no": 1,
    "book_page_no": 110
  }
]
```

## Common Patterns

### English Lessons
- **LB** + **AB**: Most vocabulary, grammar, and writing lessons
- **LB** + **ORT**: Reading comprehension lessons
- **LB** only: Listening and speaking lessons
- **TR**: Background teacher notes and strategies

### Math Lessons
- **CB** (Course Book): Concept introduction
- **WB** (Workbook): Practice exercises

## System Behavior

### Multiple Book References
A single lesson type can reference 1 or more books. The system:
1. Fetches each book referenced
2. Retrieves specified pages from each
3. Concatenates all content for the LLM prompt

### Missing Books
If a book reference cannot be found:
- Warning logged: `⚠ Book not found for {book_type_code}`
- Generation continues with available content
- LLM generates based on partial context

### Page Numbers
- Pages are matched using either:
  - `book_page_no` (the number printed on the page)
  - `page_no` (sequential page number)
- System searches for both to maximize matches

## Debugging

### Check Available Books
```sql
SELECT id, grade_level, subject, book_tag, title
FROM textbooks
WHERE grade_level = '2' AND subject = 'English';
```

### Check SOW Book References
Look for `book_references` in the SOW extraction JSON:
```sql
SELECT id, grade_level, subject,
       jsonb_path_query(extraction, '$.curriculum.units[*].lessons[*].lesson_plan_types[*].book_references')
FROM sow_entries
WHERE grade_level = 'Grade 2' AND subject = 'English';
```

## Console Output Example

When generating a lesson plan:
```
📋 [SOW] Finding lesson 1 in SOW...
   📖 Book references found: 2
      - LB: pages [110, 111]
      - AB: pages [88, 89]
     - LB: pages [110, 111]
       🔍 Searching DB: grade='2', subject='English', book_tag='LB'
         Page 110: 8 Home, sweet home Think about it What kinds of homes...
         Page 111: 8 Home, sweet home Topic vocabulary Listen, point...
       ✓ Fetched 2 pages from 'English Grade 2 Course Book'
     - AB: pages [88, 89]
       🔍 Searching DB: grade='2', subject='English', book_tag='AB'
         Page 88: Activity 1: Match the animals to their homes...
         Page 89: Activity 2: Draw your dream home...
       ✓ Fetched 2 pages from 'English Grade 2 Activity Book'

   📝 Context Summary:
      - Book pages loaded: 4
      - Books used: LB (pages [110, 111]), AB (pages [88, 89])
```
