import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface Settings {
  autoPlayVoice: boolean
  textSize: 'normal' | 'large' | 'xl'
  defaultLanguage: 'am' | 'en'
  voiceIdAm: string
  voiceIdEn: string
}

const DEFAULT_SETTINGS: Settings = {
  autoPlayVoice: true,
  textSize: 'normal',
  defaultLanguage: 'am',
  voiceIdAm: 'am-ET-MekdesNeural',
  voiceIdEn: 'en-US-ChristopherNeural',
}

export function voiceForLanguage(settings: Settings, language: string): string {
  return language === 'am' ? settings.voiceIdAm : settings.voiceIdEn
}

interface SettingsContextType {
  settings: Settings
  updateSetting: <K extends keyof Settings>(key: K, value: Settings[K]) => void
  resetSettings: () => void
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

function loadSettings(): Settings {
  try {
    const stored = localStorage.getItem('captain-settings')
    if (!stored) return DEFAULT_SETTINGS
    const parsed = JSON.parse(stored) as Partial<Settings> & { voiceId?: string | null }
    const next = { ...DEFAULT_SETTINGS, ...parsed }
    if (!parsed.voiceIdAm && parsed.voiceId?.startsWith('am-')) {
      next.voiceIdAm = parsed.voiceId
    }
    if (!parsed.voiceIdEn && parsed.voiceId && !parsed.voiceId.startsWith('am-')) {
      next.voiceIdEn = parsed.voiceId
    }
    return next
  } catch {
    return DEFAULT_SETTINGS
  }
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(loadSettings)

  useEffect(() => {
    try {
      localStorage.setItem('captain-settings', JSON.stringify(settings))
    } catch {
      /* ignore quota */
    }
  }, [settings])

  const updateSetting = <K extends keyof Settings>(key: K, value: Settings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
  }

  const resetSettings = () => setSettings(DEFAULT_SETTINGS)

  return (
    <SettingsContext.Provider value={{ settings, updateSetting, resetSettings }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider')
  }
  return context
}
