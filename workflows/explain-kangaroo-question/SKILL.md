---
name: explain-kangaroo-question
description: Use when writing or checking the pre-generated step-by-step explanations for original Math Kangaroo questions (release-data) or their generated similar questions.
---

# Explain Kangaroo Question

## Overview

Explanations are written ahead of time and shipped as data. Readers are 6-7 years old, so a wrong explanation is worse than none. Two separate roles do the work, and they never share a session:

1. **Blind solver**: solves each question from an answer-free packet.
2. **Writer**: compares the blind answer with the key, then writes the explanation.

## Files

| Question | Explanation file |
|---|---|
| Original | `release-data/exams/<exam_id>/explanations.json` with `{schema_version: 1, prompt_version, questions: {qNN: entry}}` |
| Similar | `generated/<exam_id>/<qNN>/explanation.json` with `{schema_version: 1, prompt_version, ...entry}` |

Only `status: "generated"` similar questions get an explanation. See `canada-gr0102e-2020` for a finished example of both.

## Entry

| Field | Rule |
|---|---|
| `source` | `"original"` or `"variant"` |
| `content_hash` | Leave `""`. `--stamp-hashes` fills it. |
| `answer` | The key's letter. |
| `independent_answer` | The blind solver's letter, or `null` if it could not decide. Never the key. |
| `key_idea` | One sentence: the idea that cracks the problem. |
| `steps` | 2-5 short strings, one step each, that walk to the answer. |
| `answer_sentence` | Exactly `So the answer is X.` |
| `choice_feedback` | One sentence for every wrong letter, no entry for the right one. Say what that choice gets wrong. |
| `generated_by`, `generated_at` | Model name and ISO time. |
| `review` | `{status, note}`. `unreviewed` normally. `flagged` with a `note` when the blind answer is missing or differs, or when the figure or the key looks broken. |

## Writing

- Short sentences, everyday words. Numbers as digits: `8 + 4 = 12`, `19 - 6 = 13`.
- Name what the child can see in the picture ("the tall tower", "the jar on the left"). Do not mention file names, labels, or that the figure is an image.
- Every step must be true for this exact figure. Check counts and positions against the picture before writing them.
- Never write `X is correct`, `answer is X`, or `option X is right` about a wrong letter.
- When flagged because nobody could confirm the key, write steps that describe the method only. Do not invent reasoning that lands on the key.

## Blind solver output

`<packet>/<exam_id>.solve.json`:

```json
{"original": {"q01": {"answer": "D", "confidence": "high", "work": "kangaroo 3,6; rabbit 8,6 -> 6"}},
 "variant":  {"q01": {"answer": null, "confidence": "low", "work": "P and Q are not on the path"}}}
```

`confidence` is `high`, `medium`, or `low`. Use `null` rather than guessing.

## Check

```bash
python3 scripts/validate_explanations.py --exam-id <exam_id> --stamp-hashes
```

Exit code 0 means every rule passes. Flagged items are listed for a human.
