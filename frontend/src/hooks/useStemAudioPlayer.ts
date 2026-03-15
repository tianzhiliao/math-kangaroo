import { useEffect, useSyncExternalStore } from 'react'
import {
  createStemTextVersion,
  stemAudioController,
  type StemAudioStatus,
} from '../audio/stemAudioController'
import type { QuestionAudioTarget } from '../lib/questionIdentity'

interface UseStemAudioPlayerOptions {
  audioTarget: QuestionAudioTarget
  stemText: string
}

interface UseStemAudioPlayerResult {
  canPlay: boolean
  error: string | null
  status: StemAudioStatus
  togglePlayback: () => void
}

function buildStemAudioUrl(audioTarget: QuestionAudioTarget, stemText: string) {
  const version = createStemTextVersion(stemText)
  return `/api/tts/exams/${encodeURIComponent(audioTarget.examId)}/questions/${audioTarget.questionId}/stem.wav?v=${version}`
}

export function useStemAudioPlayer({
  audioTarget,
  stemText,
}: UseStemAudioPlayerOptions): UseStemAudioPlayerResult {
  const normalizedStemText = stemText.trim()
  const canPlay = normalizedStemText.length > 0
  const audioKey = audioTarget.playbackKey
  const audioUrl = buildStemAudioUrl(audioTarget, normalizedStemText)
  const snapshot = useSyncExternalStore(
    stemAudioController.subscribe,
    stemAudioController.getSnapshot,
    stemAudioController.getSnapshot,
  )
  const isCurrentAudio = snapshot.key === audioKey
  const status: StemAudioStatus = isCurrentAudio ? snapshot.status : 'idle'
  const error = isCurrentAudio ? snapshot.error : null

  const togglePlayback = () => {
    if (!canPlay) {
      return
    }

    if (status === 'loading' || status === 'playing') {
      stemAudioController.stop(audioKey)
      return
    }

    stemAudioController.start(audioKey, audioUrl)
  }

  useEffect(() => {
    return () => {
      stemAudioController.stopIfCurrent(audioKey)
    }
  }, [audioKey])

  return {
    canPlay,
    error,
    status,
    togglePlayback,
  }
}
