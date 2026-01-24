import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'

const API_BASE = ''  // Proxied through Vite

function App() {
    const [activeTab, setActiveTab] = useState('generate')
    const [loading, setLoading] = useState(false)
    const [status, setStatus] = useState(null)
    const [books, setBooks] = useState([])
    const [lessonPlan, setLessonPlan] = useState(null)
    const [lessonTypes, setLessonTypes] = useState({})

    // Form states
    const [generateForm, setGenerateForm] = useState({
        grade: 'Grade 2',
        subject: 'English',
        lesson_type: 'reading',
        page_start: 1,
        page_end: null,
        topic: ''
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
            if (types.length > 0 && !types.find(t => t.type === generateForm.lesson_type)) {
                setGenerateForm(prev => ({ ...prev, lesson_type: types[0].type }))
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

    const handleGenerate = async (e) => {
        e.preventDefault()
        setLoading(true)
        setStatus({ type: 'loading', message: 'Generating lesson plan...' })
        setLessonPlan(null)

        try {
            const res = await fetch(`${API_BASE}/generate/lesson-plan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...generateForm,
                    page_end: generateForm.page_end || generateForm.page_start
                })
            })

            const data = await res.json()

            if (data.success) {
                // Use HTML content directly from LLM
                setLessonPlan(data.html_content || '')
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

    const formatLessonPlan = (plan) => {
        if (!plan) return ''

        // Each field may contain rich markdown content from LLM
        const sections = []

        // Learning Objectives (SLOs)
        if (plan.slos && plan.slos.length > 0) {
            sections.push(`## 📎 Learning Objectives (SLOs)\n${plan.slos.map(slo => `- ${slo}`).join('\n')}`)
        }

        // Brainstorming/Warm-up Activity
        if (plan.brainstorming_activity) {
            sections.push(plan.brainstorming_activity)
        }

        // Methodology
        if (plan.methodology) {
            sections.push(plan.methodology)
        }

        // Main Teaching Activity
        if (plan.main_teaching_activity) {
            sections.push(plan.main_teaching_activity)
        }

        // Hands-On Activity
        if (plan.hands_on_activity) {
            sections.push(plan.hands_on_activity)
        }

        // Assessment for Learning (AFL)
        if (plan.afl) {
            sections.push(plan.afl)
        }

        // Resources
        if (plan.resources && plan.resources.length > 0) {
            sections.push(`## 📚 Resources\n${plan.resources.map(r => `- ${r}`).join('\n')}`)
        }

        return sections.join('\n\n---\n\n')
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
                    message: `${data.message}. Pages: ${data.pages_processed || 0}, Entries: ${data.entries_extracted || 0}`
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

    const currentLessonTypes = lessonTypes[generateForm.subject] || []

    return (
        <div className="app">
            <header className="header">
                <h1>Lesson Plan Generator</h1>
                <p>AI-powered curriculum-aware lesson planning for Grade 2</p>
            </header>

            <div className="tabs">
                <button
                    className={`tab ${activeTab === 'generate' ? 'active' : ''}`}
                    onClick={() => setActiveTab('generate')}
                >
                    ✨ Generate
                </button>
                <button
                    className={`tab ${activeTab === 'upload' ? 'active' : ''}`}
                    onClick={() => setActiveTab('upload')}
                >
                    📤 Upload
                </button>
                <button
                    className={`tab ${activeTab === 'library' ? 'active' : ''}`}
                    onClick={() => setActiveTab('library')}
                >
                    📖 Library
                </button>
            </div>

            {/* Generate Tab */}
            {activeTab === 'generate' && (
                <div className="card">
                    <h2><span className="icon">⚡</span> Generate Lesson Plan</h2>

                    <form onSubmit={handleGenerate}>
                        <div className="form-grid">
                            <div className="form-group">
                                <label>Grade</label>
                                <select
                                    value={generateForm.grade}
                                    onChange={e => setGenerateForm({ ...generateForm, grade: e.target.value })}
                                >
                                    <option value="Grade 2">Grade 2</option>
                                </select>
                            </div>

                            <div className="form-group">
                                <label>Subject</label>
                                <select
                                    value={generateForm.subject}
                                    onChange={e => setGenerateForm({ ...generateForm, subject: e.target.value })}
                                >
                                    <option value="English">English</option>
                                    <option value="Mathematics">Mathematics</option>
                                </select>
                            </div>

                            <div className="form-group">
                                <label>Lesson Type</label>
                                <select
                                    value={generateForm.lesson_type}
                                    onChange={e => setGenerateForm({ ...generateForm, lesson_type: e.target.value })}
                                >
                                    {currentLessonTypes.map(lt => (
                                        <option key={lt.type} value={lt.type}>{lt.type.replace('_', ' ')}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="form-group">
                                <label>Page Start</label>
                                <input
                                    type="number"
                                    min="1"
                                    value={generateForm.page_start}
                                    onChange={e => setGenerateForm({ ...generateForm, page_start: parseInt(e.target.value) })}
                                    required
                                />
                            </div>

                            <div className="form-group">
                                <label>Page End (optional)</label>
                                <input
                                    type="number"
                                    min={generateForm.page_start}
                                    value={generateForm.page_end || ''}
                                    onChange={e => setGenerateForm({ ...generateForm, page_end: e.target.value ? parseInt(e.target.value) : null })}
                                    placeholder="Same as start"
                                />
                            </div>

                            <div className="form-group">
                                <label>Topic (optional for English)</label>
                                <input
                                    type="text"
                                    value={generateForm.topic}
                                    onChange={e => setGenerateForm({ ...generateForm, topic: e.target.value })}
                                    placeholder="e.g., The Lion and the Mouse"
                                />
                            </div>
                        </div>

                        <div style={{ marginTop: '1.5rem' }}>
                            <button type="submit" className="btn btn-primary" disabled={loading}>
                                {loading ? <><span className="spinner"></span> Generating...</> : '✨ Generate Lesson Plan'}
                            </button>
                        </div>
                    </form>

                    {status && (
                        <div className={`status ${status.type}`}>
                            {status.type === 'loading' && <span className="spinner"></span>}
                            {status.type === 'success' && '✓'}
                            {status.type === 'error' && '✗'}
                            {status.message}
                        </div>
                    )}

                    {lessonPlan && (
                        <div
                            className="lesson-plan"
                            dangerouslySetInnerHTML={{ __html: lessonPlan }}
                        />
                    )}
                </div>
            )}

            {/* Upload Tab */}
            {activeTab === 'upload' && (
                <div className="card">
                    <h2><span className="icon">📤</span> Upload Documents</h2>

                    <div style={{ marginBottom: '1.5rem' }}>
                        <div className="tabs" style={{ width: 'fit-content', margin: 0 }}>
                            <button
                                className={`tab ${uploadType === 'textbook' ? 'active' : ''}`}
                                onClick={() => setUploadType('textbook')}
                            >
                                📖 Textbook
                            </button>
                            <button
                                className={`tab ${uploadType === 'sow' ? 'active' : ''}`}
                                onClick={() => setUploadType('sow')}
                            >
                                📋 SOW
                            </button>
                        </div>
                    </div>

                    <form onSubmit={handleUpload}>
                        <div
                            className={`file-upload ${selectedFile ? 'has-file' : ''}`}
                            onDrop={handleFileDrop}
                            onDragOver={e => e.preventDefault()}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <div className="icon">📁</div>
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

                        <div className="form-grid" style={{ marginTop: '1.5rem' }}>
                            <div className="form-group">
                                <label>Grade</label>
                                <select
                                    value={uploadForm.grade}
                                    onChange={e => setUploadForm({ ...uploadForm, grade: e.target.value })}
                                >
                                    <option value="Grade 2">Grade 2</option>
                                </select>
                            </div>

                            <div className="form-group">
                                <label>Subject</label>
                                <select
                                    value={uploadForm.subject}
                                    onChange={e => setUploadForm({ ...uploadForm, subject: e.target.value })}
                                >
                                    <option value="English">English</option>
                                    <option value="Mathematics">Mathematics</option>
                                </select>
                            </div>

                            {uploadType === 'textbook' ? (
                                <>
                                    <div className="form-group">
                                        <label>Book Type</label>
                                        <select
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
                                    <div className="form-group">
                                        <label>Book Title</label>
                                        <input
                                            type="text"
                                            value={uploadForm.title}
                                            onChange={e => setUploadForm({ ...uploadForm, title: e.target.value })}
                                            placeholder="e.g., Oxford English Grade 2"
                                            required
                                        />
                                    </div>
                                </>
                            ) : (
                                <div className="form-group">
                                    <label>Term</label>
                                    <select
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

                        <div style={{ marginTop: '1.5rem' }}>
                            <button type="submit" className="btn btn-primary" disabled={loading || !selectedFile}>
                                {loading ? <><span className="spinner"></span> Processing...</> : '📤 Upload & Process'}
                            </button>
                        </div>
                    </form>

                    {status && (
                        <div className={`status ${status.type}`}>
                            {status.type === 'loading' && <span className="spinner"></span>}
                            {status.type === 'success' && '✓'}
                            {status.type === 'error' && '✗'}
                            {status.message}
                        </div>
                    )}
                </div>
            )}

            {/* Library Tab */}
            {activeTab === 'library' && (
                <div className="card">
                    <h2><span className="icon">📖</span> Ingested Books</h2>

                    {books.length === 0 ? (
                        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
                            No books ingested yet. Upload a textbook to get started.
                        </p>
                    ) : (
                        <div className="books-list">
                            {books.map(book => (
                                <div key={book.id} className="book-item">
                                    <div className="book-info">
                                        <h3>{book.title}</h3>
                                        <p>{book.grade_level} • {book.subject}</p>
                                    </div>
                                    <div>
                                        <span className="book-badge">{book.book_type}</span>
                                        {book.page_count && (
                                            <span className="book-badge" style={{ marginLeft: '0.5rem' }}>
                                                {book.page_count} pages
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    <div style={{ marginTop: '1.5rem' }}>
                        <button className="btn btn-secondary" onClick={fetchBooks}>
                            🔄 Refresh
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}

export default App
