import { Settings, SlidersHorizontal, Volume2, Type, Globe, Trash2 } from 'lucide-react'
import { PageShell } from '@/pages/ConsolePage'
import { useSettings } from '@/shared/lib/useSettings'

export function SettingsPage() {
  const { settings, updateSetting, resetSettings } = useSettings()

  return (
    <PageShell icon={Settings} title="Settings" label="PREFERENCES & CONFIGURATION">
      <div className="max-w-2xl mx-auto space-y-6">
        
        {/* Voice Settings */}
        <div className="bg-base-900 border border-border rounded-lg overflow-hidden shadow-sm">
          <div className="px-5 py-4 border-b border-border bg-base-800 flex items-center gap-2">
            <Volume2 className="h-4 w-4 text-sky" />
            <h2 className="text-sm font-semibold text-text-primary">Voice Settings</h2>
          </div>
          <div className="p-5 space-y-4">
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
                onChange={(e) => updateSetting('defaultLanguage', e.target.value as 'am' | 'en' | 'fr')}
                className="bg-base-800 border border-border rounded px-3 py-1.5 text-sm text-text-primary outline-none focus:border-amber"
              >
                <option value="am">Amharic (አማርኛ)</option>
                <option value="en">English</option>
                <option value="fr">French</option>
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
