import { useState, useEffect } from 'react'

const API_BASE = ''  // Proxied through Vite

const UsageIndicator = ({ session }) => {
    const [usage, setUsage] = useState(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        if (session?.access_token) {
            fetchUsage()
        }
    }, [session])

    const fetchUsage = async () => {
        try {
            const response = await fetch(`${API_BASE}/generate/weekly-usage`, {
                headers: {
                    'Authorization': `Bearer ${session?.access_token}`
                }
            })

            if (response.ok) {
                const data = await response.json()
                setUsage(data)
            }
        } catch (error) {
            console.error('Failed to fetch usage:', error)
        } finally {
            setLoading(false)
        }
    }

    if (loading || !usage) return null

    // Determine color based on usage percentage
    const getColor = () => {
        if (usage.percentage < 50) return '#10B981'  // Green
        if (usage.percentage < 90) return '#F59E0B'  // Orange
        return '#EF4444'  // Red
    }

    const color = getColor()
    const progressWidth = `${usage.percentage}%`

    return (
        <div className="usage-indicator">
            <div className="usage-header">
                <div className="usage-icon" style={{ backgroundColor: color }}></div>
                <span className="usage-title">Weekly Usage</span>
                <span className="usage-count" style={{ color: color }}>
                    {usage.used}/{usage.limit}
                </span>
            </div>
            <div className="usage-progress-bg">
                <div
                    className="usage-progress-fill"
                    style={{ width: progressWidth, backgroundColor: color }}
                ></div>
            </div>
            <p className="usage-subtitle">
                {usage.remaining} lesson plan{usage.remaining !== 1 ? 's' : ''} remaining this week
            </p>
        </div>
    )
}

export default UsageIndicator
