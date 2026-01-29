import { useState } from 'react'
import './index.css'

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
                // Auto login or ask to login?
                // Typically auto-login or show success message.
                // For this implementation, let's call success callback (could be auto login)
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
        <div className="main-content" style={{ justifyContent: 'center', alignItems: 'flex-start', paddingTop: '48px', minHeight: 'calc(100vh - 72px)' }}>
            <div className="form-panel" style={{ width: '600px', margin: '0 auto' }}>
                <h1 className="panel-title">Create Account</h1>
                <p className="panel-subtitle">Join us to start generating lesson plans</p>

                <form onSubmit={handleSubmit}>
                    <div style={{ display: 'flex', gap: '20px' }}>
                        <div className="form-field" style={{ flex: 1 }}>
                            <label className="form-label">First Name</label>
                            <input
                                type="text"
                                name="first_name"
                                className="form-input"
                                value={formData.first_name}
                                onChange={handleChange}
                                placeholder="First Name"
                                required
                            />
                        </div>
                        <div className="form-field" style={{ flex: 1 }}>
                            <label className="form-label">Last Name</label>
                            <input
                                type="text"
                                name="last_name"
                                className="form-input"
                                value={formData.last_name}
                                onChange={handleChange}
                                placeholder="Last Name"
                                required
                            />
                        </div>
                    </div>

                    <div className="form-field">
                        <label className="form-label">Email Address</label>
                        <input
                            type="email"
                            name="email"
                            className="form-input"
                            value={formData.email}
                            onChange={handleChange}
                            placeholder="name@school.edu"
                            required
                        />
                    </div>

                    <div className="form-field">
                        <label className="form-label">Password</label>
                        <input
                            type="password"
                            name="password"
                            className="form-input"
                            value={formData.password}
                            onChange={handleChange}
                            placeholder="Create a strong password"
                            required
                            minLength={6}
                        />
                    </div>

                    <div style={{ display: 'flex', gap: '20px' }}>
                        <div className="form-field" style={{ flex: 1 }}>
                            <label className="form-label">Role</label>
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
                        <div className="form-field" style={{ flex: 1 }}>
                            <label className="form-label">School Branch</label>
                            <input
                                type="text"
                                name="school_branch"
                                className="form-input"
                                value={formData.school_branch}
                                onChange={handleChange}
                                placeholder="e.g. Downtown Campus"
                                required
                            />
                        </div>
                    </div>

                    {formData.role === 'teacher' && (
                        <div style={{ display: 'flex', gap: '20px' }}>
                            <div className="form-field" style={{ flex: 1 }}>
                                <label className="form-label">Primary Grade</label>
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
                            <div className="form-field" style={{ flex: 1 }}>
                                <label className="form-label">Primary Subject</label>
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
                    )}

                    {error && (
                        <div className="status error" style={{ marginBottom: '20px' }}>
                            {error}
                        </div>
                    )}

                    <button type="submit" className="generate-btn" disabled={loading}>
                        {loading ? (
                            <>
                                <span className="spinner"></span>
                                Creating Account...
                            </>
                        ) : (
                            'Sign Up'
                        )}
                    </button>

                    <div style={{ marginTop: '24px', textAlign: 'center', fontSize: '14px', color: 'var(--text-secondary)' }}>
                        Already have an account?{' '}
                        <button
                            type="button"
                            onClick={onSwitchToLogin}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: 'var(--primary)',
                                fontWeight: '600',
                                cursor: 'pointer',
                                textDecoration: 'underline'
                            }}
                        >
                            Log In
                        </button>
                    </div>
                </form>
            </div>
        </div>
    )
}

export default Signup
