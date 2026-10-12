# Generated question evaluation

Produced by `scripts/evaluate_generated_questions.py`.

## Coverage

- Source questions in release-data: 270
- Generated variants: 268
- Reusing the variant of an identical question: 2
- Missing: 0

## Structural audit

- Errors: 0
- Warnings: 0
- Notes: 27

Correct letters, variants vs. their source questions. A child who always
picks the most common letter scores its share without reading the question.

| Letter | Variants | Share | Sources | Share |
|---|---|---|---|---|
| A | 23 | 9% | 46 | 17% |
| B | 66 | 25% | 51 | 19% |
| C | 103 | 38% | 59 | 22% |
| D | 55 | 21% | 65 | 24% |
| E | 21 | 8% | 47 | 18% |

| Severity | Check | Count |
|---|---|---|
| info | `stem_reused` | 27 |

### Findings

- **info** `felix-austria-2014/q04` `stem_reused`: stem wording matches the source (similarity 0.98)
- **info** `felix-austria-2014/q14` `stem_reused`: stem wording matches the source (similarity 0.98)
- **info** `felix-austria-2017/q05` `stem_reused`: stem wording matches the source (similarity 0.98)
- **info** `felix-austria-2017/q08` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-austria-2018/q03` `stem_reused`: stem wording matches the source (similarity 0.98)
- **info** `felix-austria-2019/q01` `stem_reused`: stem wording matches the source (similarity 0.98)
- **info** `felix-austria-2019/q02` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-austria-2019/q05` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-austria-2019/q10` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-brazil-2020/q08` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-brazil-2020/q11` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-brazil-2020/q23` `stem_reused`: stem wording matches the source (similarity 0.99)
- **info** `canada-gr0102e-2020/q09` `stem_reused`: stem wording matches the source (similarity 0.97)
- **info** `canada-gr0102e-2020/q10` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-brazil-2021/q03` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-brazil-2021/q04` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-brazil-2021/q16` `stem_reused`: stem wording matches the source (similarity 0.99)
- **info** `felix-brazil-2021/q19` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-brazil-2021/q21` `stem_reused`: stem wording matches the source (similarity 0.99)
- **info** `felix-austria-2023/q03` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-austria-2023/q05` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-austria-2023/q07` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-austria-2023/q08` `stem_reused`: stem wording matches the source (similarity 0.99)
- **info** `felix-austria-2023/q09` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-austria-2023/q10` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-austria-2023/q12` `stem_reused`: stem wording matches the source (similarity 0.99)
- **info** `felix-austria-2025/q07` `stem_reused`: stem wording matches the source (similarity 1.00)
