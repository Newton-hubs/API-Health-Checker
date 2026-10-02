const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

async function request(path, options) {
  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, options)
  } catch {
    // fetch only rejects on network-level failures (server down, CORS block, ...)
    throw new Error('Cannot reach the server. Is the backend running?')
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') {
        message = body.detail
      } else if (response.status === 422) {
        message = 'Please enter a valid http:// or https:// URL.'
      }
    } catch {
      // body was not JSON; keep the generic message
    }
    throw new Error(message)
  }

  return response.json()
}

export function checkUrl(url) {
  return request('/api/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
}

export function getChecks(pageSize = 10) {
  return request(`/api/checks?page_size=${pageSize}`)
}

export function getStats() {
  return request('/api/stats')
}
