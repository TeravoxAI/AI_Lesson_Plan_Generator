import { useState } from 'react'
import './index.css'

const BookOpenIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
    </svg>
)

const EyeOffIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/>
        <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/>
        <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/>
        <line x1="2" x2="22" y1="2" y2="22"/>
    </svg>
)

const EyeIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
        <circle cx="12" cy="12" r="3"/>
    </svg>
)

const ChevronDownIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m6 9 6 6 6-6"/>
    </svg>
)

const Signup = ({ onSignupSuccess, onSwitchToLogin }) => {
    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        grade: 'Grade 2',
        subject: 'English',
        school_branch: '',
        role: 'teacher',
        email: '',
        password: ''
    })
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [showPassword, setShowPassword] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        setError(null)

        try {
            const response = await fetch('/authentication/signup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            })

            const data = await response.json()

            if (data.success) {
                onSignupSuccess(data.user, data.session)
            } else {
                setError(data.message || 'Signup failed')
            }
        } catch (err) {
            setError('An error occurred. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        })
    }

    return (
        <div className="auth-container">
            {/* Left Branded Panel */}
            <div className="auth-brand-panel auth-brand-panel-narrow">
                <div className="auth-brand-content">
                    <div className="auth-brand-icon">
                        <BookOpenIcon />
                    </div>
                    <h1 className="auth-brand-title">Lesson Plan Generator</h1>
                    <p className="auth-brand-subtitle">
                        Join thousands of educators creating better lesson plans
                    </p>
                </div>
            </div>

            {/* Right Form Panel */}
            <div className="auth-form-panel">
                <div className="auth-form-container auth-form-container-wide">
                    <div className="auth-form-header">
                        <h2 className="auth-form-title">Create Account</h2>
                        <p className="auth-form-subtitle">Fill in your details to get started</p>
                    </div>

                    <form onSubmit={handleSubmit} className="auth-form">
                        <div className="form-row">
                            <div className="form-field">
                                <label className="form-label">First Name</label>
                                <input
                                    type="text"
                                    name="first_name"
                                    className="form-input"
                                    value={formData.first_name}
                                    onChange={handleChange}
                                    placeholder="First name"
                                    required
                                />
                            </div>
                            <div className="form-field">
                                <label className="form-label">Last Name</label>
                                <input
                                    type="text"
                                    name="last_name"
                                    className="form-input"
                                    value={formData.last_name}
                                    onChange={handleChange}
                                    placeholder="Last name"
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-field">
                            <label className="form-label">Email</label>
                            <input
                                type="email"
                                name="email"
                                className="form-input"
                                value={formData.email}
                                onChange={handleChange}
                                placeholder="Enter your email"
                                required
                            />
                        </div>

                        <div className="form-field">
                            <label className="form-label">Password</label>
                            <div className="password-input-wrapper">
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    name="password"
                                    className="form-input"
                                    value={formData.password}
                                    onChange={handleChange}
                                    placeholder="Create a password"
                                    required
                                    minLength={6}
                                />
                                <button
                                    type="button"
                                    className="password-toggle"
                                    onClick={() => setShowPassword(!showPassword)}
                                    tabIndex={-1}
                                >
                                    {showPassword ? <EyeIcon /> : <EyeOffIcon />}
                                </button>
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-field">
                                <label className="form-label">Role</label>
                                <div className="select-wrapper">
                                    <select
                                        name="role"
                                        className="form-select"
                                        value={formData.role}
                                        onChange={handleChange}
                                    >
                                        <option value="teacher">Teacher</option>
                                        <option value="principal">Principal</option>
                                    </select>
                                </div>
                            </div>
                            <div className="form-field">
                                <label className="form-label">School Branch</label>
                                <input
                                    type="text"
                                    name="school_branch"
                                    className="form-input"
                                    value={formData.school_branch}
                                    onChange={handleChange}
                                    placeholder="School branch"
                                    required
                                />
                            </div>
                        </div>

                        {formData.role === 'teacher' && (
                            <div className="form-row">
                                <div className="form-field">
                                    <label className="form-label">Grade</label>
                                    <div className="select-wrapper">
                                        <select
                                            name="grade"
                                            className="form-select"
                                            value={formData.grade}
                                            onChange={handleChange}
                                        >
                                            <option value="Grade 1">Grade 1</option>
                                            <option value="Grade 2">Grade 2</option>
                                            <option value="Grade 3">Grade 3</option>
                                            <option value="Grade 4">Grade 4</option>
                                            <option value="Grade 5">Grade 5</option>
                                            <option value="Grade 6">Grade 6</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="form-field">
                                    <label className="form-label">Subject</label>
                                    <div className="select-wrapper">
                                        <select
                                            name="subject"
                                            className="form-select"
                                            value={formData.subject}
                                            onChange={handleChange}
                                        >
                                            <option value="English">English</option>
                                            <option value="Mathematics">Mathematics</option>
                                            <option value="Science">Science</option>
                                            <option value="History">History</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="status error">
                                {error}
                            </div>
                        )}

                        <button type="submit" className="auth-submit-btn" disabled={loading}>
                            {loading ? (
                                <>
                                    <span className="spinner"></span>
                                    Creating Account...
                                </>
                            ) : (
                                'Create Account'
                            )}
                        </button>

                        <div className="auth-switch-prompt">
                            Already have an account?{' '}
                            <button
                                type="button"
                                onClick={onSwitchToLogin}
                                className="auth-switch-link"
                            >
                                Sign In
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    )
}

export default Signup
