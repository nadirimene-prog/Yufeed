# Full Design System Redesign: Sentinel → Minimalist Modern

## Overview

Replace the dark-first "YuFeed Sentinel" glassmorphism design system with the light-first "Minimalist Modern" design system. This is a token-first migration: changing the CSS foundation will cascade through all semantic-token-based components automatically, minimizing per-file changes.

## Key Design Decisions

1. **Glass Card → Featured Card**: Refactor `glass-card.tsx` into an "elevated/featured card" with gradient borders (no glassmorphism)
2. **Dark mode**: Remove the dark/light toggle. The new system is light-only, using inverted sections (`bg-foreground text-background`) for dark areas
3. **Risk colors**: Keep existing risk colors (critical/high/medium/low) — essential for a compliance app — but remove glow variants
4. **Fonts**: Geist → Inter, Space Grotesk → Calistoga, keep JetBrains Mono

---

## Phase 1: Design Tokens & CSS Foundation

_This single phase transforms ~70% of the visual appearance by changing the token values that everything references._

### File: `src/app/design-system.css` — Complete rewrite

- **Remove**: Aurora palette, cyan scales, dark theme mapping, glass defaults, dark bg layers
- **Replace with**: Minimalist Modern semantic tokens
  - `--bg-base: #FAFAFA` (warm off-white)
  - `--bg-elevated: #FFFFFF` (pure white cards)
  - `--bg-overlay: #F1F5F9` (slate-100)
  - `--bg-floating: #E2E8F0` (slate-200)
  - `--text-primary: #0F172A` (slate-900)
  - `--text-secondary: #64748B` (slate-500)
  - `--text-tertiary: #94A3B8` (slate-400)
  - `--brand-primary: #0052FF` (Electric Blue)
  - `--brand-primary-hover: #0047E0`
  - `--brand-secondary: #4D7CFF` (gradient endpoint)
  - `--border-subtle: #E2E8F0`
  - `--border-default: #CBD5E1`
  - `--border-strong: #94A3B8`
  - `--border-focus: #0052FF`
- **Remove**: Glass blur/bg/border tokens entirely
- **Remove**: Light theme overrides (now default IS light)
- **Keep**: Reduced motion, high contrast, spacing, radius, z-index, layout tokens

### File: `src/app/design-tokens-v2.css` — Complete rewrite

- **Replace color scales**:
  - `--color-aurora-*` → `--color-accent-*` (Electric Blue scale: #EFF6FF → #0052FF → #001A4D)
  - `--color-cyan-*` → Remove (single accent system now)
  - `--color-void-*` → `--color-slate-*` (keep slate values, rename for clarity)
- **Replace gradients**:
  - `--gradient-aurora` → `--gradient-accent: linear-gradient(to right, #0052FF, #4D7CFF)`
  - `--gradient-aurora-subtle` → `--gradient-accent-subtle: linear-gradient(to right, rgba(0,82,255,0.05), rgba(77,124,255,0.03))`
  - Remove `--gradient-glass`, `--gradient-mesh`
- **Replace shadows**:
  - Update elevation shadows for lighter appearance (reduce opacity)
  - Replace `--shadow-glass*` with `--shadow-accent: 0 4px 14px rgba(0,82,255,0.25)` and `--shadow-accent-lg: 0 8px 24px rgba(0,82,255,0.35)`
  - Remove all `--shadow-glow-*` variants
- **Remove**: Entire glass system (blur, bg, border tokens)
- **Remove**: `--surface-ultra-*`, `--surface-glow-*`
- **Update semantic mapping**: `:root` block becomes light-first
- **Remove**: `.light` class overrides (default IS light now)
- **Update risk colors**: Keep colors, remove `-glow` variants
- **Keep**: Typography scale, spacing, radius, easing, durations, z-index

### File: `src/app/globals.css` — Major update

- **@theme inline block**:
  - Replace aurora/cyan/void color scales with accent/slate scales
  - Replace `--font-sans` → Inter, `--font-display` → Calistoga
  - Replace glass shadow tokens with accent shadow tokens
  - Remove glass color mappings
- **@layer base**:
  - Update `::selection` to use accent blue instead of aurora
  - Update `body` background/text to new tokens
  - Update heading styles: `font-weight: normal` for h1/h2 (Calistoga doesn't need semibold)
  - Update scrollbar colors
  - Update `input-base:focus` box-shadow from purple to blue
- **@layer utilities**:
  - Update `.text-gradient` to use `#0052FF → #4D7CFF`
  - Replace `.glass-surface`, `.glass-interactive`, `.glass-elevated`, `.glass`, `.glow-critical` with new utilities:
    - `.surface-card` (white bg, subtle border, shadow)
    - `.surface-card-interactive` (with hover lift + shadow deepen)
    - `.surface-featured` (gradient border wrapper)
    - `.surface-inverted` (dark section: bg-foreground + light text + dot pattern)
  - Update `.animate-shimmer` gradient from purple to blue tint
  - Add `.section-label` utility (pill badge with accent dot + mono text)
  - Add `.gradient-underline` utility
- **@layer components**:
  - Update `.card` hover to add subtle accent gradient overlay
  - Update `.input-base:focus` box-shadow to accent blue
  - Update `.status-dot-pulse` colors
- **Keyframes**:
  - Update `status-pulse` from cyan to Electric Blue
  - Update `pulse-glow` from green to Electric Blue
  - Add `floating` keyframe (translateY ±10px, 5s ease-in-out infinite)
  - Add `rotate-slow` keyframe (360deg, 60s linear infinite)
  - Add `pulse-dot` keyframe (scale 1→1.3→1, opacity 1→0.7→1, 2s infinite)

---

## Phase 2: Font Loading

_Swap the three font families._

### File: `src/app/layout.tsx`

- Replace imports:
  - `Geist` → `Inter` (from `next/font/google`)
  - `Space_Grotesk` → `Calistoga` (from `next/font/google`)
  - Keep `JetBrains_Mono`
- Update CSS variables: `--font-geist` → `--font-inter`, `--font-space-grotesk` → `--font-calistoga`
- Update Inter config: weights `[400, 500, 600, 700]`, subsets `["latin"]`
- Update Calistoga config: default weight, subsets `["latin"]`
- Update `<body>` className: `bg-bg-base text-foreground` (tokens stay same, values change)
- Update `viewport.themeColor`: `#FAFAFA` (light) and `#0F172A` (dark/inverted)

---

## Phase 3: Motion System

_Update hardcoded color values in Framer Motion variants._

### File: `src/lib/motion.ts`

- `cardHover`: Change `rgba(109, 90, 205, ...)` → `rgba(0, 82, 255, ...)` in boxShadow
- `sidebarItem`: Change `rgba(109, 90, 205, 0.1)` → `rgba(0, 82, 255, 0.08)` in backgroundColor
- `criticalPulse`: Keep (risk color, unchanged)
- `primaryPulse`: Change `rgba(109, 90, 205, ...)` → `rgba(0, 82, 255, ...)`
- `reducedCardHover`: Change `rgba(109, 90, 205, 0.2)` → `rgba(0, 82, 255, 0.15)`
- Add new variants:
  - `floatingCard`: y-axis bob animation (±10px, 5s ease-in-out infinite)
  - `pulsingDot`: scale + opacity pulse (2s infinite)
  - `rotatingRing`: rotate 360° (60s linear infinite)

---

## Phase 4: Core UI Components

_Update the 6 most-used components. Most changes are small since they use semantic tokens._

### File: `src/components/ui/button-horizon.tsx`

- **primary variant**: Change from `bg-primary` to `bg-gradient-to-r from-[#0052FF] to-[#4D7CFF] text-white shadow-sm hover:shadow-[0_4px_14px_rgba(0,82,255,0.25)] hover:-translate-y-0.5 hover:brightness-110 active:scale-[0.98]`
- **glass variant**: Replace with `bg-transparent border border-border text-foreground hover:bg-[#F1F5F9] hover:border-[rgba(0,82,255,0.3)]`
- **gradient variant**: Update to use Electric Blue gradient
- **outline variant**: Update hover to `hover:border-[rgba(0,82,255,0.3)]`
- Update border-radius from `rounded-lg` to `rounded-xl` in base class

### File: `src/components/ui/card.tsx`

- Default variant: Ensure `bg-white border border-[#E2E8F0]` with `rounded-xl`
- Add hover effect: `group-hover:bg-gradient-to-br group-hover:from-[rgba(0,82,255,0.03)] group-hover:to-transparent`
- Update shadow progression: `shadow-md` default → `shadow-xl` on hover

### File: `src/components/ui/glass-card.tsx`

- Rename component to `FeaturedCard` (keep file, add deprecation alias)
- Remove all `backdrop-filter`, `backdrop-blur`, glow variants
- Default: Clean elevated card with stronger shadow
- Featured/elevated: Gradient border technique (2px gradient stroke via nested divs)
- Keep compound component pattern (Header/Title/Content/Footer)
- Update all class references

### File: `src/components/ui/input.tsx`

- Remove all `bg-white/5`, `bg-white/10` glass variants
- Update focus: `ring-2 ring-[#0052FF] ring-offset-2`
- Update placeholder: `text-[#94A3B8]/50`
- Update height: `h-12` for default inputs

### File: `src/components/ui/badge-horizon.tsx`

- Update primary variant to use accent blue
- Add `sectionLabel` variant: rounded-full pill with accent border, mono text, accent dot
- Update `StatusBadge` dot colors

### File: `src/components/ui/form.tsx`

- Update focus ring colors from aurora to Electric Blue
- Update error border colors
- Remove glass-related styling

---

## Phase 5: Secondary Components (12 files)

_Smaller updates, mostly token-based color references._

### Files to update:

- `skeleton.tsx` — Update shimmer gradient color from purple to blue tint
- `metric-card.tsx` — Update to new card surface, remove glass effects
- `tabs.tsx` — Update active tab indicator to accent blue, remove glass bg
- `modal.tsx` — Update backdrop color, surface bg to white, border to slate
- `toast.tsx` — Update surface colors, remove glass bg
- `progress.tsx` — Update bar gradient to accent blue
- `tooltip.tsx` — Update bg to white/dark surface
- `dialog.tsx` — Update overlay and surface colors
- `select.tsx` — Update focus ring, dropdown bg
- `data-table-horizon.tsx` — Update header bg, row hover, borders
- `filter-bar.tsx` — Update filter chip styling
- `command.tsx` — Update command palette surface styling

---

## Phase 6: App Shell

_Update the sidebar, header, and main layout._

### File: `src/components/sidebar.tsx`

- Background: Change to `#FFFFFF` (light sidebar) with right border `border-r border-[#E2E8F0]`
- Active item: `bg-[rgba(0,82,255,0.08)] text-[#0052FF]` with left accent bar
- Hover: `bg-[#F1F5F9]`
- Logo/brand area: Update to match new palette
- Text colors: Use slate hierarchy

### File: `src/components/header.tsx`

- Background: `bg-white/80 backdrop-blur-sm` (subtle blur for sticky header)
- Bottom border: `border-b border-[#E2E8F0]`
- Search bar: Updated focus ring
- User menu: Updated dropdown styling

### File: `src/components/app-shell.tsx`

- Update `bg-bg-base` references (will auto-update via tokens)
- Update mobile sidebar overlay: `bg-black/30` (lighter overlay for light theme)
- No structural changes needed

---

## Phase 7: Page-Level Cleanup

_Fix pages that hardcode colors instead of using tokens._

### Priority pages (hardcoded colors):

- `compliance/dashboard/page.tsx` — Replace `border-gray-200`, `bg-white`, `dark:bg-slate-900` with token classes
- Any page using `dark:` prefixed classes — Remove (no dark mode)
- Pages importing `GlassCard` — Update imports if renamed

### Migration pattern for GlassCard → FeaturedCard:

```tsx
// Before
import { GlassCard } from "@/components/ui/glass-card";
// After (backward-compatible alias)
import { FeaturedCard, GlassCard } from "@/components/ui/glass-card";
```

---

## Execution Strategy

The phases are ordered by impact and dependency:

- **Phase 1** (CSS tokens) transforms the entire visual appearance in one shot
- **Phase 2** (fonts) changes typography globally
- **Phase 3** (motion) fixes hardcoded colors in animations
- **Phases 4-5** (components) polish individual component behaviors
- **Phase 6** (shell) updates the app frame
- **Phase 7** (pages) catches hardcoded stragglers

Estimated scope: ~20 files modified, ~3 files rewritten, ~10 files with minor updates.

After each phase, the app should remain functional with no build errors.
