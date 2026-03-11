# Optimize Question Card Images Spec

## Why
User requests visual improvements for the question card's image display:
1. Single images appear too small and the left container takes up too much unnecessary width.
2. Multiple images need to be maximized within the fixed area without scrolling.

## What Changes

### Single Image Scenario (`.question-card--stem-single`)
- **Layout**: Reduce the width of the left image column.
  - *Current*: `6fr 4fr` (60% left)
  - *New*: `1fr 1fr` (50% left) or `5fr 5fr`.
- **Image Size**: Increase the visual size of the image by ~50%.
  - *Current*: `max-width: 85%`, `max-height: 85%` with padding.
  - *New*: Increase limits to `100%`, reduce container padding, potentially use `transform: scale()` if container bounds allow, or simply letting it fill the available box better.
  - *Note*: "Enlarge 50%" strictly might be impossible if constrained by height, but we will maximize `max-height` and `max-width` to limits and reduce whitespace.

### Multi Image Scenario (`.question-card--stem-multi`)
- **Layout**: Keep the layout stable (fixed window).
- **Image Size**: "Moderate enlargement" while ensuring no scroll.
  - Reduce `gap` in grid.
  - Reduce internal padding of the figure container.
  - Ensure `object-fit: contain`.

## Impact
- **Affected Files**: `src/index.css` (primary styling rules).
- **Visuals**: Left column width changes dynamically based on image count.

## MODIFIED Requirements

### Requirement: Single Image Display
- **Condition**: `stemGraphicCount === 1`
- **Layout**: Left column width reduces (target ~50% or 45% of card width).
- **Image**: Displayed larger (closer to container edges).

### Requirement: Multi Image Display
- **Condition**: `stemGraphicCount > 1`
- **Layout**: Left column width remains optimized for grid (keep ~60% or adjust if needed).
- **Image**: Grid layout optimized to fill space without scrolling.
