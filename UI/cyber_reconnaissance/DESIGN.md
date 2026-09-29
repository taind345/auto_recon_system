---
name: Cyber Reconnaissance
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f3'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1b1b1b'
  on-surface-variant: '#3c4a3c'
  inverse-surface: '#303030'
  inverse-on-surface: '#f1f1f1'
  outline: '#6c7b6a'
  outline-variant: '#bbcbb8'
  surface-tint: '#006e2a'
  primary: '#006e2a'
  on-primary: '#ffffff'
  primary-container: '#00c853'
  on-primary-container: '#004c1b'
  inverse-primary: '#3ce36a'
  secondary: '#006c4e'
  on-secondary: '#ffffff'
  secondary-container: '#97f5cc'
  on-secondary-container: '#007353'
  tertiary: '#006c49'
  on-tertiary: '#ffffff'
  tertiary-container: '#29c48b'
  on-tertiary-container: '#004b32'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#69ff87'
  primary-fixed-dim: '#3ce36a'
  on-primary-fixed: '#002108'
  on-primary-fixed-variant: '#00531e'
  secondary-fixed: '#97f5cc'
  secondary-fixed-dim: '#7bd8b1'
  on-secondary-fixed: '#002115'
  on-secondary-fixed-variant: '#00513a'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#f9f9f9'
  on-background: '#1b1b1b'
  surface-variant: '#e2e2e2'
typography:
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.03em
  headline-xl-mobile:
    fontFamily: Space Grotesk
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.04em
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.06em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.08em
spacing:
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1.5rem
  margin-sm: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system embodies high-velocity intelligence, digital forensics, and precision threat surveillance. It rejects muddy, dark-mode sci-fi clichés in favor of a clinical, hyper-legible "lab-grade" cyber operations interface: blindingly stark white diagnostic backgrounds paired with razor-sharp black containment lines and striking synthetic emerald accents.

The visual style blends Neo-Brutalist technical precision with an architectural tactical instrument. It evokes an uncompromising sense of absolute clarity, situational awareness, and executive operational control. The aesthetic is clean, engineered, high-density, and uncompromisingly authoritative—built specifically for cyber intelligence analysts, network operators, and telemetry engineers.

## Colors

The palette relies on stark polarization:
- **Canvas & Containers (`#ffffff`):** Pure clinical white provides an ultra-clear, low-fatigue substrate for dense surveillance feeds and telemetry data.
- **Structural Black (`#000000`):** Used for typography, strict 1px/2px containment borders, and high-priority indicators, creating maximum optical contrast.
- **Primary Electric Green (`#00c853`):** Active radar scans, positive threat detection, focus states, and primary interaction triggers.
- **Deep Emerald (`#047857`):** Stable states, verified infrastructure indicators, interactive hover targets, and structural anchors.
- **Telemetry Emerald (`#10b981`):** Sub-node activity, secondary status pings, and active telemetry meters.
- **Technical Muted Grays (`#f4f4f5`, `#71717a`):** Diagnostic grid dividers, passive table headers, and structural backgrounds.

## Typography

Typography acts as instrumentation:
- **Headlines:** Set in `Space Grotesk`. Geometric, technical, and authoritative. Headlines utilize tight tracking and structured capitalization for sector tags and status overviews.
- **Body:** Set in `Inter`. Utilitarian and neutral, optimized for parsing high-density analytical briefings and complex incident narratives without distortion.
- **Labels & Monospace:** Set in `JetBrains Mono`. Dedicated to IP addresses, payload logs, hex strings, timestamps, system telemetry, and micro-badges. All technical labels use uppercase tracking to preserve machine-readout aesthetics.

## Layout & Spacing

The layout is anchored by a persistent vertical navigation rail (width: `72px` collapsed, `240px` expanded) docked to the left edge of the viewport. 

- **Desktop (1280px+):** The workspace expands fluidly beyond the left rail into an asymmetric multi-pane dashboard using a 12-column subgrid with `1.5rem` gutters. Panels are segmented by crisp vertical and horizontal dividing lines.
- **Tablet (768px - 1279px):** The rail collapses into icon-only mode (`72px`). Content condenses into an 8-column arrangement with `1rem` gutters. Secondary inspector panes dock into collapsible slide-over drawers.
- **Mobile (< 768px):** The vertical rail transitions to an anchor bar docked at the base or an off-canvas drawer accessed via a monospace trigger. The grid simplifies to a single-column stack with `1rem` margins and `0.5rem` to `1rem` card gaps.

## Elevation & Depth

This system avoids blurred drop shadows and diffuse lighting in favor of **structural containment and hard-edge isometric offsets**:

- **Borders & Dividers:** All containment tiers are established through solid `1px` or `2px` jet black (`#000000`) borders.
- **Hard Depth / Tactile Offsets:** Active cards, floating modal palettes, and key tactical action targets utilize high-contrast hard shadows: `2px 2px 0px #000000` or `4px 4px 0px #000000`.
- **Active State Highlights:** Focused interactive zones use a double-border effect or a solid neon aura created with `0 0 0 2px #000000, 0 0 0 4px #00c853`.
- **Surface Nesting:** Contrast is heightened by nesting pure `#ffffff` panels within subtle `#f4f4f5` diagnostic track envelopes.

## Shapes

Every element is defined by strict `0px` radius edges (sharp). No organic curvature is permitted; buttons, cards, badges, tooltips, and inputs terminate at strict 90-degree right angles. To accentuate the tactical instrument identity, selected containers feature 45-degree chamfered corners (`clip-path: polygon(...)`) on top-right edges for identification chips and terminal tabs.

## Components

### Vertical Navigation Rail
- **Layout:** Fixed left column, pure white surface bounded by a continuous `1px` right border in jet black (`#000000`).
- **Items:** Fixed square targets (`48px x 48px`) housing technical icons. Hover shifts background to `#f4f4f5`. Active state applies an inverted jet black (`#000000`) background with electric green (`#00c853`) icons and a `3px` left edge accent in `#00c853`.
- **System Indicator:** Displays a live pulsing green beacon (`#00c853`) with monospace coordinates and ping metrics at the bottom edge.

### Buttons
- **Primary:** Solid jet black background (`#000000`), bold electric green text (`#00c853`), and `1px` black border. Hover triggers an inverted state: `#00c853` background with `#000000` text and a hard `3px 3px 0px #000000` shadow.
- **Secondary / Ghost:** White background, solid `1px` black border, black text. Hover applies a `#f4f4f5` tint with a hard `2px 2px 0px #000000` offset.
- **Critical / Intercept:** Deep emerald (`#047857`) background, crisp white monospace text, zero border-radius.

### Chips & Threat Badges
- **Structure:** Monospace font (`JetBrains Mono`, `10px`), all uppercase, `2px 6px` padding.
- **Visuals:** High-contrast outlined boxes with a solid 1px border.
  - *Active / Green Alert:* `#000000` border, `#00c853` background, `#000000` text.
  - *Telemetry / Info:* `#000000` border, `#ffffff` background, `#047857` text.

### Inputs & Terminal Fields
- **Fields:** Pure white background, `1px` solid black border, sharp edges.
- **Prefix:** Built-in terminal icon or segment label in monospace (`JetBrains Mono`) contained inside a `#f4f4f5` inner box with a right-side black divider line.
- **Focus:** `2px` solid `#000000` outline with a localized inset ring of `#00c853`.

### Checkboxes & Radios
- **Checkboxes:** Exact `16px x 16px` squares, `1.5px` solid black border. Selected state fills with jet black (`#000000`) and displays an electric green (`#00c853`) square dot or check mark.
- **Radios:** Displayed as diamond check elements (rotated 45-degree squares) or strict squares with a centered inner emerald box.

### Data Cards & Telemetry Grid Panels
- **Anatomy:** White substrate, bounded by `1px` solid `#000000` borders, optionally accented with a top-level technical header bar (`bg: #000000`, `text: #ffffff`, uppercase monospace label).
- **Diagnostics:** Subtle interior hairline dividers (`#e4e4e7`) delineate internal metrics. Key summary figures leverage `Space Grotesk` with adjacent neon-green directional indicator marks.