const BASE_URL = 'http://localhost:5000/api'

export const apiRequest = async (endpoint, method = 'GET', body = null) => {
    const token = localStorage.getItem('token')

    const headers = {}

    if (token) {
        headers['Authorization'] = `Bearer ${token}`
    }

    const config = {
        method,
        headers,
    }

    if (body) {
        headers['Content-type'] = 'application/json'
        config.body = JSON.stringify(body)
    }

    const response = await fetch(`${BASE_URL}${endpoint}`, config)

    if (response.status === 401) {
        localStorage.removeItem('token')
        // window.location.href = '/login'
        throw new Error('The session has ended. Please log in again.')
    }

    const data = await response.json()

    if (!response.ok) {
        throw new Error(data.error || 'Something went wrong.')
    }

    return data
}