import { useState, useRef, useEffect } from 'react'
import { Play, Pause, Download, Volume2, VolumeX, Music } from 'lucide-react'
import { cn } from '@/shared/lib/cn'

interface AudioPlayerProps {
  audioUrl?: string | null
  title?: string
  className?: string
}

export function AudioPlayer({ audioUrl, title = 'Audio Response', className }: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isMuted, setIsMuted] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    setIsPlaying(false)
    setCurrentTime(0)
    setDuration(0)
  }, [audioUrl])

  if (!audioUrl) {
    return (
      <div className="flex items-center gap-2 p-2.5 rounded border border-border-subtle bg-base-800/50 text-text-muted text-xs">
        <Music className="h-3.5 w-3.5" />
        <span>No audio response synthesized</span>
      </div>
    )
  }

  const togglePlay = () => {
    if (!audioRef.current) return
    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play().catch(() => {
        // Handle playback fallback
      })
    }
    setIsPlaying(!isPlaying)
  }

  const toggleMute = () => {
    if (!audioRef.current) return
    audioRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = Math.floor(secs % 60)
    return `${m}:${s < 10 ? '0' : ''}${s}`
  }

  return (
    <div
      className={cn(
        'panel p-3 bg-base-800/90 border border-border flex flex-col sm:flex-row sm:items-center gap-3',
        className,
      )}
    >
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={() => setCurrentTime(audioRef.current?.currentTime || 0)}
        onLoadedMetadata={() => setDuration(audioRef.current?.duration || 0)}
        onEnded={() => setIsPlaying(false)}
      />

      <div className="flex items-center gap-2">
        <button
          onClick={togglePlay}
          className="w-8 h-8 rounded-full bg-amber text-base-900 flex items-center justify-center hover:bg-amber-light transition-all flex-shrink-0"
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? (
            <Pause className="h-4 w-4 fill-current" />
          ) : (
            <Play className="h-4 w-4 fill-current ml-0.5" />
          )}
        </button>

        <div className="flex flex-col">
          <span className="text-xs font-semibold text-text-primary tracking-tight">
            {title}
          </span>
          <span className="mono text-[10px] text-text-secondary">
            {formatTime(currentTime)} / {formatTime(duration || 12)}
          </span>
        </div>
      </div>

      {/* Waveform / Progress bar */}
      <div className="flex-1 flex items-center gap-2">
        <input
          type="range"
          min={0}
          max={duration || 100}
          value={currentTime}
          onChange={(e) => {
            const val = Number(e.target.value)
            setCurrentTime(val)
            if (audioRef.current) audioRef.current.currentTime = val
          }}
          className="w-full accent-amber h-1 bg-base-700 rounded cursor-pointer"
        />
      </div>

      {/* Volume & Download */}
      <div className="flex items-center gap-2 self-end sm:self-center">
        <button
          onClick={toggleMute}
          className="p-1.5 text-text-secondary hover:text-text-primary transition-colors"
          title={isMuted ? 'Unmute' : 'Mute'}
        >
          {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
        </button>

        <a
          href={audioUrl}
          download="captain-voice-response.mp3"
          className="p-1.5 text-text-secondary hover:text-amber transition-colors"
          title="Download Audio File"
        >
          <Download className="h-4 w-4" />
        </a>
      </div>
    </div>
  )
}
