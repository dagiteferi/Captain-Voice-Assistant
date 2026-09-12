import { useState, useEffect } from 'react'

export function useAudioBlob(audioUrl?: string | null) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!audioUrl) {
      setBlobUrl(null)
      return
    }

    let isMounted = true
    let currentObjectUrl: string | null = null

    setIsLoading(true)
    setError(null)

    const fetchBlob = async () => {
      try {
        // Use relative URL so Vite proxy handles routing to backend
        const fullUrl = audioUrl.startsWith('http') ? audioUrl : audioUrl
        const res = await fetch(fullUrl)
        if (!res.ok) throw new Error(`Failed to fetch audio (${res.status})`)
        const blob = await res.blob()
        if (isMounted) {
          currentObjectUrl = URL.createObjectURL(blob)
          setBlobUrl(currentObjectUrl)
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error('Unknown error'))
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    fetchBlob()

    return () => {
      isMounted = false
      if (currentObjectUrl) {
        URL.revokeObjectURL(currentObjectUrl)
      }
    }
  }, [audioUrl])

  return { blobUrl, isLoading, error }
}
