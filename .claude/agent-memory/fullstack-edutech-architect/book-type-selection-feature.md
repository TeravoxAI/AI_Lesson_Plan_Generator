# Book Type Selection Feature for Mathematics

**Implemented:** 2026-02-15

## Overview
Added checkboxes to allow users to select which textbooks to use when generating Mathematics lesson plans (Course Book and/or Activity Book).

## Implementation Details

### Frontend Changes (App.jsx)

**1. State Management**
- Added `book_types: ['CB', 'AB']` to `generateForm` state (defaults to both selected)
- Added `toggleBookType()` function to handle checkbox toggling (prevents deselecting last option)

**2. UI Components**
- Added "Book Type" section with two checkboxes after Chapter/Unit selection
- Checkboxes use same styling as lesson type selection (green theme with CheckIcon)
- Shows between "Chapter/Unit" and "Course Book Pages" fields
- Only visible when Mathematics subject is selected

**3. Validation**
- Frontend validates at least one book type is selected before API call
- Error message: "Please select at least one book type"

**4. State Reset**
- Book types reset to default ['CB', 'AB'] when switching subjects

### Backend Changes

**1. Models (src/models.py)**
```python
book_types: Optional[List[str]] = None  # ["CB", "AB"]
```
- Added to `GenerateRequest` model

**2. Router (routers/generate.py)**
- Accepts `book_types` parameter (defaults to ["CB", "AB"] if not provided)
- Validates book_types contains only "CB" or "AB"
- Validates at least one book type is selected
- Passes book_types to `generator.generate_math()`

**3. Lesson Generator (src/generation/lesson_generator.py)**
- Added `book_types` parameter to `generate_math()`
- Defaults to ["CB", "AB"] if None
- Passes to `router.retrieve_math_context()`

**4. Context Router (src/generation/router.py)**
- Added `book_types` parameter to `retrieve_math_context()`
- Filters textbook fetching based on selected book types:
  - If "CB" in book_types → fetch Course Book pages
  - If "AB" in book_types → fetch Activity Book/Workbook pages
- Logs which books are being skipped due to book_types filter

## API Request Format

**Example with both books:**
```json
{
  "grade": "Grade 2",
  "subject": "Mathematics",
  "unit_number": 1,
  "course_book_pages": "145-150",
  "workbook_pages": "80-85",
  "book_types": ["CB", "AB"]
}
```

**Example with Course Book only:**
```json
{
  "grade": "Grade 2",
  "subject": "Mathematics",
  "unit_number": 1,
  "course_book_pages": "145-150",
  "book_types": ["CB"]
}
```

## Database Mapping

**Book Type Codes:**
- `CB` = Course Book (db: book_type="course_book" or book_tag="CB")
- `AB` = Activity Book (db: book_type="workbook" or book_tag="AB"/"WB")

## Backward Compatibility

- If `book_types` not provided in request → defaults to ["CB", "AB"]
- Existing API calls without book_types will continue to work unchanged

## Testing Checklist

✅ Checkboxes appear only for Mathematics subject
✅ User can select Course Book only
✅ User can select Activity Book only
✅ User can select both
✅ Cannot deselect last remaining checkbox
✅ Validation prevents generation without selection
✅ Book type selection resets when subject changes
✅ Backend filters textbook content correctly
✅ Frontend build succeeds
✅ Backend Python files compile without errors

## Files Modified

**Frontend:**
- `/home/taha-mazhar/ibm/AI_Lesson_Plan_Generator/frontend/src/App.jsx`

**Backend:**
- `/home/taha-mazhar/ibm/AI_Lesson_Plan_Generator/src/models.py`
- `/home/taha-mazhar/ibm/AI_Lesson_Plan_Generator/routers/generate.py`
- `/home/taha-mazhar/ibm/AI_Lesson_Plan_Generator/src/generation/lesson_generator.py`
- `/home/taha-mazhar/ibm/AI_Lesson_Plan_Generator/src/generation/router.py`

## User Experience Flow

1. User selects "Mathematics" as subject
2. **New:** Book Type checkboxes appear with both selected by default
3. User selects desired book types (Course Book, Activity Book, or both)
4. User selects chapter/unit
5. User enters course book pages
6. User optionally enters workbook pages
7. User clicks "Generate Lesson Plan"
8. Backend fetches only the selected book types
9. LLM generates lesson plan using selected textbook content

## Notes for Future Development

- Consider adding similar book type selection for English (LB, AB, ORT, TR)
- Book type selection could be saved in user preferences
- Could add tooltips explaining difference between Course Book and Activity Book
- Consider conditional display of page number fields based on selected book types
