import { useEffect, useState } from 'react'
import {
  loadStemAudioAvailability,
  peekStemAudioAvailability,
  type StemAudioAvailabilityState as ResolvedStemAudioAvailabilityState,
} from './stemAudioAvailabilityStore'

export type StemAudioAvailabilityStatus = 'checking' | 'available' | 'unavailable'

interface StemAudioAvailabilityState {
  status: StemAudioAvailabilityStatus
  message: string | null
}

const AUDIO_UNAVAILABLE_MESSAGE = 'Question audio is unavailable in this environment.'

function normalizeUnavailableMessage(detail: unknown) {
  if (typeof detail !== 'string' || detail.trim().length === 0) {
    return AUDIO_UNAVAILABLE_MESSAGE
  }

  if (detail.includes('OPENAI_API_KEY')) {
    return AUDIO_UNAVAILABLE_MESSAGE
  }

  return detail
}

export async function fetchStemAudioAvailability(
  fetcher: typeof fetch = fetch,
): Promise<ResolvedStemAudioAvailabilityState> {
  try {
    const response = await fetcher('/api/health', {
      headers: {
        Accept: 'application/json',
      },
    })
    const payload = await response.json().catch(() => null)

    if (response.ok && payload?.status === 'ok') {
      return {
        status: 'available',
        message: null,
      }
    }

    return {
      status: 'unavailable',
      message: normalizeUnavailableMessage(payload?.detail),
    }
  } catch {
    return {
      status: 'unavailable',
      message: AUDIO_UNAVAILABLE_MESSAGE,
    }
  }
}

export function useStemAudioAvailability(): StemAudioAvailabilityState {
  const [state, setState] = useState<StemAudioAvailabilityState>(
    peekStemAudioAvailability() ?? {
      status: 'checking',
      message: null,
    },
  )

  useEffect(() => {
    let isCancelled = false

    void loadStemAudioAvailability(() => fetchStemAudioAvailability()).then((result) => {
      if (!isCancelled) {
        setState(result)
      }
    })

    return () => {
      isCancelled = true
    }
  }, [])

  return state
}
