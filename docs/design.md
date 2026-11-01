# Console design standards (Ledger)

The rules every console page follows (plan task 4.U0). Agents building UI read this before
writing a page, and every UI change ships with screenshots (see
[Checking UI changes](#checking-ui-changes)). The decisions here come from Quincy's design
review on 2026-10-29 to 2026-11-01.

**Reference implementation:** [`docs/design/ledger-screens.html`](design/ledger-screens.html),
a single-file clickable prototype of every Phase 4 screen. Open it in a browser and use the
**Screens** menu (top right) to move between screens and states. When this file and the
prototype disagree, this file wins; fix the prototype. Prototype-only parts, not to be
built: the **Screens** menu, the **Mark** switch on sign-in, and the paused glass mark code
(`.si-glass`, `.mk-rim`, `.mk-glow`, `drawRim`).

## Product

- **Name:** Ledger. **Who it's for:** a manufacturer's security team, as an operations
  console (not a public reporting form).
- **Look:** Apple Pro apps on true black. Quiet, precise, angular. Content first; chrome
  stays out of the way.
- **Dark mode only** (confirmed 2026-11-01). There is no light theme; don't add
  `prefers-color-scheme: light` styles.
- **Console rules that come from the API** (`CLAUDE.md`): no business rules in pages (the
  pages call the API and show what it returns); reporter details only on the single-ticket
  page; the signed-in username is sent as `X-Actor` on every change; every time is UTC to
  the second.

## Type

- **Font stack:** `-apple-system, BlinkMacSystemFont, "SF Pro Text"` (UI) and
  `"SF Pro Display"` (headlines), falling back to **Inter**, then system sans. SF Pro comes
  only from the system stack: its license forbids serving it as a web font. Code, IDs and
  timestamps use `ui-monospace, "SF Mono", "JetBrains Mono"`.
- **Body** 15 px / 1.47. Labels 13 px, captions 12 px. Headlines 600 weight with negative
  tracking that grows with size (about -0.028em at 40 px); body tracking stays at 0.
- **Numbers that change** (counts, countdowns, times) use `font-variant-numeric: tabular-nums`.
- **Casing (HIG, chosen 2026-10-29):** Title Case for controls (buttons, menu items,
  segments, dock items, column headings). Sentence case for everything else, including page
  headings, toasts, errors, and checkbox, radio and switch labels.

## Color

All tokens live on `:root` in the prototype; use the variables, never raw hex.

| Role | Tokens |
|---|---|
| Canvas | `--canvas` `#000` (true black) |
| Surfaces (elevation is lightness, never shadow) | `--surface-1` `#1C1C1E`, `--surface-2` `#2C2C2E`, `--surface-3` `#3A3A3C` |
| Text | `--label` `#F5F5F7`, `--label-2` `#A1A1A6`, `--label-3` `#6E6E73`, `--label-4` `#48484A` |
| Lines and fills | `--hairline`, `--separator`, `--separator-strong`; `--fill-1` to `--fill-4` |
| Accent (everything interactive) | `--accent` `#0A84FF`, `--accent-text` `#409CFF` for links and tinted text |
| State only | `--green`, `--yellow`, `--orange`, `--red`, `--cyan`, `--indigo`, `--gray` (Apple's dark variants) |
| TLP labels | `--tlp-red`, `--tlp-amber`, `--tlp-green`, `--tlp-clear` (TLP 2.0 colors for black backgrounds) |
| Metal | `--titanium`: only on the Home countdown (the one hero number) |

- **Status colors carry meaning and are reserved:** never use red, orange, yellow or green
  for decoration, and always pair a status color with a label or icon.
- **Mark palette** (sign-in mark, its Lines and Blueprint highlights): `#0A84FF`, `#409CFF`,
  `#64D2FF`, `#7D7AFF`, `#5E5CE6`. Status colors are deliberately left out.

## Spacing, shape and layout

- **8-point grid** with 4-point half steps: `--s1` 4 px to `--s9` 96 px.
- **Corner radii ("Machined"):** `--r-xs` 3, `--r-sm` 5, `--r-md` 8, `--r-lg` 12, `--r-xl`
  16 px. Nested corners are concentric: inner radius = outer radius minus the inset.
- **Control heights:** 28, 36 and 44 px (`--h-sm`, `--h-md`, `--h-lg`). Touch targets are at
  least 44 px.
- **Page layout:** no sidebar. One content column (max 1200 px). Navigation lives in the
  floating **dock** at the bottom, visible on every device, with the `/` command field inside
  it ("Find or do… /"; a magnifier on phones). Phones use a 16 px side gutter and respect
  `env(safe-area-inset-*)`.
- **Two widths to design for:** desktop (checked at 1280 px) and phone (checked at 390 px).
  The sign-in screen is split on desktop (mark left, form right) and centered on phones.

## Materials

Glass only reads through what's behind it, so it goes only where content moves underneath.

| Surface | Material |
|---|---|
| Dock, command field, menus, toasts | Glass: translucent fill with `backdrop-filter: blur() saturate()` and a light top edge |
| Dialogs (short: a title, a sentence or two, maybe a short list, buttons; no text fields), e.g. Close Ticket | Glass: `rgba(44, 44, 48, 0.6)`, the dock's `blur(14px) saturate(190%) brightness(1.08)` and its edge highlight |
| Big modals (forms or long reads): New Ticket, Edit Ticket, Triage, Record Submission | Solid `--surface-1` |
| Cards, rows, page content | Solid surfaces |

- Modals sit over a 60% black scrim.
- Every glass surface goes solid under `prefers-reduced-transparency: reduce`.

## Components

The prototype has each of these built; copy its markup and CSS rather than re-deriving them.

- **Buttons** (`.btn`): `primary` (filled accent), `secondary` (gray fill), `tinted` (accent
  at 18%), `plain` (text), `destructive` (red at 16%; `solid` for the final confirm), `icon`.
  Sizes `sm`/default/`lg`. **One filled primary per screen.** Actions repeated on every row
  use `tinted`.
- **Ticket list** (the "Quiet" list, `.lrow`): rows grouped by due window (Due in 24 h,
  Later, …) with counts. Each row shows the ticket, its report track (EW, N, FR chips) and
  a deadline chip. **Lists stay calm:** hovering a row only highlights it (a 12 px-corner
  highlight wider than the text) and gives the deadline chip a faint fill. The chip's
  actions (the next report action, Open) appear only when the chip itself is hovered,
  focused or tapped, and hover effects are off while a list is scrolling (clicks still work).
- **State and status:** ticket state is a dot plus a word (`.state`: received = cyan ring,
  reportable = orange dot, closed = gray). Report status is a badge (`.badge`): not
  applicable gray, awaiting indigo, pending cyan, overdue red, submitted green, submitted
  late orange.
- **Forms** (`.field`, `.input`): label above, help or error below. Focus: accent border plus
  a 3 px accent ring at 45%. Errors: red border, a red ring and one line of text under the
  field; validate on blur, not on submit.
- **Segmented controls** (`.seg`): a sliding indicator behind the selected segment.
- **Deadline island** (`.island`): the next deadline floats at the top of the ticket page with
  a live countdown.
- **Sheets and dialogs** (`.sheet-card`, `.sheet-card.dialog`): see Materials. Sheets have a
  bar with Cancel (left), the title (center) and the action (right).
- **Toasts:** glass, short, sentence case.
- **Empty and "not available yet" states:** say what's missing and what will make it
  available ("arrives when the API supports it"), with the control still in place.
- **Wordmark:** a plain white bookmark (no tile) and "Ledger".

## The mark and sign-in

- **One shape, one source.** The bookmark is the SVG path `#mk-shape`
  (`M0 0H100V140L50 103.6L0 140Z`, viewBox `0 0 100 140`). Everything that draws the mark
  reads it: the sign-in treatments, HTML clipped through `#mk-clip-box`, and the wordmark
  (a mask built from the path in JS). To change the logo, change that path only.
- **Three treatments, one picked at random on every load:** Lines (ledger rules; every 4 s a
  new rule lights in a mark color), Blueprint (an outline draws over a dot grid, then dot
  patterns light in a mark color) and Window (a bookmark-shaped window onto slowly drifting,
  screen-blended color fields, blurred into one surface). Each new line or pattern takes a
  random mark color, never the same twice in a row.
- **The mark never reacts to errors.** A failed sign-in shakes the field group, gives it a
  red outline, and shows one line of text under it.
- **The sign-in field** is one group that grows from username to password; the arrow button
  travels down to the password row. Its material is the translucent field
  (`rgba(36, 36, 40, 0.62)` with blur), not the glass recipe.

## Motion

Motion is physical, interruptible and quick. Animate only `transform`, `opacity` and
`filter` where possible.

- **Press system:** one pointer-driven press state (`.is-pressed`, not `:active`) for every
  control, with 10 px drag-off slop and Space/Return. Glass controls swell to 1.14, solid
  buttons shrink to 0.97, segments to 0.95; rows and fields highlight.
- **Morph, don't swap:** an element that changes shape (dock to command field, island to its
  expanded list) stays one container that springs width, height and radius while its
  contents cross-fade. Approved values: width 0.36 s, height 0.40 s, shrinking critically
  damped (no undershoot); contents stagger in from 50 to 60 ms, then +20 to 25 ms each,
  nearest the origin first, and leave together. If the clicked element has a counterpart in
  the new shape, it travels there.
- **Containers keep their inset:** when an item inside grows, the container grows by the same
  amount on the same spring.
- **When new content replaces old, the old leaves first and visibly.**
- **Springs:** default critically damped (no bounce). Overshoot only after a gesture with
  momentum.
- **Countdowns use a numeric text transition** (the web version of SwiftUI's
  `.contentTransition(.numericText(countsDown: true))`, `ntSet()` in the prototype):
  - Each character sits in its own slot, and only changed characters move.
  - Numbers are aligned digit run by digit run from the right, so the words in "in 6 h 10 m" never move.
  - The old character slides 0.42 em in the counting direction (down when counting down), shrinks to 70% and blurs out. The new one arrives from the other side at 70% and grows to full size.
  - The spring is critically damped, response 0.42 s, written as a CSS `linear()` easing.
  - When several characters change, they start 70 ms apart, left to right.
  - A slot whose glyph changes width springs to the new width.
  - A visually hidden copy of the full text is for screen readers.
- **Ticking clocks** update about 40 ms after each second boundary, rescheduled every tick, never with a plain 1 s
  `setInterval` (that lands on the boundary and shows a second twice, then skips one).
- **Reduced motion** (`prefers-reduced-motion: reduce`): no travel, springs or parallax; use
  short cross-fades (about 150 ms). Ambient motion on the sign-in mark stops.

## Accessibility

- WCAG 2.2 AA contrast for text. Focus is always visible: a 3 px accent outline at 45%.
- Every control is reachable and usable by keyboard; dialogs trap focus and return it on
  close.
- Status is never color alone (label or icon with it).
- Respect `prefers-reduced-motion`, `prefers-reduced-transparency`, `prefers-contrast: more`
  and `forced-colors: active`.
- Live text that changes every second (countdowns) is not announced on every tick.

## Copy voice

Plain, short, specific. Say what happened and what to do next, in sentence case, no jargon
and no exclamation marks. Errors name the problem in one line under the field ("That
username and password don't match."). Times are UTC and say so. Buttons say exactly what
they do ("Record Notification", "Close as Invalid").

## Tried and dropped

Kept short so nobody re-proposes them:

- A glass sign-in field following the Digital Signage glass rules (the original field was
  preferred).
- A red flash on the mark for a failed sign-in.
- A metal app-icon tile for the mark or wordmark.
- A glass treatment of the mark itself (paused).
- A light theme.

## Checking UI changes

Before reporting any UI change as done:

- Render it in a real browser and look at screenshots of every state it touches: rest,
  hover/focus, pressed, filled, error, empty, open/closed.
- Check both widths: 1280 px and 390 px.
- Do one pass with reduced motion on.
- Crop and zoom on the changed element.
- Fix what the screenshots show.
- In the report, say what was checked and what screenshots can't show (motion feel, HDR,
  Safari-specific rendering).

PRs that change UI include the screenshots (see the PR template).
