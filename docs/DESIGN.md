# Synoptic Blueprint

The design brief was "a look Claude has never used": not glassmorphism, not
gradient cards with rounded corners and soft shadows, and not warm newsprint.

## The idea

A weather chart already has a visual language, and it is a technical drawing.
Real synoptic charts are isobars, station plots, front lines and wind barbs
drawn as line work on a drafting sheet. So the page is not a dashboard *about*
the atmosphere; it is a drawing *of* it.

That premise decides the rest.

## Rules

**No shadows. Ever.** Depth comes from line weight alone — 0.5px for grid,
1px for structure, 2px for emphasis. A drawing has no z-axis.

**No rounded corners.** `--radius: 0px` is a token so the decision is
enforceable rather than remembered.

**Registration marks, not borders.** Each panel carries crop marks at two
corners, the way a plate-aligned sheet does.

**Annotation, not tooltips.** The meteogram's extremes are called out with a
dashed leader line into a label, because that is how a drawing points at
something. Nothing important hides behind a hover.

**A title block.** The footer is an engineering title block: sheet, coordinates,
time zone, source, issue time, cache state, revision. It is genuinely useful
metadata that a weather app usually buries.

**Real notation.** The wind barbs are correct — pennant 50 knots, full barb 10,
half barb 5. The station plot puts temperature upper-left, dew point lower-left
and the pressure code upper-right, with sky cover shaded in the circle, as the
station model specifies. Anyone who reads charts can read this page.

**The background is data.** The isobar field is generated from the actual
pressure forecast: a wide pressure spread draws tightly spaced lines, a slack
gradient opens them out.

## Colour

Two themes, one drawing. **Cyanotype** is the blueprint under darkroom light;
**Draft** is the same sheet printed on paper. Accents follow chart convention
rather than brand taste: cold blue, warm red, precipitation green, caution
amber.

Every text colour was measured against its background before any of it was
written. All pass WCAG AA; most pass AAA.

| | Cyanotype | Draft |
|---|---|---|
| Primary text | 14.9:1 | 12.6:1 |
| Secondary | 9.3:1 | 6.0:1 |
| Tertiary | 6.1:1 | 4.6:1 |
| Lowest accent | 6.7:1 | 4.8:1 |

## Type

The first draft used a wide display mono for micro-labels, which looked like
drafting stencil and read badly at 11px. Legibility wins over character:

- **Inter** for everything read as language, falling back to the platform UI
  font.
- **JetBrains Mono** for numbers only, falling back to the platform mono.
  Tabular figures throughout, so a column of temperatures does not jitter as
  values change.
- 15px body floor, 11px label floor, uppercase labels held at weight 600 with
  restrained tracking.

Fonts load from Google Fonts as an enhancement. The fallback stack is real, not
decorative — the screenshots used during development were taken with the web
fonts blocked.

## Layout

A 12-column grid, packed as masonry: each panel is measured after render and
given a matching row span. Start-aligned grids leave holes when panels differ
in height; stretched grids leave dead space inside short panels. Measuring
avoids both, and it survives panels that appear conditionally, such as sea
state only showing for coastal places.

Because dense packing reorders panels on screen, the sheet numbers are assigned
*after* layout, from actual position — a numbered drawing whose numbers jump
around is worse than no numbers.
