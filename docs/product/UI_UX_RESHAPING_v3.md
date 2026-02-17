# YuFeed UI/UX Reshaping v3.0 — Horizon Design System

## Overview

This document outlines the comprehensive UI/UX reshaping of the YuFeed platform, introducing the **Horizon Design System** — a modern, accessible, and refined interface optimized for compliance workflows.

---

## 🎯 Design Principles

### 1. **Clarity First**
Every element serves a clear purpose. Information hierarchy guides users naturally through complex compliance workflows.

### 2. **Accessible by Default**
- WCAG 2.1 AA compliance throughout
- Keyboard navigation support
- Screen reader optimized
- Reduced motion preferences respected

### 3. **Motion with Meaning**
Animations serve functional purposes:
- Guide attention to important updates
- Provide feedback on interactions
- Maintain context during transitions

### 4. **Density Balanced**
Information-rich interfaces without overwhelming users. Thoughtful whitespace and grouping.

### 5. **Consistent Rhythm**
8px base grid system with predictable spacing patterns.

---

## 🎨 Visual Changes

### Color System Evolution

| Old System (Sentinel) | New System (Horizon) | Rationale |
|----------------------|---------------------|-----------|
| Electric purple `#6d5acd` | Softer violet `#8b5cf6` | Better contrast ratios |
| Bright cyan `#00d4ff` | Teal cyan `#06b6d4` | More professional feel |
| Void grays `#0a0a12` | Slate foundation | Better readability |
| Neon glows | Subtle surfaces | Less visual fatigue |

### Typography Scale

```css
/* Fluid typography for all screen sizes */
--text-2xs: clamp(0.625rem, 0.6rem + 0.125vw, 0.6875rem);
--text-xs: clamp(0.6875rem, 0.65rem + 0.1875vw, 0.75rem);
--text-sm: clamp(0.8125rem, 0.775rem + 0.1875vw, 0.875rem);
--text-base: clamp(0.875rem, 0.825rem + 0.25vw, 1rem);
/* ... continues through display sizes */
```

### Surface & Elevation

| Level | Usage | Style |
|-------|-------|-------|
| Base | Page background | `#0a0a0f` |
| Elevated | Cards, panels | `#12121a` |
| Overlay | Modals, dropdowns | `#1a1a25` |
| Floating | Popovers, tooltips | `#222230` |

---

## 🧩 Component Architecture

### New Component Structure

```
components/
├── ui/                      # Base UI primitives
│   ├── card.tsx            # Card system with variants
│   ├── button-horizon.tsx  # Button system
│   ├── badge-horizon.tsx   # Badges, status indicators
│   └── ...
├── layout/                  # Layout components
│   ├── sidebar-new.tsx
│   ├── header-new.tsx
│   └── app-shell-new.tsx
└── patterns/                # Complex patterns
    ├── metric-card.tsx
    ├── activity-feed.tsx
    └── ...
```

### Card Variants

```tsx
// Default — Standard container
<Card variant="default">

// Interactive — Hover effects, clickable
<Card variant="interactive">

// Elevated — Higher elevation, shadows
<Card variant="elevated">

// Ghost — Minimal styling
<Card variant="ghost">

// Outlined — Border emphasis
<Card variant="outlined">
```

### Button System

```tsx
// Primary — Main actions
<Button variant="primary">Save</Button>

// Secondary — Alternative actions
<Button variant="secondary">Cancel</Button>

// Tertiary — Subtle actions
<Button variant="tertiary">Learn more</Button>

// Destructive — Dangerous actions
<Button variant="destructive">Delete</Button>

// Accent — Highlighted actions
<Button variant="accent">Upgrade</Button>

// Link — Text button
<Button variant="link">View details</Button>
```

---

## 🚀 Key Improvements

### 1. Navigation Redesign

**Before:**
- Fixed dual-panel sidebar
- Context panel always visible
- Limited mobile support

**After:**
- Collapsible sidebar (72px - 256px)
- Expandable submenus
- Full mobile support with overlay
- Keyboard accessible

### 2. Global Search

New command palette-style search with:
- Keyboard shortcut (⌘K)
- Recent searches
- Quick actions
- AI-powered suggestions

### 3. Dashboard Layout

**Before:**
- Complex 3-panel workbench
- Information overload
- Fixed layouts

**After:**
- Clean 2-column grid
- Progressive disclosure
- Responsive breakpoints
- Focus on key metrics

### 4. Accessibility Enhancements

- Skip link for keyboard navigation
- Focus visible states
- ARIA labels throughout
- Color contrast compliance
- Reduced motion support

---

## 📱 Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Mobile | < 640px | Single column, collapsed nav |
| Tablet | 640px - 1024px | 2 columns, sidebar overlay |
| Desktop | 1024px - 1280px | Full sidebar, 3 columns |
| Wide | > 1280px | Expanded layouts, max-width containers |

---

## 🔄 Migration Guide

### Step 1: Update Global Styles

Replace `globals.css` with `globals-new.css` and update imports:

```tsx
// Before
import "./globals.css";

// After
import "./globals-new.css";
```

### Step 2: Update Layout

Replace the app shell:

```tsx
// Before
import AppShell from "@/components/app-shell";

// After
import AppShell from "@/components/app-shell-new";
```

### Step 3: Component Migration

Replace components incrementally:

| Old Component | New Component |
|--------------|---------------|
| `GlassCard` | `Card` |
| `Button` (old) | `Button` from `button-horizon.tsx` |
| `StatusChip` | `Badge` / `StatusBadge` |
| `RiskBadge` | `RiskBadge` from `badge-horizon.tsx` |
| `Sidebar` | `Sidebar` from `sidebar-new.tsx` |
| `Header` | `Header` from `header-new.tsx` |

### Step 4: Page Updates

Update pages to use new layout components:

```tsx
import {
  PageHeader,
  PageGrid,
  PageSection,
} from "@/components/app-shell-new";

export default function MyPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Page Title"
        description="Page description"
      >
        <Button>Action</Button>
      </PageHeader>

      <PageGrid columns={3}>
        {/* Cards */}
      </PageGrid>

      <PageSection title="Section Title">
        {/* Content */}
      </PageSection>
    </div>
  );
}
```

---

## 🎨 Customization

### Theme Variables

```css
/* Custom theme overrides */
:root {
  /* Brand colors */
  --brand-primary: #your-color;
  --brand-secondary: #your-color;

  /* Backgrounds */
  --bg-base: #your-color;
  --bg-elevated: #your-color;

  /* Text */
  --text-primary: #your-color;
  --text-secondary: #your-color;
}
```

### Component Variants

Extend components with custom variants:

```tsx
const customCardVariants = cva("...", {
  variants: {
    variant: {
      custom: "your-custom-styles",
    },
  },
});
```

---

## ♿ Accessibility Checklist

- [ ] Keyboard navigation works throughout
- [ ] Focus indicators are visible
- [ ] Color contrast meets WCAG AA
- [ ] Screen reader announcements work
- [ ] Reduced motion preferences respected
- [ ] Skip links present
- [ ] Form labels associated
- [ ] Error messages descriptive

---

## 📊 Performance Optimizations

- Font display: swap for faster text rendering
- CSS containment for layout stability
- Hardware-accelerated animations
- Lazy loading for below-fold content
- Optimized re-renders with React patterns

---

## 🐛 Known Issues & Solutions

### Issue: Flash of Unstyled Content (FOUC)
**Solution:** Ensure `suppressHydrationWarning` is set on html element

### Issue: Font Loading Delay
**Solution:** Use `font-display: swap` and preload critical fonts

### Issue: Animation Jank
**Solution:** Use `transform` and `opacity` only for animations

---

## 📚 Additional Resources

- [Design Tokens](./design-tokens.md)
- [Component Library Storybook](./storybook.md)
- [Accessibility Guidelines](./accessibility.md)
- [Animation Guidelines](./animation.md)

---

## 📝 Changelog

### v3.0.0 (2026-02-17)
- Initial Horizon Design System release
- Complete UI/UX reshaping
- New component architecture
- Improved accessibility
- Enhanced mobile experience
- Modernized visual design

---

## 🤝 Contributing

When contributing to the design system:

1. Follow established patterns
2. Maintain accessibility standards
3. Test across breakpoints
4. Document component usage
5. Include Storybook stories

---

## 📞 Support

For questions or issues with the new UI/UX:

- Design System: #design-system Slack channel
- Accessibility: #a11y Slack channel
- General: Create a GitHub issue

---

*Last updated: 2026-02-17*
*Design System Version: 3.0.0*
