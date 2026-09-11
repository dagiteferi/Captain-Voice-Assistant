const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit & { role?: string } = {},
): Promise<T> {
  const { role, headers, ...restOptions } = options

  const reqHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(headers as Record<string, string>),
  }

  // EXCEPTION: POST /api/v1/knowledge/submissions must NOT send the X-User-Role header
  const isKnowledgeSubmission = endpoint === '/api/v1/knowledge/submissions' && restOptions.method === 'POST'
  
  if (role && !isKnowledgeSubmission) {
    reqHeaders['X-User-Role'] = role
  }

  let response: Response
  try {
    response = await fetch(`${BASE_URL}${endpoint}`, {
      ...restOptions,
      headers: reqHeaders,
    })
  } catch (error) {
    if (import.meta.env.DEV) {
      console.error('Network Error:', error)
    }
    throw new Error('Network Error: Cannot reach backend')
  }

  if (!response.ok) {
    let errorMessage = `HTTP error ${response.status}: ${response.statusText}`
    try {
      const errData = await response.json()
      if (Array.isArray(errData.detail)) {
        errorMessage = errData.detail.map((e: any) => e.msg).join(', ')
      } else if (errData.detail) {
        errorMessage = errData.detail
      }
    } catch {
      // JSON parse failed
    }
    
    if (import.meta.env.DEV) {
      console.error(`API Error [${endpoint}]:`, errorMessage)
    }
    throw new Error(errorMessage)
  }

  return response.json() as Promise<T>
}
