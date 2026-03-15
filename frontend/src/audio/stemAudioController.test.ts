import { describe, expect, it } from 'vitest'
import {
  StemAudioController,
  createStemTextVersion,
} from './stemAudioController'

type Listener = () => void

class FakeAudio {
  currentTime = 0
  preload = 'none'
  pauseCalls = 0
  playCalls = 0
  readonly src: string
  readonly listeners = new Map<string, Set<Listener>>()
  readonly playPromise: Promise<void>
  private resolvePlayPromise!: () => void
  private rejectPlayPromise!: (error?: unknown) => void

  constructor(src: string) {
    this.src = src
    this.playPromise = new Promise<void>((resolve, reject) => {
      this.resolvePlayPromise = resolve
      this.rejectPlayPromise = reject
    })
  }

  play = () => {
    this.playCalls += 1
    return this.playPromise
  }

  pause = () => {
    this.pauseCalls += 1
  }

  addEventListener(type: string, listener: EventListener) {
    const listeners = this.listeners.get(type) ?? new Set<Listener>()
    listeners.add(listener as Listener)
    this.listeners.set(type, listeners)
  }

  removeEventListener(type: string, listener: EventListener) {
    this.listeners.get(type)?.delete(listener as Listener)
  }

  emit(type: string) {
    this.listeners.get(type)?.forEach((listener) => listener())
  }

  resolvePlay() {
    this.resolvePlayPromise()
  }

  rejectPlay(error: unknown) {
    this.rejectPlayPromise(error)
  }
}

function createControllerHarness() {
  const audios: FakeAudio[] = []
  const controller = new StemAudioController((src) => {
    const audio = new FakeAudio(src)
    audios.push(audio)
    return audio
  })

  return {
    audios,
    controller,
  }
}

async function flushMicrotasks() {
  await Promise.resolve()
  await Promise.resolve()
}

describe('StemAudioController', () => {
  it('starts in loading and then becomes playing on success', async () => {
    const { controller, audios } = createControllerHarness()

    controller.start('Exam_2020:1', '/api/audio-1')
    expect(controller.getSnapshot().status).toBe('loading')

    audios[0].emit('playing')
    audios[0].resolvePlay()
    await flushMicrotasks()

    expect(controller.getSnapshot()).toMatchObject({
      key: 'Exam_2020:1',
      status: 'playing',
      error: null,
    })
  })

  it('stops cleanly while still loading', () => {
    const { controller } = createControllerHarness()

    controller.start('Exam_2020:1', '/api/audio-1')
    controller.stop('Exam_2020:1')

    expect(controller.getSnapshot().status).toBe('idle')
  })

  it('stops cleanly while already playing', async () => {
    const { controller, audios } = createControllerHarness()

    controller.start('Exam_2020:1', '/api/audio-1')
    audios[0].emit('playing')
    audios[0].resolvePlay()
    await flushMicrotasks()

    controller.stop('Exam_2020:1')

    expect(controller.getSnapshot().status).toBe('idle')
    expect(audios[0].pauseCalls).toBe(1)
  })

  it('can stop the active audio during route cleanup', () => {
    const { controller } = createControllerHarness()

    controller.start('Exam_2020:1', '/api/audio-1')
    controller.stopIfCurrent('Exam_2020:1')

    expect(controller.getSnapshot().status).toBe('idle')
  })

  it('recovers from an error and can retry', async () => {
    const { controller, audios } = createControllerHarness()

    controller.start('Exam_2020:1', '/api/audio-1')
    audios[0].rejectPlay(new Error('network'))
    await flushMicrotasks()

    expect(controller.getSnapshot()).toMatchObject({
      key: 'Exam_2020:1',
      status: 'error',
    })

    controller.start('Exam_2020:1', '/api/audio-1')
    audios[1].emit('playing')
    audios[1].resolvePlay()
    await flushMicrotasks()

    expect(controller.getSnapshot().status).toBe('playing')
  })

  it('never keeps two audio instances active at the same time', () => {
    const { controller, audios } = createControllerHarness()

    controller.start('Exam_2020:1', '/api/audio-1')
    controller.start('Exam_2020:2', '/api/audio-2')

    expect(audios).toHaveLength(2)
    expect(audios[0].pauseCalls).toBe(1)
    expect(controller.getSnapshot()).toMatchObject({
      key: 'Exam_2020:2',
      status: 'loading',
    })
  })

  it('creates stable version hashes for audio URLs', () => {
    expect(createStemTextVersion('Hello there')).toBe(createStemTextVersion('Hello there'))
    expect(createStemTextVersion('Hello there')).not.toBe(createStemTextVersion('Hello there!'))
  })
})
