---
name: similar-kangaroo-question
description: Use when a Math Kangaroo visual exam question needs a new similar item, or when the figure is an unfilled wireframe, a copied diagram, a generated image, or the item has no exam.json-style record or contest card.
---

# Similar Kangaroo Question

## Overview

One new item from one existing visual question. Match that figure's line weight.

## When to Use

- The bank item has a PNG figure, and the new item must keep its language, grade, and task type
- The picture must be redrawn, not copied
- A draft is strokes with no fill, or delivery stopped at the SVG

**Not for:** text-only items or published exam files.

## Contract

The caller names three paths. Write those files and nothing else.

| File | Contents |
|---|---|
| `*.svg` | Figure only. Real shapes. No `<image>`, no base64. |
| `*.json` | One question in the `release-data/exams/*/exam.json` shape, plus `answer`. `assets[].path` is the SVG. |
| `*-card.png` | Number, stem, figure, choices, in the paper's language. Width at least 1600. Rasterize the SVG. Do not redraw it. |

## Steps

1. Read `stem_text`, `choices`, `answer_key`, and the PNG. Sample fill colors and outline thickness from pixels, not from a caption.
2. Write a new stem in that language and grade. Same task. Change shapes, layout, or numbers. One correct choice.
3. Draw on white with filled shapes and dark outlines. Use sampled fills when the scan has color. If it is only ink, give each region its own pastel. Never `fill="none"`. Match outline ÷ viewBox width to the source. Keep edges from inventing extra regions. Use SVG `<text>` only for marks or numbers the task needs. Check every choice against the geometry.
4. JSON fields: `id`, `number`, `part`, `points`, `stem_text`, `answer` (the letter), `choices` (`label`, `text`, `asset_refs`), `shared_asset_refs`, `assets` (`id`, `path`, `format`, `media_type`, `kind`, `role`, `width`, `height`). Use `format` `svg`, `media_type` `image/svg+xml`, `kind` `question_figure`, `role` `stem`.
5. Card: serif type, white page, choices in source order. Render the SVG at the size it will be pasted.

## Example

```xml
<polygon points="188,36 40,252 332,252" fill="#ACD0EC" stroke="#222222" stroke-width="7" stroke-linejoin="round"/>
```

## Common Mistakes

| Excuse | Reality |
|---|---|
| "Color would make the edge look unfinished." | Fill the regions. An ink scan still gets pastels and a dark stroke. |
| "The SVG is enough, so skip the PNG." | The card is stem plus figure plus choices, at least 1600px wide. |
| "A custom JSON with `correct_letter` is the same." | Use `label`, `answer`, `shared_asset_refs`, and `assets`. |
| "A generated picture is faster." | Draw vectors. No image model. |
| "Overlaps still count as one shape." | Shared edges create extra regions. Separate them, or nest without touching. |

## Red Flags

- `fill="none"` or a white fill with only a stroke
- Same arrangement as the source picture
- Answer not checked on the drawn geometry
- Choices in a language other than the paper
