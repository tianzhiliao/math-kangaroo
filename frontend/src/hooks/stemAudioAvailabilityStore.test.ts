import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  loadStemAudioAvailability,
  peekStemAudioAvailability,
  resetStemAudioAvailabilityStore,
} from './stemAudioAvailabilityStore'

afterEach(() => {
  resetStemAudioAvailabilityStore()
  vi.restoreAllMocks()
})

describe('stemAudioAvailabilityStore', () => {
  it('reuses a successful availability result from cache', async () => {
    const fetchAvailability = vi
      .fn()
      .mockResolvedValue({ status: 'available' as const, message: null })

    const first = await loadStemAudioAvailability(fetchAvailability)
    const second = await loadStemAudioAvailability(fetchAvailability)

    expect(first).toEqual({ status: 'available', message: null })
    expect(second).toEqual(first)
    expect(peekStemAudioAvailability()).toEqual(first)
    expect(fetchAvailability).toHaveBeenCalledTimes(1)
  })

  it('does not cache unavailable results so the next check can retry', async () => {
    const fetchAvailability = vi
      .fn()
      .mockResolvedValueOnce({ status: 'unavailable' as const, message: 'offline' })
      .mockResolvedValueOnce({ status: 'available' as const, message: null })

    const first = await loadStemAudioAvailability(fetchAvailability)
    const second = await loadStemAudioAvailability(fetchAvailability)

    expect(first).toEqual({ status: 'unavailable', message: 'offline' })
    expect(second).toEqual({ status: 'available', message: null })
    expect(peekStemAudioAvailability()).toEqual(second)
    expect(fetchAvailability).toHaveBeenCalledTimes(2)
  })
})
