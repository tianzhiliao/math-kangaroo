/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useState } from 'react'

export type StemAudioAvailabilityStatus = 'checking' | 'available' | 'unavailable'

interface StemAudioAvailabilityState {
  status: StemAudioAvailabilityStatus
  message: string | null
}

const AUDIO_UNAVAILABLE_MESSAGE = 'Question audio is unavailable in this environment.'

let cachedState: StemAudioAvailabilityState | null = null
let availabilityRequest: Promise<StemAudioAvailabilityState> | null = null

function normalizeUnavailableMessage(detail: unknown) {
  if (typeof detail !== 'string' || detail.trim().length === 0) {
    return AUDIO_UNAVAILABLE_MESSAGE
  }

  if (detail.includes('OPENAI_API_KEY')) {
    return AUDIO_UNAVAILABLE_MESSAGE
  }

  return detail
}

async function fetchStemAudioAvailability(): Promise<StemAudioAvailabilityState> {
  try {
    const response = await fetch('/api/health', {
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
    cachedState ?? {
      status: 'checking',
      message: null,
    },
  )

  useEffect(() => {
    if (cachedState) {
      setState(cachedState)
      return
    }

    if (!availabilityRequest) {
      availabilityRequest = fetchStemAudioAvailability().then((result) => {
        cachedState = result
        return result
      }).finally(() => {
        availabilityRequest = null
      })
    }

    let isCancelled = false

    void availabilityRequest.then((result) => {
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
