import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface Settings {
  autoPlayVoice: boolean
  textSize: 'normal' | 'large' | 'xl'
  defaultLanguage: 'am' | 'en' | 'fr'
}

const DEFAULT_SETTINGS: Settings = {
  autoPlayVoice: true,
  textSize: 'normal',
  defaultLanguage: 'am',
}

interface SettingsContextType {
  settings: Settings
  updateSetting: <K extends keyof Settings>(key: K, value: Settings[K]) => void
  resetSettings: () => void
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(() => {
    try {
      const stored = localStorage.getItem('captain-settings')
      if (stored) {
        return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) }
      }
    } catch (e) {
      console.error('Failed to load settings from localStorage', e)
    }
    return DEFAULT_SETTINGS
  })

  useEffect(() => {
    try {
      localStorage.setItem('captain-settings', JSON.stringify(settings))
    } catch (e) {
      console.error('Failed to save settings to localStorage', e)
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
