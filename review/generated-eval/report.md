# Generated question evaluation

Produced by `scripts/evaluate_generated_questions.py`.

## Coverage

- Source questions in release-data: 270
- Generated variants: 260
- Reusing the variant of an identical question: 2
- Withdrawn (not shown in the app): 8
- Missing: 0

  - `canada-gr0102e-2020/q07`: Figure broken: the path does not connect P and Q, and points A-E are not on the path.
  - `canada-gr0102e-2021/q07`: Two answers: bracelet C is Nora's bracelet turned over.
  - `canada-gr0102e-2023/q02`: Several answers: with cylinders, cones or a lying cylinder, A, B, D and E all fit the top view.
  - `felix-austria-2018/q10`: Hands have no palm or back detail, so the count is 3 (B) or 5 (D).
  - `felix-austria-2019/q02`: Two answers: read bottom-to-top, the chain also contains option C.
  - `felix-austria-2019/q15`: Answer depends on an unstated premise (marks showing through the paper); the strips no longer form a pattern.
  - `felix-austria-2022/q10`: No choice matches the figure: the shapes follow abcba, but every option has 1st = 3rd digit.
  - `felix-austria-2024/q04`: Figure broken: no big-triangle outline, and the pieces do not form a triangle.

## Structural audit

- Errors: 0
- Warnings: 0
- Notes: 26

Correct letters, variants vs. their source questions. A child who always
picks the most common letter scores its share without reading the question.

| Letter | Variants | Share | Sources | Share |
|---|---|---|---|---|
| A | 22 | 8% | 38 | 15% |
| B | 62 | 24% | 52 | 20% |
| C | 100 | 38% | 58 | 22% |
| D | 55 | 21% | 64 | 25% |
| E | 21 | 8% | 48 | 18% |

| Severity | Check | Count |
|---|---|---|
| info | `stem_reused` | 26 |

### Findings

- **info** `felix-austria-2014/q04` `stem_reused`: stem wording matches the source (similarity 0.98)
- **info** `felix-austria-2014/q14` `stem_reused`: stem wording matches the source (similarity 0.98)
- **info** `felix-austria-2017/q05` `stem_reused`: stem wording matches the source (similarity 0.98)
- **info** `felix-austria-2017/q08` `stem_reused`: stem wording matches the source (similarity 1.00)
- **info** `felix-austria-2018/q03` `stem_reused`: stem wording matches the source (similarity 0.98)
- **info** `felix-austria-2019/q01` `stem_reused`: stem wording matches the source (similarity 0.98)
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
