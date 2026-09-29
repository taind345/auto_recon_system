---
name: Terminal Protocol / Cyber-Recon
colors:
  surface: '#101413'
  surface-dim: '#101413'
  surface-bright: '#363a38'
  surface-container-lowest: '#0b0f0e'
  surface-container-low: '#181c1b'
  surface-container: '#1c201f'
  surface-container-high: '#272b29'
  surface-container-highest: '#323634'
  on-surface: '#e0e3e0'
  on-surface-variant: '#b9ccb5'
  inverse-surface: '#e0e3e0'
  inverse-on-surface: '#2d3130'
  outline: '#849581'
  outline-variant: '#3b4b3a'
  surface-tint: '#00e55b'
  primary: '#edffe8'
  on-primary: '#003911'
  primary-container: '#00ff66'
  on-primary-container: '#007128'
  inverse-primary: '#006e27'
  secondary: '#dcfdff'
  on-secondary: '#00373a'
  secondary-container: '#00f1fd'
  on-secondary-container: '#006a6f'
  tertiary: '#fff8f4'
  on-tertiary: '#432c00'
  tertiary-container: '#ffd79e'
  on-tertiary-container: '#835900'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#6bff83'
  primary-fixed-dim: '#00e55b'
  on-primary-fixed: '#002107'
  on-primary-fixed-variant: '#00531b'
  secondary-fixed: '#6ff6ff'
  secondary-fixed-dim: '#00dce6'
  on-secondary-fixed: '#002022'
  on-secondary-fixed-variant: '#004f53'
  tertiary-fixed: '#ffddaf'
  tertiary-fixed-dim: '#ffba43'
  on-tertiary-fixed: '#281800'
  on-tertiary-fixed-variant: '#614000'
  background: '#101413'
  on-background: '#e0e3e0'
  surface-variant: '#323634'
typography:
  headline-xl:
    fontFamily: JetBrains Mono
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: JetBrains Mono
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: JetBrains Mono
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0em
  body-lg:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 22px
    letterSpacing: 0em
  body-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.02em
  body-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.03em
  label-lg:
    fontFamily: Space Mono
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.08em
  label-md:
    fontFamily: Space Mono
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.1em
  label-sm:
    fontFamily: Space Mono
    fontSize: 9px
    fontWeight: '700'
    lineHeight: 12px
    letterSpacing: 0.12em
spacing:
  gutter: 0.75rem
  gutter-mobile: 0.5rem
  margin: 1rem
  margin-mobile: 0.5rem
  space-xs: 0.125rem
  space-sm: 0.25rem
  space-md: 0.5rem
  space-lg: 0.75rem
  space-xl: 1.25rem
---

## Brand & Style
This design system embodies the clinical precision, intensity, and low-latency velocity of advanced offensive cyber reconnaissance. Engineered for elite penetration testers, security analysts, and telemetry engineers, the interface evokes the tactical reality of direct hardware and socket interaction—a high-contrast terminal operating system rather than a commercial software dashboard.

The aesthetic fuses raw Cyberpunk utilitarianism with the disciplined typography of technical telemetry. Structural elements reject skeuomorphic decoration in favor of hard edges, monospaced data streams, phosphor-style radiance, and high-density telemetry readouts. The interface creates an emotional sensation of operational control, lethal efficiency, and immediate terminal situational awareness.

## Colors
The palette is built upon a subterranean, pitch-black foundation calibrated to reduce eye strain while amplifying optical phosphor persistence.

- **Primary (`#00FF66`)**: Phosphor Neon Green. Used for active reconnaissance feeds, primary commands, system statuses, successful packet captures, and terminal prompt markers.
- **Secondary (`#00F3FF`)**: Glitch Cyan. Signals telemetry streams, secondary network paths, selected nodes, active ports, and variable injections.
- **Tertiary (`#FFB000`)**: Amber Terminal. Reserved for elevated alerts, packet collision flags, protocol warnings, rate limits, and pending payload states.
- **Neutral (`#050807`)**: Void Terminal Canvas. A deep black-emerald substrate accented with layered container tiers:
  - Base canvas: `#050807`
  - Panel surface: `#0A0D0C`
  - Elevated card/module background: `#0F1412`
  - Boundary rules and matrix lines: `#1A2420`
- **Critical Failure (`#FF003C`)**: Laser Crimson. Reserved for fatal errors, tripped intrusion detection systems, broken sockets, and hostile network responses.

## Typography
Typography is strictly monospaced to preserve tabular data alignment, column-based hex/IP readouts, and rigorous ASCII alignment.

- **Headlines & Body**: Rendered in **JetBrains Mono** for maximum character distinction (notably `0`, `O`, `l`, `1`), ligatures for operational operators (`->`, `!=`, `:=`), and balanced vertical rhythm.
- **Labels, Telemetry Keys, & Status Flags**: Rendered in **Space Mono** in uppercase styling with deliberate tracking/letter-spacing to mimic tactical hardware silkscreens and matrix printer readouts.
- All numbers must maintain fixed-width tabular figures to prevent jitter during live packet streaming or real-time port scanning.

## Layout & Spacing
The layout follows a dense, hyper-structured tactical grid optimized for screen efficiency and multi-stream data ingestion.

- **Layout Model**: 12-column terminal grid on desktop screens, collapsing into a 4-column stack on constrained mobile monitors. Layouts prioritize maximized data density over open negative space.
- **Rhythm**: Built on a tight 4px base increment (`0.25rem`). Component margins and internal paddings are compressed to minimize dead space, simulating high-efficiency command-line consoles.
- **Reflow Rules**: Multi-pane interfaces (target list, trace tree, terminal stdout) sit side-by-side on displays >= 1024px. Below this breakpoint, subordinate panels fold into keyboard-accessible command drawer tabs.

## Elevation & Depth
Elevation rejects naturalistic soft drop shadows. Depth is achieved via crisp line structures, tonal zoning, and cathode-ray phosphor luminescence:

1. **Flat Structural Tiering**: Higher-level interfaces do not float above canvas surfaces via blur; they are distinguished by high-contrast outline frames (`#1A2420` resting, `#00FF66` active) and stepped background tones (`#050807` -> `#0A0D0C` -> `#0F1412`).
2. **Phosphor Glow**: Active modules, warning nodes, and hovered targets emit focused neon halos using tight, high-intensity color glow:
   - Primary Active: `box-shadow: 0 0 10px rgba(0, 255, 102, 0.35), inset 0 0 4px rgba(0, 255, 102, 0.15)`
   - Warning Active: `box-shadow: 0 0 10px rgba(255, 176, 0, 0.35), inset 0 0 4px rgba(255, 176, 0, 0.15)`
   - Glitch Secondary: `box-shadow: 0 0 10px rgba(0, 243, 255, 0.35), inset 0 0 4px rgba(0, 243, 255, 0.15)`
3. **CRT Scanlines & Matrix Overlays**: Tactical panels utilize a micro scanline texture overlay (`repeating-linear-gradient(0deg, rgba(0, 0, 0, 0.2) 0px, transparent 1px, transparent 2px)`) across display viewports to enhance the authentic terminal atmosphere.

## Shapes
The design system enforces complete geometric sharpness:
- **Corner Radii**: Strictly `0px` across all containers, inputs, buttons, badges, and modals.
- **Chamfered Geometry**: High-level modules may feature 45-degree angled corner notches (`clip-path: polygon(...)`) to reflect hardware console panels.
- **Dividers**: Single-pixel technical boundaries (`1px solid #1A2420`) with crosshair corner junctions (`+`) at visual intersections.

## Components

### Buttons
- **Primary [EXECUTE]**: Background `#00FF66`, text `#050807`, font `Space Mono` bold uppercase. On hover: emits an emerald glow, inverted text to `#000000`, with an oscillating prompt prefix (`> RUN`).
- **Ghost/Command**: Background transparent, border `1px solid #1A2420`, text `#00FF66`. On hover: border `#00FF66`, background `rgba(0, 255, 102, 0.05)`.
- **Destructive/Abort**: Border `1px solid #FF003C`, text `#FF003C`. On hover: background `#FF003C`, text `#050807`.

### Terminal Inputs & Command Lines
- Prefixed with terminal symbols (`root@recon:~#` or `>_`).
- Background: `#0A0D0C`, border: `1px solid #1A2420`, text: `#00FF66`.
- Active/Focus: Border transitions to `#00FF66` with an inner phosphor halo. Text caret renders as a blinking neon block (`width: 8px`, animation: 1s step-end infinite).

### Data Tables & Log Lists
- Striped with micro-contrast alternating backgrounds (`#0A0D0C` and `#0D1210`).
- Compact cell padding (`space-xs` vertical, `space-sm` horizontal).
- Headers in `Space Mono` uppercase `#00F3FF` with a bottom rule `1px solid #1A2420`. Hovering a row highlights the entire row with a `1px` border in `#00FF66` and an immediate ASCII pointer indicator (`>>`).

### Status Badges & Chips
- Sharp rectangular enclosures.
- Background: `rgba(color, 0.12)`, border: `1px solid color`.
- State colors: Active/Open (`#00FF66`), Vulnerable/Intercepted (`#00F3FF`), Warning/Slow (`#FFB000`), Dead/Blocked (`#FF003C`).

### Checkboxes & Radios
- Sharp `0px` boxes.
- Unchecked: `1px solid #1A2420`, background: `#050807`.
- Checked: Border `#00FF66`, inner content filled with an ASCII block (`■`) or custom solid cross (`+`) in `#00FF66`.

### Panels & Recon Cards
- Outer framing: `1px solid #1A2420`.
- Panel Header: Dedicated metadata bar with status coordinates (`STATUS: 200_OK // SECTOR: 0x4F`) and terminal control handles (`[-] [X]`).