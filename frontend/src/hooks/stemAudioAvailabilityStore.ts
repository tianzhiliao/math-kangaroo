export type StemAudioAvailabilityStatus = 'available' | 'unavailable'

export interface StemAudioAvailabilityState {
  status: StemAudioAvailabilityStatus
  message: string | null
}

type StemAudioAvailabilityFetcher = () => Promise<StemAudioAvailabilityState>

let cachedAvailableState: StemAudioAvailabilityState | null = null
let availabilityRequest: Promise<StemAudioAvailabilityState> | null = null

export function peekStemAudioAvailability() {
  return cachedAvailableState
}

export function loadStemAudioAvailability(fetcher: StemAudioAvailabilityFetcher) {
  if (cachedAvailableState) {
    return Promise.resolve(cachedAvailableState)
  }

  if (availabilityRequest) {
    return availabilityRequest
  }

  availabilityRequest = fetcher()
    .then((result) => {
      if (result.status === 'available') {
        cachedAvailableState = result
      }

      return result
    })
    .finally(() => {
      availabilityRequest = null
    })

  return availabilityRequest
}

export function resetStemAudioAvailabilityStore() {
  cachedAvailableState = null
  availabilityRequest = null
}
