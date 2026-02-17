# Horizon Design System — Quick Reference

## 🚀 Essential Imports

```tsx
// UI Components
import {
  // Layout
  Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter,

  // Actions
  Button, IconButton, ButtonGroup,

  // Status
  Badge, StatusBadge, RiskBadge, CountBadge,

  // Forms
  FormField, FormLabel, FormDescription, FormError,
  Input, PasswordInput, Textarea, Select,
  Checkbox, CheckboxWithLabel, Switch, SwitchWithLabel,

  // Data
  DataTable, Tabs, TabList, Tab, TabPanels, TabPanel,

  // Feedback
  Skeleton, SkeletonText, SkeletonCard,
  EmptyState, EmptySearch, EmptyError,
  useToast, useToastHelpers,

  // Overlays
  Modal, ModalHeader, ModalTitle, ModalDescription, ModalBody, ModalFooter,
  ConfirmModal, Drawer,
} from "@/components/ui";

// Layout
import { PageHeader, PageGrid, PageSection } from "@/components/app-shell-new";

// Error Handling
import { ErrorBoundary, SectionErrorBoundary } from "@/components/error-boundary";
```

---

## 🎨 Common Patterns

### Button Variants
```tsx
<Button variant="primary">Primary</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="tertiary">Tertiary</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="destructive">Delete</Button>
<Button variant="accent">Accent</Button>
<Button variant="link">Link</Button>
```

### Card Variants
```tsx
<Card variant="default">Standard card</Card>
<Card variant="interactive">Clickable with hover</Card>
<Card variant="elevated">With shadow</Card>
<Card variant="ghost">Minimal</Card>
<Card variant="outlined">Border only</Card>
```

### Form Field Pattern
```tsx
<FormField error={errors.email} required>
  <FormLabel>Email</FormLabel>
  <FormDescription>We'll never share your email.</FormDescription>
  <Input type="email" placeholder="you@example.com" />
  <FormError />
</FormField>
```

### Toast Notifications
```tsx
const { success, error, promise } = useToastHelpers();

// Simple toast
success("Saved!", "Your changes were saved.");

// Promise-based
await promise(saveData(), {
  loading: "Saving...",
  success: "Saved!",
  error: "Failed to save",
});
```

### Modal Usage
```tsx
<Modal isOpen={isOpen} onClose={close} size="md">
  <ModalHeader>
    <ModalTitle>Title</ModalTitle>
    <ModalDescription>Description</ModalDescription>
  </ModalHeader>
  <ModalBody>Content</ModalBody>
  <ModalFooter>
    <Button variant="secondary" onClick={close}>Cancel</Button>
    <Button variant="primary" onClick={submit}>Submit</Button>
  </ModalFooter>
</Modal>
```

### Data Table
```tsx
<DataTable
  data={data}
  columns={columns}
  keyExtractor={(item) => item.id}
  sortable
  pagination
  searchable
  selectable
  loading={isLoading}
/>
```

### Tabs
```tsx
<Tabs defaultTab="1">
  <TabList>
    <Tab id="1">Overview</Tab>
    <Tab id="2">Details</Tab>
  </TabList>
  <TabPanels>
    <TabPanel id="1">Overview content</TabPanel>
    <TabPanel id="2">Details content</TabPanel>
  </TabPanels>
</Tabs>
```

---

## 🎯 Design Tokens

### Colors
| Token | Value | Usage |
|-------|-------|-------|
| `--brand-primary` | `#8b5cf6` | Primary actions, links |
| `--brand-secondary` | `#06b6d4` | Accents, highlights |
| `--bg-base` | `#0a0a0f` | Page background |
| `--bg-elevated` | `#12121a` | Cards, panels |
| `--text-primary` | `#f8fafc` | Primary text |
| `--text-secondary` | `#94a3b8` | Secondary text |
| `--risk-critical` | `#f87171` | Critical alerts |
| `--risk-high` | `#fbbf24` | High priority |
| `--risk-low` | `#34d399` | Success states |

### Spacing
| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | `0.25rem` (4px) | Tight spacing |
| `--space-2` | `0.5rem` (8px) | Default gap |
| `--space-4` | `1rem` (16px) | Section padding |
| `--space-6` | `1.5rem` (24px) | Card padding |
| `--space-8` | `2rem` (32px) | Large gaps |

### Typography
| Token | Value | Usage |
|-------|-------|-------|
| `--text-sm` | ~13px | Labels, captions |
| `--text-base` | ~14px | Body text |
| `--text-lg` | ~16px | Lead text |
| `--font-display` | Space Grotesk | Headings |
| `--font-sans` | Geist | Body text |
| `--font-mono` | JetBrains Mono | Code, data |

---

## ♿ Accessibility Checklist

- [ ] All buttons have accessible labels
- [ ] Form fields have associated labels
- [ ] Images have alt text
- [ ] Color contrast is 4.5:1 or higher
- [ ] Focus indicators are visible
- [ ] Keyboard navigation works
- [ ] Screen reader announces changes
- [ ] Reduced motion is respected

---

## 🐛 Common Issues & Fixes

### Styles not loading
```bash
# Ensure CSS imports are correct
import "./globals.css";  // Should import design-system.css
```

### TypeScript errors
```bash
# Check types are imported
import type { ButtonProps } from "@/components/ui";
```

### Modal not trapping focus
```bash
# Ensure focus-trap.ts is in lib/
import { trapFocus } from "@/lib/focus-trap";
```

### Toasts not appearing
```bash
# Wrap app with ToastProvider
<ToastProvider>{children}</ToastProvider>
```

---

## 📦 File Locations

```
components/
├── ui/
│   ├── index.ts          # All exports
│   ├── card.tsx
│   ├── button-horizon.tsx
│   ├── badge-horizon.tsx
│   ├── form.tsx
│   ├── data-table-horizon.tsx
│   ├── skeleton.tsx
│   ├── empty-state.tsx
│   ├── toast.tsx
│   ├── modal.tsx
│   └── tabs.tsx
├── app-shell-new.tsx
├── sidebar-new.tsx
├── header-new.tsx
└── error-boundary.tsx

lib/
├── utils.ts
└── focus-trap.ts

app/
├── design-system.css
├── globals-new.css
└── layout-new.tsx
```

---

## 🔗 Useful Links

- **Full Documentation**: `UI_UX_PROFESSIONAL_GUIDE.md`
- **Migration Guide**: `docs/product/UI_UX_RESHAPING_v3.md`
- **Component Examples**: `dashboard/page-new.tsx`
- **All Deliverables**: `UI_UX_FINAL_DELIVERABLES.md`

---

## 💡 Pro Tips

1. **Always use FormField wrapper** for form inputs — handles labels, errors, and accessibility
2. **Use Skeleton components** for loading states — prevents layout shift
3. **Wrap with ErrorBoundary** for error resilience
4. **Use Toast promises** for async operations — better UX
5. **Test keyboard navigation** — Tab, Shift+Tab, Enter, Escape
6. **Check color contrast** — Use browser dev tools
7. **Use design tokens** — Never hardcode colors or spacing
8. **Add loading states** — Every async operation needs feedback

---

**Keep this reference handy while developing!**
