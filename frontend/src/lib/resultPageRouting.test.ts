import { describe, expect, it } from 'vitest'
import { getPracticeDoneRoute, getReportRoute } from './resultPageRouting'

describe('resultPageRouting', () => {
  it('keeps PracticeDone in loading while recovery is still in flight', () => {
    expect(
      getPracticeDoneRoute({
        restoreOutcome: 'restoring',
        hasCurrentExam: false,
        hasSession: false,
        sessionMode: null,
        isSubmitted: false,
        hasResult: false,
      }),
    ).toBe('loading')
  })

  it('sends PracticeDone home when no recoverable session exists', () => {
    expect(
      getPracticeDoneRoute({
        restoreOutcome: 'missing',
        hasCurrentExam: false,
        hasSession: false,
        sessionMode: null,
        isSubmitted: false,
        hasResult: false,
      }),
    ).toBe('toHome')
  })

  it('sends PracticeDone back to practice when the recovered session is unfinished', () => {
    expect(
      getPracticeDoneRoute({
        restoreOutcome: 'loaded',
        hasCurrentExam: true,
        hasSession: true,
        sessionMode: 'practice',
        isSubmitted: false,
        hasResult: false,
      }),
    ).toBe('toPractice')
  })

  it('shows PracticeDone when the recovered practice session is complete', () => {
    expect(
      getPracticeDoneRoute({
        restoreOutcome: 'loaded',
        hasCurrentExam: true,
        hasSession: true,
        sessionMode: 'practice',
        isSubmitted: true,
        hasResult: true,
      }),
    ).toBe('show')
  })

  it('keeps Report in loading while recovery is still in flight', () => {
    expect(
      getReportRoute({
        restoreOutcome: 'restoring',
        hasCurrentExam: false,
        hasSession: false,
        sessionMode: null,
        isSubmitted: false,
        hasResult: false,
      }),
    ).toBe('loading')
  })

  it('sends Report home when no recoverable session exists', () => {
    expect(
      getReportRoute({
        restoreOutcome: 'missing',
        hasCurrentExam: false,
        hasSession: false,
        sessionMode: null,
        isSubmitted: false,
        hasResult: false,
      }),
    ).toBe('toHome')
  })

  it('sends Report back to the exam when the recovered real exam is unfinished', () => {
    expect(
      getReportRoute({
        restoreOutcome: 'loaded',
        hasCurrentExam: true,
        hasSession: true,
        sessionMode: 'real',
        isSubmitted: false,
        hasResult: false,
      }),
    ).toBe('toExam')
  })

  it('shows Report when the recovered real exam is complete', () => {
    expect(
      getReportRoute({
        restoreOutcome: 'loaded',
        hasCurrentExam: true,
        hasSession: true,
        sessionMode: 'real',
        isSubmitted: true,
        hasResult: true,
      }),
    ).toBe('show')
  })
})
