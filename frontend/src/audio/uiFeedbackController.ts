export type UIFeedbackKind = 'nav' | 'primary' | 'utility' | 'danger'

interface FeedbackNote {
  frequency: number
  duration: number
  gain: number
  type: OscillatorType
  delay?: number
}

const FEEDBACK_PATTERNS: Record<UIFeedbackKind, FeedbackNote[]> = {
  nav: [
    { frequency: 660, duration: 0.045, gain: 0.016, type: 'triangle' },
    { frequency: 820, duration: 0.05, gain: 0.012, type: 'triangle', delay: 0.03 },
  ],
  primary: [
    { frequency: 520, duration: 0.05, gain: 0.02, type: 'sine' },
    { frequency: 760, duration: 0.09, gain: 0.024, type: 'triangle', delay: 0.028 },
  ],
  utility: [{ frequency: 480, duration: 0.05, gain: 0.014, type: 'sine' }],
  danger: [
    { frequency: 260, duration: 0.07, gain: 0.018, type: 'square' },
    { frequency: 210, duration: 0.09, gain: 0.012, type: 'triangle', delay: 0.035 },
  ],
}

export class UIFeedbackController {
  private audioContext: AudioContext | null = null

  private getAudioContext() {
    if (typeof window === 'undefined') {
      return null
    }

    const AudioContextClass = window.AudioContext
    if (!AudioContextClass) {
      return null
    }

    if (!this.audioContext) {
      this.audioContext = new AudioContextClass()
    }

    return this.audioContext
  }

  play(kind: UIFeedbackKind) {
    const audioContext = this.getAudioContext()
    if (!audioContext) {
      return
    }

    const now = audioContext.currentTime
    const notes = FEEDBACK_PATTERNS[kind]

    notes.forEach((note) => {
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()
      const noteStart = now + (note.delay ?? 0)
      const noteEnd = noteStart + note.duration

      oscillator.type = note.type
      oscillator.frequency.setValueAtTime(note.frequency, noteStart)

      gainNode.gain.setValueAtTime(0.0001, noteStart)
      gainNode.gain.exponentialRampToValueAtTime(note.gain, noteStart + 0.01)
      gainNode.gain.exponentialRampToValueAtTime(0.0001, noteEnd)

      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)
      oscillator.start(noteStart)
      oscillator.stop(noteEnd)
    })
  }
}

export const uiFeedbackController = new UIFeedbackController()
