import { useState, useEffect, useRef } from 'react'

const API_BASE = ''  // Proxied through Vite

// Icons as SVG components
const BookIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
)

const UserIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
    </svg>
)

const SparklesIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
        <path d="M5 3v4" />
        <path d="M19 17v4" />
        <path d="M3 5h4" />
        <path d="M17 19h4" />
    </svg>
)

const CheckIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 6 9 17 4 12" />
    </svg>
)

const DownloadIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
)

const CopyIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
)

const FileIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
        <polyline points="14 2 14 8 20 8" />
    </svg>
)

const ClockIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
    </svg>
)

const GraduationIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
        <path d="M6 12v5c3 3 9 3 12 0v-5" />
    </svg>
)

const BookOpenIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
)

function App() {
    const [activeView, setActiveView] = useState('generate')
    const [loading, setLoading] = useState(false)
    const [status, setStatus] = useState(null)
    const [books, setBooks] = useState([])
    const [lessonPlan, setLessonPlan] = useState(null)
    const [lessonTypes, setLessonTypes] = useState({})
    const [lessonMeta, setLessonMeta] = useState(null)

    // Form states
    const [generateForm, setGenerateForm] = useState({
        grade: 'Grade 2',
        subject: 'English',
        lesson_number: 1,
        selected_types: ['recall']  // Default to first type
    })

    const [uploadForm, setUploadForm] = useState({
        grade: 'Grade 2',
        subject: 'English',
        book_type: 'learners',
        title: '',
        term: 'Term 1'
    })

    const [uploadType, setUploadType] = useState('textbook')
    const [selectedFile, setSelectedFile] = useState(null)
    const fileInputRef = useRef(null)

    // Fetch initial data
    useEffect(() => {
        fetchBooks()
        fetchLessonTypes()
    }, [])

    // Update lesson types when subject changes
    useEffect(() => {
        if (lessonTypes[generateForm.subject]) {
            const types = lessonTypes[generateForm.subject]
            if (types.length > 0) {
                // Keep only valid types for the new subject
                const validTypes = generateForm.selected_types.filter(t =>
                    types.find(lt => lt.type === t)
                )
                if (validTypes.length === 0) {
                    setGenerateForm(prev => ({ ...prev, selected_types: [types[0].type] }))
                } else {
                    setGenerateForm(prev => ({ ...prev, selected_types: validTypes }))
                }
            }
        }
    }, [generateForm.subject, lessonTypes])

    const fetchBooks = async () => {
        try {
            const res = await fetch(`${API_BASE}/ingest/books`)
            const data = await res.json()
            setBooks(data.books || [])
        } catch (err) {
            console.error('Failed to fetch books:', err)
        }
    }

    const fetchLessonTypes = async () => {
        try {
            const res = await fetch(`${API_BASE}/generate/lesson-types`)
            const data = await res.json()
            setLessonTypes(data)
        } catch (err) {
            console.error('Failed to fetch lesson types:', err)
        }
    }

    const toggleLessonType = (type) => {
        setGenerateForm(prev => {
            const types = prev.selected_types
            if (types.includes(type)) {
                // Don't allow deselecting if it's the only one
                if (types.length === 1) return prev
                return { ...prev, selected_types: types.filter(t => t !== type) }
            } else {
                return { ...prev, selected_types: [...types, type] }
            }
        })
    }

    const handleGenerate = async (e) => {
        e.preventDefault()
        setLoading(true)
        setStatus({ type: 'loading', message: 'Generating lesson plan...' })
        setLessonPlan(null)
        setLessonMeta(null)

        try {
            // For now, use the first selected type (backend currently supports single type)
            const primaryType = generateForm.selected_types[0]

            const res = await fetch(`${API_BASE}/generate/lesson-plan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    grade: generateForm.grade,
                    subject: generateForm.subject,
                    lesson_type: primaryType,
                    page_start: generateForm.lesson_number,
                    page_end: generateForm.lesson_number
                })
            })

            const data = await res.json()

            if (data.success) {
                setLessonPlan(data.html_content || '')
                setLessonMeta({
                    grade: generateForm.grade,
                    subject: generateForm.subject,
                    lessonNumber: generateForm.lesson_number,
                    types: generateForm.selected_types
                })
                setStatus({ type: 'success', message: 'Lesson plan generated successfully!' })
            } else {
                setStatus({ type: 'error', message: data.error || 'Generation failed' })
            }
        } catch (err) {
            setStatus({ type: 'error', message: err.message })
        } finally {
            setLoading(false)
        }
    }

    const handleUpload = async (e) => {
        e.preventDefault()
        if (!selectedFile) {
            setStatus({ type: 'error', message: 'Please select a file' })
            return
        }

        setLoading(true)
        setStatus({ type: 'loading', message: `Processing ${uploadType}...` })

        const formData = new FormData()
        formData.append('file', selectedFile)
        formData.append('grade', uploadForm.grade)
        formData.append('subject', uploadForm.subject)

        if (uploadType === 'textbook') {
            formData.append('book_type', uploadForm.book_type)
            formData.append('title', uploadForm.title)
        } else {
            formData.append('term', uploadForm.term)
        }

        try {
            const endpoint = uploadType === 'textbook' ? '/ingest/textbook' : '/ingest/sow'
            const res = await fetch(`${API_BASE}${endpoint}`, {
                method: 'POST',
                body: formData
            })

            const data = await res.json()

            if (data.success) {
                setStatus({
                    type: 'success',
                    message: `${data.message}. Pages: ${data.pages_processed || 0}`
                })
                setSelectedFile(null)
                if (fileInputRef.current) fileInputRef.current.value = ''
                fetchBooks()
            } else {
                setStatus({ type: 'error', message: data.error || 'Upload failed' })
            }
        } catch (err) {
            setStatus({ type: 'error', message: err.message })
        } finally {
            setLoading(false)
        }
    }

    const handleFileDrop = (e) => {
        e.preventDefault()
        const file = e.dataTransfer.files[0]
        if (file) setSelectedFile(file)
    }

    const handleCopy = () => {
        if (lessonPlan) {
            // Create a temporary element to extract text from HTML
            const temp = document.createElement('div')
            temp.innerHTML = lessonPlan
            navigator.clipboard.writeText(temp.textContent || temp.innerText)
            setStatus({ type: 'success', message: 'Copied to clipboard!' })
            setTimeout(() => setStatus(null), 2000)
        }
    }

    const handleDownload = () => {
        if (lessonPlan) {
            const blob = new Blob([lessonPlan], { type: 'text/html' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `lesson-plan-${generateForm.grade}-${generateForm.subject}-L${generateForm.lesson_number}.html`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
        }
    }

    const currentLessonTypes = lessonTypes[generateForm.subject] || []

    const formatTypeName = (type) => {
        return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    }

    return (
        <div className="app">
            {/* Header */}
            <header className="header">
                <div className="logo">
                    <BookIcon className="logo-icon" />
                    <span className="logo-text">Lesson Plan Generator</span>
                </div>
                <div className="user-area">
                    <UserIcon className="user-icon" />
                    <span className="user-name">Teacher Portal</span>
                </div>
            </header>

            {/* Secondary Navigation */}
            <div style={{ padding: '16px 48px', background: 'var(--background)' }}>
                <div className="secondary-nav">
                    <button
                        className={`nav-btn ${activeView === 'generate' ? 'active' : ''}`}
                        onClick={() => setActiveView('generate')}
                    >
                        Generate
                    </button>
                    <button
                        className={`nav-btn ${activeView === 'upload' ? 'active' : ''}`}
                        onClick={() => setActiveView('upload')}
                    >
                        Upload
                    </button>
                    <button
                        className={`nav-btn ${activeView === 'library' ? 'active' : ''}`}
                        onClick={() => setActiveView('library')}
                    >
                        Library
                    </button>
                </div>
            </div>

            {/* Generate View */}
            {activeView === 'generate' && (
                <div className="main-content">
                    {/* Form Panel */}
                    <div className="form-panel">
                        <h1 className="panel-title">Create Your Lesson Plan</h1>
                        <p className="panel-subtitle">
                            Fill in the details below to generate a customized lesson plan for your class.
                        </p>

                        <form onSubmit={handleGenerate}>
                            {/* Grade Level */}
                            <div className="form-field">
                                <label className="form-label">Grade Level</label>
                                <select
                                    className="form-select"
                                    value={generateForm.grade}
                                    onChange={e => setGenerateForm({ ...generateForm, grade: e.target.value })}
                                >
                                    <option value="Grade 2">Grade 2</option>
                                </select>
                            </div>

                            {/* Subject */}
                            <div className="form-field">
                                <label className="form-label">Subject</label>
                                <select
                                    className="form-select"
                                    value={generateForm.subject}
                                    onChange={e => setGenerateForm({ ...generateForm, subject: e.target.value })}
                                >
                                    <option value="English">English</option>
                                    <option value="Mathematics">Mathematics</option>
                                </select>
                            </div>

                            {/* Lesson Number */}
                            <div className="form-field">
                                <label className="form-label">Lesson Number</label>
                                <input
                                    type="number"
                                    className="form-input"
                                    min="1"
                                    value={generateForm.lesson_number}
                                    onChange={e => setGenerateForm({ ...generateForm, lesson_number: parseInt(e.target.value) || 1 })}
                                    placeholder="Enter lesson number"
                                    required
                                />
                            </div>

                            {/* Lesson Plan Type */}
                            <div className="form-field">
                                <label className="form-label">Lesson Plan Type</label>
                                <p className="form-hint">Select one or more plan types</p>
                                <div className="lesson-type-options">
                                    {currentLessonTypes.map(lt => (
                                        <div
                                            key={lt.type}
                                            className={`lesson-type-option ${generateForm.selected_types.includes(lt.type) ? 'selected' : ''}`}
                                            onClick={() => toggleLessonType(lt.type)}
                                        >
                                            <div className="lesson-type-checkbox">
                                                <CheckIcon />
                                            </div>
                                            <span className="lesson-type-label">{formatTypeName(lt.type)}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Generate Button */}
                            <button type="submit" className="generate-btn" disabled={loading}>
                                {loading ? (
                                    <>
                                        <span className="spinner"></span>
                                        Generating...
                                    </>
                                ) : (
                                    <>
                                        <SparklesIcon />
                                        Generate Lesson Plan
                                    </>
                                )}
                            </button>
                        </form>

                        {status && (
                            <div className={`status ${status.type}`}>
                                {status.type === 'loading' && <span className="spinner"></span>}
                                {status.message}
                            </div>
                        )}
                    </div>

                    {/* Output Panel */}
                    <div className="output-panel">
                        <div className="output-header">
                            <h2 className="output-title">Generated Lesson Plan</h2>
                            {lessonPlan && (
                                <div className="output-actions">
                                    <button className="action-btn" onClick={handleCopy} title="Copy to clipboard">
                                        <CopyIcon />
                                    </button>
                                    <button className="action-btn" onClick={handleDownload} title="Download HTML">
                                        <DownloadIcon />
                                    </button>
                                </div>
                            )}
                        </div>
                        <div className="output-divider"></div>

                        {lessonMeta && (
                            <div className="lesson-meta">
                                <div className="meta-item">
                                    <GraduationIcon />
                                    <span>{lessonMeta.grade}</span>
                                </div>
                                <div className="meta-item">
                                    <BookOpenIcon />
                                    <span>{lessonMeta.subject}</span>
                                </div>
                                <div className="meta-item">
                                    <ClockIcon />
                                    <span>Lesson {lessonMeta.lessonNumber}</span>
                                </div>
                            </div>
                        )}

                        {lessonPlan ? (
                            <div
                                className="lesson-plan"
                                dangerouslySetInnerHTML={{ __html: lessonPlan }}
                            />
                        ) : (
                            <div className="empty-state">
                                <FileIcon />
                                <p>No lesson plan generated yet</p>
                                <span>Fill in the form and click "Generate" to create your lesson plan</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Upload View */}
            {activeView === 'upload' && (
                <div className="main-content">
                    <div className="form-panel" style={{ width: '100%', maxWidth: '600px', margin: '0 auto' }}>
                        <h1 className="panel-title">Upload Documents</h1>
                        <p className="panel-subtitle">
                            Upload textbooks or Scheme of Work documents to enhance lesson plan generation.
                        </p>

                        <div className="secondary-nav" style={{ marginBottom: '24px' }}>
                            <button
                                className={`nav-btn ${uploadType === 'textbook' ? 'active' : ''}`}
                                onClick={() => setUploadType('textbook')}
                            >
                                Textbook
                            </button>
                            <button
                                className={`nav-btn ${uploadType === 'sow' ? 'active' : ''}`}
                                onClick={() => setUploadType('sow')}
                            >
                                Scheme of Work
                            </button>
                        </div>

                        <form onSubmit={handleUpload}>
                            <div
                                className={`file-upload ${selectedFile ? 'has-file' : ''}`}
                                onDrop={handleFileDrop}
                                onDragOver={e => e.preventDefault()}
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <div className="file-upload-icon">📁</div>
                                {selectedFile ? (
                                    <p><strong>{selectedFile.name}</strong></p>
                                ) : (
                                    <>
                                        <p>Drag & drop your {uploadType === 'textbook' ? 'PDF' : 'PDF/Image'} here</p>
                                        <span>or click to browse</span>
                                    </>
                                )}
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    style={{ display: 'none' }}
                                    accept={uploadType === 'textbook' ? '.pdf' : '.pdf,.png,.jpg,.jpeg'}
                                    onChange={e => setSelectedFile(e.target.files[0])}
                                />
                            </div>

                            <div className="form-grid">
                                <div className="form-field">
                                    <label className="form-label">Grade</label>
                                    <select
                                        className="form-select"
                                        value={uploadForm.grade}
                                        onChange={e => setUploadForm({ ...uploadForm, grade: e.target.value })}
                                    >
                                        <option value="Grade 2">Grade 2</option>
                                    </select>
                                </div>

                                <div className="form-field">
                                    <label className="form-label">Subject</label>
                                    <select
                                        className="form-select"
                                        value={uploadForm.subject}
                                        onChange={e => setUploadForm({ ...uploadForm, subject: e.target.value })}
                                    >
                                        <option value="English">English</option>
                                        <option value="Mathematics">Mathematics</option>
                                    </select>
                                </div>

                                {uploadType === 'textbook' ? (
                                    <>
                                        <div className="form-field">
                                            <label className="form-label">Book Type</label>
                                            <select
                                                className="form-select"
                                                value={uploadForm.book_type}
                                                onChange={e => setUploadForm({ ...uploadForm, book_type: e.target.value })}
                                            >
                                                {uploadForm.subject === 'English' ? (
                                                    <>
                                                        <option value="learners">Learner's Book</option>
                                                        <option value="activity">Activity Book</option>
                                                        <option value="reading">Reading Book</option>
                                                    </>
                                                ) : (
                                                    <>
                                                        <option value="course_book">Course Book</option>
                                                        <option value="workbook">Workbook</option>
                                                    </>
                                                )}
                                            </select>
                                        </div>
                                        <div className="form-field">
                                            <label className="form-label">Book Title</label>
                                            <input
                                                type="text"
                                                className="form-input"
                                                value={uploadForm.title}
                                                onChange={e => setUploadForm({ ...uploadForm, title: e.target.value })}
                                                placeholder="e.g., Oxford English Grade 2"
                                                required
                                            />
                                        </div>
                                    </>
                                ) : (
                                    <div className="form-field">
                                        <label className="form-label">Term</label>
                                        <select
                                            className="form-select"
                                            value={uploadForm.term}
                                            onChange={e => setUploadForm({ ...uploadForm, term: e.target.value })}
                                        >
                                            <option value="Term 1">Term 1</option>
                                            <option value="Term 2">Term 2</option>
                                            <option value="Term 3">Term 3</option>
                                        </select>
                                    </div>
                                )}
                            </div>

                            <button type="submit" className="generate-btn" disabled={loading || !selectedFile}>
                                {loading ? (
                                    <>
                                        <span className="spinner"></span>
                                        Processing...
                                    </>
                                ) : (
                                    'Upload & Process'
                                )}
                            </button>
                        </form>

                        {status && (
                            <div className={`status ${status.type}`}>
                                {status.type === 'loading' && <span className="spinner"></span>}
                                {status.message}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Library View */}
            {activeView === 'library' && (
                <div className="main-content">
                    <div className="form-panel" style={{ width: '100%', maxWidth: '800px', margin: '0 auto' }}>
                        <h1 className="panel-title">Document Library</h1>
                        <p className="panel-subtitle">
                            View all uploaded textbooks and scheme of work documents.
                        </p>

                        {books.length === 0 ? (
                            <div className="empty-state" style={{ minHeight: '200px' }}>
                                <FileIcon />
                                <p>No documents uploaded yet</p>
                                <span>Upload a textbook or SOW to get started</span>
                            </div>
                        ) : (
                            <div className="books-list">
                                {books.map(book => (
                                    <div key={book.id} className="book-item">
                                        <div className="book-info">
                                            <h3>{book.title}</h3>
                                            <p>{book.grade_level} • {book.subject}</p>
                                        </div>
                                        <div className="book-badges">
                                            <span className="book-badge">{book.book_type}</span>
                                            {book.page_count && (
                                                <span className="book-badge">{book.page_count} pages</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        <button
                            className="generate-btn"
                            style={{ marginTop: '24px', background: 'var(--background-light)', color: 'var(--text-primary)', border: '1px solid var(--border)' }}
                            onClick={fetchBooks}
                        >
                            Refresh List
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}

export default App
