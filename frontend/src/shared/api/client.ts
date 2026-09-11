const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit & { role?: string } = {},
): Promise<T> {
  const { role = 'captain', headers, ...restOptions } = options

  const reqHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-User-Role': role,
    ...(headers as Record<string, string>),
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...restOptions,
    headers: reqHeaders,
  })

  if (!response.ok) {
    let errorMessage = `HTTP error ${response.status}: ${response.statusText}`
    try {
      const errData = await response.json()
      if (errData.detail) errorMessage = errData.detail
    } catch {
      // JSON parse failed
    }
    throw new Error(errorMessage)
  }

  return response.json() as Promise<T>
}
