export type StemAudioStatus = 'idle' | 'loading' | 'playing' | 'error'

export interface StemAudioSnapshot {
  key: string | null
  status: StemAudioStatus
  error: string | null
}

interface AudioLike {
  currentTime: number
  preload: string
  play: () => Promise<void>
  pause: () => void
  addEventListener: (type: string, listener: EventListener) => void
  removeEventListener: (type: string, listener: EventListener) => void
}

interface ActivePlayback {
  key: string
  audio: AudioLike
  detachListeners: () => void
}

type AudioFactory = (src: string) => AudioLike
type SnapshotListener = () => void

const GENERIC_AUDIO_ERROR = 'Audio unavailable. Tap to retry.'

const IDLE_SNAPSHOT: StemAudioSnapshot = {
  key: null,
  status: 'idle',
  error: null,
}

function defaultAudioFactory(src: string): AudioLike {
  const audio = new Audio(src)
  audio.preload = 'auto'
  return audio
}

async function inspectStemAudioRequestFailure(src: string) {
  if (typeof fetch !== 'function') {
    return null
  }

  try {
    const response = await fetch(src, {
      headers: {
        Accept: 'audio/wav, application/json',
      },
    })

    if (response.ok) {
      return null
    }

    const contentType = response.headers.get('content-type') ?? ''
    if (contentType.includes('application/json')) {
      const payload = await response.json().catch(() => null)
      if (payload && typeof payload.detail === 'string' && payload.detail.trim().length > 0) {
        return payload.detail.trim()
      }
    }

    const text = await response.text().catch(() => '')
    if (text.trim().length > 0) {
      return text.trim()
    }

    return `Audio request failed (HTTP ${response.status}).`
  } catch (error) {
    console.error('[stem-audio] Failed to inspect audio request error', { src, error })
    return null
  }
}

export function createStemTextVersion(input: string): string {
  let hash = 5381

  for (let index = 0; index < input.length; index += 1) {
    hash = ((hash << 5) + hash) ^ input.charCodeAt(index)
  }

  return (hash >>> 0).toString(36)
}

export class StemAudioController {
  private active: ActivePlayback | null = null
  private playbackVersion = 0
  private snapshot: StemAudioSnapshot = IDLE_SNAPSHOT
  private readonly listeners = new Set<SnapshotListener>()
  private readonly audioFactory: AudioFactory

  constructor(audioFactory: AudioFactory = defaultAudioFactory) {
    this.audioFactory = audioFactory
  }

  subscribe = (listener: SnapshotListener) => {
    this.listeners.add(listener)

    return () => {
      this.listeners.delete(listener)
    }
  }

  getSnapshot = () => this.snapshot

  start(key: string, src: string) {
    this.stop()
    this.playbackVersion += 1
    const playbackVersion = this.playbackVersion

    const audio = this.audioFactory(src)
    audio.preload = 'auto'

    const onPlaying = () => {
      if (!this.isCurrent(activePlayback)) {
        return
      }

      this.setSnapshot({
        key,
        status: 'playing',
        error: null,
      })
    }

    const onEnded = () => {
      if (!this.isCurrent(activePlayback)) {
        return
      }

      this.finishPlayback(activePlayback)
    }

    const onError = () => {
      if (!this.isCurrent(activePlayback)) {
        return
      }

      this.finishPlaybackWithError(
        activePlayback,
        key,
        src,
        GENERIC_AUDIO_ERROR,
        playbackVersion,
      )
      console.error('[stem-audio] Audio element playback failed', { key, src })
    }

    const activePlayback: ActivePlayback = {
      key,
      audio,
      detachListeners: () => {
        audio.removeEventListener('playing', onPlaying)
        audio.removeEventListener('ended', onEnded)
        audio.removeEventListener('error', onError)
      },
    }

    audio.addEventListener('playing', onPlaying)
    audio.addEventListener('ended', onEnded)
    audio.addEventListener('error', onError)

    this.active = activePlayback
    this.setSnapshot({
      key,
      status: 'loading',
      error: null,
    })

    void audio.play().then(() => {
      if (!this.isCurrent(activePlayback)) {
        return
      }

      if (this.snapshot.status === 'loading') {
        this.setSnapshot({
          key,
          status: 'playing',
          error: null,
        })
      }
    }).catch((error: unknown) => {
      if (!this.isCurrent(activePlayback)) {
        return
      }

      const playbackError = this.describePlaybackError(error)
      const shouldInspectRequest = playbackError !== 'Playback was blocked. Tap to try again.'

      this.finishPlaybackWithError(
        activePlayback,
        key,
        src,
        playbackError,
        playbackVersion,
        shouldInspectRequest,
      )
      if (shouldInspectRequest) {
        console.error('[stem-audio] Playback request failed', { key, src, error })
      }
    })
  }

  stop(key?: string) {
    this.playbackVersion += 1

    if (this.active === null) {
      if (!key || this.snapshot.key === key) {
        this.setSnapshot(IDLE_SNAPSHOT)
      }
      return
    }

    if (key && this.active.key !== key) {
      return
    }

    const activePlayback = this.active
    this.active = null
    activePlayback.detachListeners()

    try {
      activePlayback.audio.pause()
      activePlayback.audio.currentTime = 0
    } catch {
      // Best effort cleanup; UI state still resets even if the browser rejects the reset.
    }

    this.setSnapshot(IDLE_SNAPSHOT)
  }

  stopIfCurrent(key: string) {
    this.stop(key)
  }

  private finishPlayback(activePlayback: ActivePlayback) {
    this.active = null
    activePlayback.detachListeners()
    this.setSnapshot(IDLE_SNAPSHOT)
  }

  private finishPlaybackWithError(
    activePlayback: ActivePlayback,
    key: string,
    src: string,
    error: string,
    playbackVersion: number,
    shouldInspectRequest = true,
  ) {
    this.active = null
    activePlayback.detachListeners()
    this.setSnapshot({
      key,
      status: 'error',
      error,
    })

    if (!shouldInspectRequest) {
      return
    }

    void inspectStemAudioRequestFailure(src).then((detail) => {
      if (!detail) {
        return
      }

      if (this.playbackVersion !== playbackVersion) {
        return
      }

      if (this.snapshot.key !== key || this.snapshot.status !== 'error') {
        return
      }

      this.setSnapshot({
        key,
        status: 'error',
        error: detail,
      })
    })
  }

  private isCurrent(activePlayback: ActivePlayback) {
    return this.active?.audio === activePlayback.audio
  }

  private setSnapshot(snapshot: StemAudioSnapshot) {
    this.snapshot = snapshot
    this.listeners.forEach((listener) => listener())
  }

  private describePlaybackError(error: unknown) {
    if (typeof DOMException !== 'undefined' && error instanceof DOMException && error.name === 'NotAllowedError') {
      return 'Playback was blocked. Tap to try again.'
    }

    return GENERIC_AUDIO_ERROR
  }
}

export const stemAudioController = new StemAudioController()

export function stopStemAudioPlayback(key?: string) {
  stemAudioController.stop(key)
}
