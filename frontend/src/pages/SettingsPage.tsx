import { useState, useRef } from 'react'
import { Settings, Volume2, Type, Globe, Trash2, Play, Square, Loader2, CheckCircle2 } from 'lucide-react'
import { PageShell } from '@/pages/ConsolePage'
import { useSettings } from '@/shared/lib/useSettings'

// Available Edge TTS voice options grouped by language
const VOICE_OPTIONS: { label: string; value: string; lang: 'en' | 'am'; description: string }[] = [
  // Amharic voices
  { label: 'Mekdes (Female)', value: 'am-ET-MekdesNeural', lang: 'am', description: 'Natural Amharic female voice' },
  { label: 'Ameha (Male)', value: 'am-ET-AmehaNeural', lang: 'am', description: 'Natural Amharic male voice' },
  // English voices
  { label: 'Christopher (Male, US)', value: 'en-US-ChristopherNeural', lang: 'en', description: 'Deep, authoritative male voice' },
  { label: 'Jenny (Female, US)', value: 'en-US-JennyNeural', lang: 'en', description: 'Friendly, professional female voice' },
  { label: 'Guy (Male, US)', value: 'en-US-GuyNeural', lang: 'en', description: 'Casual, clear male voice' },
  { label: 'Aria (Female, US)', value: 'en-US-AriaNeural', lang: 'en', description: 'Expressive, versatile female voice' },
  { label: 'Ryan (Male, UK)', value: 'en-GB-RyanNeural', lang: 'en', description: 'British professional male voice' },
  { label: 'Sonia (Female, UK)', value: 'en-GB-SoniaNeural', lang: 'en', description: 'British professional female voice' },
]

// Determine which preview text to use
function getPreviewText(voiceValue: string, lang: 'am' | 'en'): { text: string; language: string } {
  if (lang === 'am' || voiceValue.startsWith('am-')) {
    return { text: 'ይህ የድምፅ ቅምሻ ነው። ድምፄን ሰምተው ይምረጡ።', language: 'am' }
  }
  return { text: 'This is a voice preview. Please listen and select if you like it.', language: 'en' }
}

function VoicePreviewButton({ voiceId, lang }: { voiceId: string; lang: 'am' | 'en' }) {
  const [state, setState] = useState<'idle' | 'loading' | 'playing' | 'done'>('idle')
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const handlePreview = async () => {
    if (state === 'loading') return

    // Stop if currently playing
    if (state === 'playing' && audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      setState('idle')
      return
    }

    setState('loading')
    const { language } = getPreviewText(voiceId, lang)
    try {
      const res = await fetch(`/api/v1/audio/preview?voice_id=${encodeURIComponent(voiceId)}&language=${language}`)
      if (!res.ok) throw new Error('Preview failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => {
        setState('done')
        URL.revokeObjectURL(url)
        setTimeout(() => setState('idle'), 1500)
      }
      audio.onerror = () => setState('idle')
      setState('playing')
      await audio.play()
    } catch {
      setState('idle')
    }
  }

  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        void handlePreview()
      }}
      title={state === 'playing' ? 'Stop preview' : 'Preview this voice'}
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border transition-all ${
        state === 'playing'
          ? 'bg-rose/10 border-rose/40 text-rose'
          : state === 'done'
          ? 'bg-emerald/10 border-emerald/30 text-emerald'
          : 'bg-sky/10 border-sky/30 text-sky hover:bg-sky/20'
      }`}
    >
      {state === 'loading' ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : state === 'playing' ? (
        <Square className="h-3 w-3 fill-current" />
      ) : state === 'done' ? (
        <CheckCircle2 className="h-3 w-3" />
      ) : (
        <Play className="h-3 w-3 fill-current" />
      )}
      {state === 'loading' ? 'Loading…' : state === 'playing' ? 'Stop' : state === 'done' ? 'Liked?' : 'Preview'}
    </button>
  )
}

export function SettingsPage() {
  const { settings, updateSetting, resetSettings } = useSettings()

  const amharicVoices = VOICE_OPTIONS.filter((v) => v.lang === 'am')
  const englishVoices = VOICE_OPTIONS.filter((v) => v.lang === 'en')

  const selectedAm = VOICE_OPTIONS.find((v) => v.value === settings.voiceIdAm)
  const selectedEn = VOICE_OPTIONS.find((v) => v.value === settings.voiceIdEn)

  return (
    <PageShell icon={Settings} title="Settings" label="PREFERENCES & CONFIGURATION">
      <div className="max-w-2xl mx-auto space-y-6">

        {/* Voice Settings */}
        <div className="bg-base-900 border border-border rounded-lg overflow-hidden shadow-sm">
          <div className="px-5 py-4 border-b border-border bg-base-800 flex items-center gap-2">
            <Volume2 className="h-4 w-4 text-sky" />
            <h2 className="text-sm font-semibold text-text-primary">Voice Settings</h2>
          </div>
          <div className="p-5 space-y-5">

            {/* Auto-play toggle */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-text-primary">Auto-play Voice Response</label>
                <p className="text-xs text-text-muted mt-1">Automatically play synthesized audio when the command is complete.</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={settings.autoPlayVoice}
                  onChange={(e) => updateSetting('autoPlayVoice', e.target.checked)}
                />
                <div className="w-9 h-5 bg-base-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-text-primary after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-amber"></div>
              </label>
            </div>

            {/* Voice selection — Amharic */}
            <div>
              <label className="text-sm font-medium text-text-primary block mb-2">
                Amharic Voice
              </label>
              <div className="space-y-2">
                {amharicVoices.map((voice) => {
                  const isSelected = settings.voiceIdAm === voice.value
                  return (
                    <div
                      key={voice.value}
                      onClick={() => updateSetting('voiceIdAm', voice.value)}
                      className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-amber/10 border-amber/50 shadow-sm'
                          : 'bg-base-800 border-border hover:border-border-hover hover:bg-base-750'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-4 h-4 rounded-full border-2 flex-shrink-0 ${
                          isSelected ? 'border-amber bg-amber' : 'border-base-500'
                        }`}>
                          {isSelected && <div className="w-full h-full rounded-full bg-base-900 scale-[0.4]" />}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-text-primary">{voice.label}</p>
                          <p className="text-xs text-text-muted">{voice.description}</p>
                        </div>
                      </div>
                      <VoicePreviewButton voiceId={voice.value} lang={voice.lang} />
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Voice selection — English */}
            <div>
              <label className="text-sm font-medium text-text-primary block mb-2">
                English Voice
              </label>
              <div className="space-y-2">
                {englishVoices.map((voice) => {
                  const isSelected = settings.voiceIdEn === voice.value
                  return (
                    <div
                      key={voice.value}
                      onClick={() => updateSetting('voiceIdEn', voice.value)}
                      className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-amber/10 border-amber/50 shadow-sm'
                          : 'bg-base-800 border-border hover:border-border-hover hover:bg-base-750'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-4 h-4 rounded-full border-2 flex-shrink-0 ${
                          isSelected ? 'border-amber bg-amber' : 'border-base-500'
                        }`}>
                          {isSelected && <div className="w-full h-full rounded-full bg-base-900 scale-[0.4]" />}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-text-primary">{voice.label}</p>
                          <p className="text-xs text-text-muted">{voice.description}</p>
                        </div>
                      </div>
                      <VoicePreviewButton voiceId={voice.value} lang={voice.lang} />
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="flex items-start gap-2 p-3 bg-amber/5 border border-amber/20 rounded-lg">
              <CheckCircle2 className="h-4 w-4 text-amber flex-shrink-0 mt-0.5" />
              <p className="text-xs text-text-secondary">
                Chat uses <span className="font-semibold text-amber">{selectedAm?.label ?? settings.voiceIdAm}</span> for Amharic
                and <span className="font-semibold text-amber">{selectedEn?.label ?? settings.voiceIdEn}</span> for English.
                Changing a voice re-speaks existing replies in that language.
              </p>
            </div>
          </div>
        </div>

        {/* Display Settings */}
        <div className="bg-base-900 border border-border rounded-lg overflow-hidden shadow-sm">
          <div className="px-5 py-4 border-b border-border bg-base-800 flex items-center gap-2">
            <Type className="h-4 w-4 text-emerald" />
            <h2 className="text-sm font-semibold text-text-primary">Display Settings</h2>
          </div>
          <div className="p-5 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-text-primary">Chat Text Size</label>
                <p className="text-xs text-text-muted mt-1">Adjust the font size of the command console messages.</p>
              </div>
              <select
                value={settings.textSize}
                onChange={(e) => updateSetting('textSize', e.target.value as 'normal' | 'large' | 'xl')}
                className="bg-base-800 border border-border rounded px-3 py-1.5 text-sm text-text-primary outline-none focus:border-amber"
              >
                <option value="normal">Normal</option>
                <option value="large">Large</option>
                <option value="xl">Extra Large</option>
              </select>
            </div>
          </div>
        </div>

        {/* Defaults */}
        <div className="bg-base-900 border border-border rounded-lg overflow-hidden shadow-sm">
          <div className="px-5 py-4 border-b border-border bg-base-800 flex items-center gap-2">
            <Globe className="h-4 w-4 text-amber" />
            <h2 className="text-sm font-semibold text-text-primary">Defaults</h2>
          </div>
          <div className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-text-primary">Target Language</label>
                <p className="text-xs text-text-muted mt-1">Default language for translation and voice synthesis.</p>
              </div>
              <select
                value={settings.defaultLanguage}
                onChange={(e) => updateSetting('defaultLanguage', e.target.value as 'am' | 'en')}
                className="bg-base-800 border border-border rounded px-3 py-1.5 text-sm text-text-primary outline-none focus:border-amber"
              >
                <option value="am">Amharic (አማርኛ)</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>
        </div>

        {/* Reset */}
        <div className="flex justify-end pt-4 border-t border-border-subtle">
          <button
            onClick={resetSettings}
            className="flex items-center gap-2 text-sm text-text-muted hover:text-rose transition-colors py-2 px-4 rounded hover:bg-rose/10"
          >
            <Trash2 className="h-4 w-4" />
            Reset to Default Settings
          </button>
        </div>

      </div>
    </PageShell>
  )
}
