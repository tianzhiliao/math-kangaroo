import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchStemAudioAvailability } from './useStemAudioAvailability'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('fetchStemAudioAvailability', () => {
  it('returns available when the backend health check is ready', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ status: 'ok' }),
    })

    const result = await fetchStemAudioAvailability(fetchMock as unknown as typeof fetch)

    expect(result).toEqual({
      status: 'available',
      message: null,
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/health',
      expect.objectContaining({
        headers: {
          Accept: 'application/json',
        },
      }),
    )
  })

  it('returns the backend detail when health reports the service is unavailable', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      json: vi.fn().mockResolvedValue({
        status: 'unavailable',
        detail: 'OpenAI TTS is configured, but this backend cannot reach api.openai.com:443.',
      }),
    })

    const result = await fetchStemAudioAvailability(fetchMock as unknown as typeof fetch)

    expect(result).toEqual({
      status: 'unavailable',
      message: 'OpenAI TTS is configured, but this backend cannot reach api.openai.com:443.',
    })
  })
})
