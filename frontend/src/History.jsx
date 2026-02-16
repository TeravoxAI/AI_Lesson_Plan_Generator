import { useState, useEffect } from 'react'

const API_BASE = ''  // Proxied through Vite

// Icons
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

const FileTextIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
    </svg>
)

const EyeIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
    </svg>
)

const CopyIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
)

const XIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" y1="6" x2="6" y2="18" />
        <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
)

const EmptyStateIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="12" y1="18" x2="12" y2="12" />
        <line x1="9" y1="15" x2="15" y2="15" />
    </svg>
)

function History({ session }) {
    const [loading, setLoading] = useState(true)
    const [plans, setPlans] = useState([])
    const [selectedPlan, setSelectedPlan] = useState(null)
    const [showModal, setShowModal] = useState(false)
    const [notification, setNotification] = useState(null)

    useEffect(() => {
        fetchHistory()
    }, [])

    const fetchHistory = async () => {
        setLoading(true)
        try {
            const res = await fetch(`${API_BASE}/generate/history`, {
                headers: {
                    'Authorization': `Bearer ${session?.access_token}`
                }
            })

            if (!res.ok) {
                throw new Error('Failed to fetch history')
            }

            const data = await res.json()
            setPlans(data.plans || [])
        } catch (err) {
            console.error('Error fetching history:', err)
            showNotification('Failed to load history', 'error')
        } finally {
            setLoading(false)
        }
    }

    const formatDate = (dateString) => {
        const date = new Date(dateString)
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    const formatLessonType = (type) => {
        if (!type) return 'N/A'
        return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    }

    const getLessonIdentifier = (plan) => {
        if (plan.subject === 'Mathematics') {
            // For Math: Show unit number and pages
            const pages = []
            if (plan.page_start && plan.page_end) {
                if (plan.page_start === plan.page_end) {
                    pages.push(`Page ${plan.page_start}`)
                } else {
                    pages.push(`Pages ${plan.page_start}-${plan.page_end}`)
                }
            }
            // Parse metadata for additional info
            let metadata = {}
            try {
                if (typeof plan.metadata === 'string') {
                    metadata = JSON.parse(plan.metadata)
                } else {
                    metadata = plan.metadata || {}
                }
            } catch (e) {
                // Ignore parse errors
            }

            return `Unit ${plan.lesson_type || 'N/A'}${pages.length > 0 ? ' • ' + pages.join(', ') : ''}`
        } else {
            // For English: Show lesson number
            return `Lesson ${plan.page_start || 'N/A'}`
        }
    }

    const handleView = (plan) => {
        setSelectedPlan(plan)
        setShowModal(true)
    }

    const handleCopy = (plan) => {
        let contentText = ''

        try {
            // Parse lesson_plan field
            let lessonPlanData = plan.lesson_plan
            if (typeof lessonPlanData === 'string') {
                lessonPlanData = JSON.parse(lessonPlanData)
            }

            // Extract HTML content if it exists
            if (lessonPlanData?.html_content) {
                const temp = document.createElement('div')
                temp.innerHTML = lessonPlanData.html_content
                contentText = temp.textContent || temp.innerText
            } else {
                contentText = JSON.stringify(lessonPlanData, null, 2)
            }
        } catch (e) {
            contentText = 'Unable to extract lesson plan content'
        }

        navigator.clipboard.writeText(contentText)
        showNotification('Copied to clipboard!', 'success')
    }

    const showNotification = (message, type = 'success') => {
        setNotification({ message, type })
        setTimeout(() => setNotification(null), 3000)
    }

    const closeModal = () => {
        setShowModal(false)
        setSelectedPlan(null)
    }

    const getMetadataValue = (plan, key, defaultValue = 'N/A') => {
        try {
            let metadata = plan.metadata
            if (typeof metadata === 'string') {
                metadata = JSON.parse(metadata)
            }
            return metadata?.[key] !== undefined && metadata?.[key] !== null
                ? metadata[key]
                : defaultValue
        } catch (e) {
            return defaultValue
        }
    }

    return (
        <div className="history-container">
            {notification && (
                <div className={`toast-notification ${notification.type}`}>
                    {notification.message}
                </div>
            )}

            <div className="history-header">
                <h1 className="history-title">Your Lesson Plans</h1>
                <p className="history-subtitle">
                    View and manage all your previously generated lesson plans
                </p>
            </div>

            {loading ? (
                <div className="loading-state">
                    <span className="spinner"></span>
                    <p>Loading your lesson plans...</p>
                </div>
            ) : plans.length === 0 ? (
                <div className="empty-state-history">
                    <EmptyStateIcon />
                    <h3>No Lesson Plans Yet</h3>
                    <p>You haven't generated any lesson plans yet. Go to the Generate tab to create your first lesson plan.</p>
                </div>
            ) : (
                <div className="plans-list">
                    {plans.map((plan) => (
                        <div key={plan.id} className="plan-row">
                            <div className="plan-row-left">
                                <div
                                    className={`plan-badge ${plan.subject === 'Mathematics' ? 'badge-math' : 'badge-english'}`}
                                >
                                    {plan.subject}
                                </div>
                                <div className="plan-info-group">
                                    <span className="plan-grade">{plan.grade_level}</span>
                                    <span className="plan-separator">•</span>
                                    <span className="plan-lesson-info">
                                        {formatLessonType(plan.lesson_type)} • {getLessonIdentifier(plan)}
                                    </span>
                                </div>
                            </div>

                            <div className="plan-row-middle">
                                <span className="plan-date-text">{formatDate(plan.created_at)}</span>
                            </div>

                            <div className="plan-row-actions">
                                <button
                                    className="plan-action-btn view-btn"
                                    onClick={() => handleView(plan)}
                                    title="View lesson plan"
                                >
                                    <EyeIcon />
                                    View
                                </button>
                                <button
                                    className="plan-action-btn copy-btn"
                                    onClick={() => handleCopy(plan)}
                                    title="Copy to clipboard"
                                >
                                    <CopyIcon />
                                    Copy
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {showModal && selectedPlan && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <div>
                                <h2 className="modal-title">
                                    {selectedPlan.grade_level} - {selectedPlan.subject}
                                </h2>
                                <p className="modal-subtitle">
                                    {getLessonIdentifier(selectedPlan)} • {formatLessonType(selectedPlan.lesson_type)}
                                </p>
                            </div>
                            <button className="modal-close-btn" onClick={closeModal}>
                                <XIcon />
                            </button>
                        </div>
                        <div className="modal-body">
                            <div
                                className="lesson-plan"
                                dangerouslySetInnerHTML={{
                                    __html: (() => {
                                        try {
                                            let lessonPlanData = selectedPlan.lesson_plan
                                            if (typeof lessonPlanData === 'string') {
                                                lessonPlanData = JSON.parse(lessonPlanData)
                                            }
                                            return lessonPlanData?.html_content || '<p>No content available</p>'
                                        } catch (e) {
                                            return '<p>Unable to display lesson plan content</p>'
                                        }
                                    })()
                                }}
                            />
                        </div>
                        <div className="modal-footer">
                            <button className="modal-action-btn" onClick={() => handleCopy(selectedPlan)}>
                                <CopyIcon />
                                Copy Content
                            </button>
                            <button className="modal-action-btn secondary" onClick={closeModal}>
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <style jsx>{`
                .history-container {
                    padding: 32px 48px;
                    max-width: 1400px;
                    margin: 0 auto;
                }

                .history-header {
                    margin-bottom: 32px;
                }

                .history-title {
                    font-size: 32px;
                    font-weight: 700;
                    color: var(--text-primary);
                    margin: 0 0 8px 0;
                }

                .history-subtitle {
                    font-size: 16px;
                    color: var(--text-secondary);
                    margin: 0;
                }

                .loading-state {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 80px 20px;
                    gap: 16px;
                }

                .loading-state p {
                    color: var(--text-secondary);
                    font-size: 16px;
                }

                .empty-state-history {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 80px 20px;
                    text-align: center;
                    color: var(--text-secondary);
                }

                .empty-state-history svg {
                    opacity: 0.3;
                    margin-bottom: 16px;
                }

                .empty-state-history h3 {
                    font-size: 20px;
                    font-weight: 600;
                    color: var(--text-primary);
                    margin: 0 0 8px 0;
                }

                .empty-state-history p {
                    font-size: 14px;
                    max-width: 400px;
                    margin: 0;
                }

                .plans-list {
                    display: flex;
                    flex-direction: column;
                    gap: 0;
                    background: white;
                    border: 1px solid var(--border);
                    border-radius: 12px;
                    overflow: hidden;
                }

                .plan-row {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 20px 24px;
                    border-bottom: 1px solid var(--border);
                    transition: background-color 0.2s;
                    gap: 20px;
                }

                .plan-row:last-child {
                    border-bottom: none;
                }

                .plan-row:hover {
                    background-color: var(--background-light);
                }

                .plan-row-left {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    flex: 1;
                    min-width: 0;
                }

                .plan-badge {
                    padding: 6px 12px;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: 600;
                    white-space: nowrap;
                    flex-shrink: 0;
                }

                .badge-english {
                    background: var(--primary);
                    color: white;
                }

                .badge-math {
                    background: var(--primary);
                    color: white;
                }

                .plan-info-group {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 14px;
                    color: var(--text-primary);
                    flex-wrap: wrap;
                }

                .plan-grade {
                    font-weight: 600;
                    white-space: nowrap;
                }

                .plan-separator {
                    color: var(--text-secondary);
                }

                .plan-lesson-info {
                    color: var(--text-secondary);
                }

                .plan-row-middle {
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                    gap: 4px;
                    flex-shrink: 0;
                }

                .plan-date-text {
                    font-size: 13px;
                    color: var(--text-secondary);
                    white-space: nowrap;
                }

                .plan-metadata {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 12px;
                    color: var(--text-secondary);
                }

                .metadata-item {
                    white-space: nowrap;
                }

                .metadata-separator {
                    color: var(--border);
                }

                .plan-row-actions {
                    display: flex;
                    gap: 8px;
                    flex-shrink: 0;
                }

                .plan-action-btn {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 6px;
                    padding: 10px 16px;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                }

                .view-btn {
                    background: var(--primary);
                    color: white;
                }

                .view-btn:hover {
                    background: var(--primary-dark);
                }

                .copy-btn {
                    background: var(--background-light);
                    color: var(--text-primary);
                    border: 1px solid var(--border);
                }

                .copy-btn:hover {
                    background: var(--background);
                }

                .modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                    padding: 20px;
                }

                .modal-content {
                    background: white;
                    border-radius: 12px;
                    width: 100%;
                    max-width: 900px;
                    max-height: 90vh;
                    display: flex;
                    flex-direction: column;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                }

                .modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    padding: 24px 28px;
                    border-bottom: 1px solid var(--border);
                }

                .modal-title {
                    font-size: 22px;
                    font-weight: 700;
                    color: var(--text-primary);
                    margin: 0;
                }

                .modal-subtitle {
                    font-size: 14px;
                    color: var(--text-secondary);
                    margin: 4px 0 0 0;
                }

                .modal-close-btn {
                    background: none;
                    border: none;
                    color: var(--text-secondary);
                    cursor: pointer;
                    padding: 4px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 6px;
                    transition: all 0.2s;
                }

                .modal-close-btn:hover {
                    background: var(--background);
                    color: var(--text-primary);
                }

                .modal-body {
                    flex: 1;
                    overflow-y: auto;
                    padding: 28px;
                }


                .modal-footer {
                    display: flex;
                    gap: 12px;
                    padding: 20px 28px;
                    border-top: 1px solid var(--border);
                    justify-content: flex-end;
                }

                .modal-action-btn {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                    background: var(--primary);
                    color: white;
                }

                .modal-action-btn:hover {
                    background: var(--primary-dark);
                }

                .modal-action-btn.secondary {
                    background: var(--background-light);
                    color: var(--text-primary);
                    border: 1px solid var(--border);
                }

                .modal-action-btn.secondary:hover {
                    background: var(--background);
                }

                .toast-notification {
                    position: fixed;
                    top: 24px;
                    right: 24px;
                    padding: 16px 24px;
                    border-radius: 8px;
                    font-weight: 600;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                    z-index: 2000;
                    animation: slideIn 0.3s ease-out;
                }

                .toast-notification.success {
                    background: #10b981;
                    color: white;
                }

                .toast-notification.error {
                    background: #ef4444;
                    color: white;
                }

                @keyframes slideIn {
                    from {
                        transform: translateX(400px);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }

                @media (max-width: 768px) {
                    .history-container {
                        padding: 20px;
                    }

                    .plan-row {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 12px;
                        padding: 16px;
                    }

                    .plan-row-left {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 10px;
                        width: 100%;
                    }

                    .plan-info-group {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 4px;
                    }

                    .plan-separator {
                        display: none;
                    }

                    .plan-row-middle {
                        align-items: flex-start;
                        width: 100%;
                    }

                    .plan-row-actions {
                        width: 100%;
                    }

                    .plan-action-btn {
                        flex: 1;
                    }

                    .modal-content {
                        max-width: 100%;
                        max-height: 95vh;
                    }
                }

                @media (min-width: 769px) and (max-width: 1024px) {
                    .plan-row {
                        flex-wrap: wrap;
                    }

                    .plan-row-middle {
                        order: 3;
                        width: 100%;
                        align-items: flex-start;
                        margin-top: 8px;
                    }

                    .plan-row-actions {
                        margin-left: auto;
                    }
                }
            `}</style>
        </div>
    )
}

export default History
