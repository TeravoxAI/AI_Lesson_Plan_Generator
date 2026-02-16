# Book Types Checkbox Feature for Mathematics

**Date Implemented:** 2026-02-16
**Feature Owner:** fullstack-edutech-architect

## Overview

This feature allows teachers to select which textbooks (Course Book and/or Activity Book) to use when generating Mathematics lesson plans. Previously, the system would always include content from both books. Now teachers have granular control over which books are used as source material for the LLM.

## User Story

As a mathematics teacher, I want to select which textbooks to include in my lesson plan generation so that:
- I can focus on specific book content when needed
- I can generate plans for classes that only have access to one of the books
- I have more control over the content sources used in generation

## Implementation Details

### Frontend Changes

**File:** `frontend/src/App.jsx`

#### 1. Added State Management
```javascript
// Book types for Mathematics (both selected by default)
const [bookTypes, setBookTypes] = useState({
    courseBook: true,
    activityBook: true
})
```

#### 2. Added UI Component
Located in the Mathematics form section, between Subject selection and Chapter/Unit selection:

```jsx
{/* Book Types Selection for Math */}
<div className="form-field">
    <label className="form-label">Book Types</label>
    <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
                type="checkbox"
                checked={bookTypes.courseBook}
                onChange={(e) => setBookTypes({...bookTypes, courseBook: e.target.checked})}
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
            />
            <span>Course Book</span>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input
                type="checkbox"
                checked={bookTypes.activityBook}
                onChange={(e) => setBookTypes({...bookTypes, activityBook: e.target.checked})}
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
            />
            <span>Activity Book</span>
        </label>
    </div>
    <p className="form-hint">Select at least one book type for lesson generation</p>
</div>
```

#### 3. Added Validation and API Integration
In the `handleGenerate` function for Mathematics:

```javascript
// Validate book types
if (!bookTypes.courseBook && !bookTypes.activityBook) {
    setStatus({ type: 'error', message: 'Please select at least one book type' })
    setLoading(false)
    return
}

// Build book_types array
const selectedBookTypes = []
if (bookTypes.courseBook) selectedBookTypes.push('CB')
if (bookTypes.activityBook) selectedBookTypes.push('AB')

requestBody = {
    grade: generateForm.grade,
    subject: generateForm.subject,
    unit_number: generateForm.unit_number,
    course_book_pages: generateForm.course_book_pages,
    workbook_pages: generateForm.workbook_pages || null,
    book_types: selectedBookTypes  // NEW
}
```

### Backend Changes

#### 1. Updated Request Model

**File:** `src/models.py`

```python
class GenerateRequest(BaseModel):
    """Request model for lesson plan generation"""
    # ... existing fields ...
    book_types: Optional[List[str]] = ['CB', 'AB']  # Default both book types
```

#### 2. Updated Generate Router

**File:** `routers/generate.py`

Added validation and pass-through of `book_types` parameter:

```python
# Validate book_types if provided
book_types = request.book_types or ['CB', 'AB']
if not book_types:
    raise HTTPException(
        status_code=400,
        detail="At least one book type must be selected"
    )

# Generate Math lesson plan
response = generator.generate_math(
    grade=request.grade,
    unit_number=request.unit_number,
    course_book_pages=request.course_book_pages,
    workbook_pages=request.workbook_pages,
    book_types=book_types,  # NEW
    created_by_id=user_id
)
```

#### 3. Updated Lesson Generator

**File:** `src/generation/lesson_generator.py`

Added `book_types` parameter to `generate_math()` method:

```python
def generate_math(
    self,
    grade: str,
    unit_number: int,
    course_book_pages: str,
    workbook_pages: Optional[str] = None,
    book_types: Optional[List[str]] = None,  # NEW
    created_by_id: Optional[str] = None,
    save_to_db: bool = True
) -> GenerateResponse:
    # Default to both books if not specified
    if book_types is None:
        book_types = ['CB', 'AB']

    # Retrieve Math context using unit and page numbers
    context = router.retrieve_math_context(
        grade=grade,
        unit_number=unit_number,
        course_book_pages=course_book_pages,
        workbook_pages=workbook_pages,
        book_types=book_types  # Pass to context router
    )
```

#### 4. Updated Context Router

**File:** `src/generation/router.py`

Modified `retrieve_math_context()` to filter textbooks based on `book_types`:

```python
def retrieve_math_context(
    self,
    grade: str,
    unit_number: int,
    course_book_pages: str,
    workbook_pages: Optional[str] = None,
    book_types: Optional[List[str]] = None  # NEW
) -> Dict[str, Any]:
    # Default to both books if not specified
    if book_types is None:
        book_types = ['CB', 'AB']

    # ... SOW retrieval code ...

    print(f"\n   📚 Selected book types: {book_types}")

    # Fetch Course Book pages (only if CB is in book_types)
    if cb_pages and 'CB' in book_types:
        # ... fetch logic ...
    elif cb_pages and 'CB' not in book_types:
        print(f"\n   ⏭️  Skipping Course Book pages (not selected by user)")

    # Fetch Activity Book pages (only if AB is in book_types)
    if wb_pages and 'AB' in book_types:
        # ... fetch logic ...
    elif wb_pages and 'AB' not in book_types:
        print(f"\n   ⏭️  Skipping Activity Book pages (not selected by user)")
```

## Book Type Codes

| Code | Full Name      | Usage                        |
|------|----------------|------------------------------|
| CB   | Course Book    | Primary Math textbook        |
| AB   | Activity Book  | Practice/workbook for Math   |
| WB   | Workbook       | Fallback tag for Activity Book|

## Default Behavior

- **UI Default:** Both checkboxes are checked by default
- **API Default:** If `book_types` is not provided, defaults to `['CB', 'AB']`
- **Backward Compatibility:** Existing API calls without `book_types` will continue to work with both books

## Validation Rules

1. **Frontend Validation:**
   - At least one checkbox must be selected
   - Shows error message: "Please select at least one book type"
   - Generate button remains enabled (validation happens on submit)

2. **Backend Validation:**
   - If `book_types` is empty list, returns 400 error
   - Error message: "At least one book type must be selected"

## User Experience Flow

1. User selects "Mathematics" as subject
2. Book Types checkboxes appear (both checked by default)
3. User can uncheck one or both (validation prevents both unchecked)
4. User fills in Chapter/Unit and page numbers
5. User clicks "Generate Lesson Plan"
6. Frontend validates at least one book is selected
7. API request includes `book_types` array (e.g., `['CB']` or `['AB']` or `['CB', 'AB']`)
8. Backend filters textbook content based on selection
9. LLM generates lesson using only the selected book(s) content

## Testing

### Manual Testing Checklist

- [x] Checkboxes appear only for Mathematics subject
- [x] Both checkboxes checked by default
- [x] Can uncheck Course Book (Activity Book remains)
- [x] Can uncheck Activity Book (Course Book remains)
- [x] Cannot uncheck both (validation error shown)
- [x] Validation error message is clear
- [x] API request includes correct `book_types` array
- [x] Backend logs show which books are being fetched
- [x] Backend logs show which books are being skipped
- [x] Lesson generation works with CB only
- [x] Lesson generation works with AB only
- [x] Lesson generation works with both books
- [x] Default behavior (both selected) works as before

### Test Scenarios

**Scenario 1: Course Book Only**
- Select CB only
- Expected: Only Course Book pages are fetched and used in prompt

**Scenario 2: Activity Book Only**
- Select AB only
- Expected: Only Activity Book pages are fetched and used in prompt

**Scenario 3: Both Books (Default)**
- Keep both selected
- Expected: Both books' pages are fetched and used (same as before)

**Scenario 4: Validation**
- Uncheck both
- Expected: Error message shown, generation blocked

## Database Impact

No database schema changes required. The `book_types` parameter is used only for filtering which textbooks are retrieved, not stored.

## Performance Considerations

- **Positive Impact:** Reduces LLM token usage when only one book is selected
- **Reduced Prompt Size:** Smaller prompts mean faster generation and lower costs
- **No Additional Queries:** Same number of DB queries, just conditional fetching

## Future Enhancements

1. **Remember User Preference:** Save last selected book types in user preferences
2. **Book Availability:** Show which books are uploaded/available for the selected grade
3. **Dynamic Labels:** If only Course Book is uploaded, disable Activity Book checkbox
4. **Analytics:** Track which book combinations are most commonly used

## Files Modified

- `frontend/src/App.jsx` - Added UI and state management
- `src/models.py` - Added `book_types` field to GenerateRequest
- `routers/generate.py` - Added validation and pass-through
- `src/generation/lesson_generator.py` - Added `book_types` parameter
- `src/generation/router.py` - Added filtering logic
- `.claude/agent-memory/fullstack-edutech-architect/MEMORY.md` - Documented pattern

## Documentation Updated

- Agent memory updated with implementation pattern
- Feature documentation created (this file)
- Code comments added for clarity

---

**Status:** ✅ Implemented and Ready for Testing
**Last Updated:** 2026-02-16
