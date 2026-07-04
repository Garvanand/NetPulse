# NetPulse Design System

## Overview
NetPulse employs a **Dark-Mode-First** design system leveraging Tailwind CSS v4's native CSS variable theming. The aesthetic relies heavily on "glassmorphism", deep slate backgrounds, and vibrant accents (Indigo for primary actions, Emerald for healthy statuses, Rose for anomalies).

## Tokens (`globals.css`)

### Typography
- **Primary Font**: Inter (Clean, modern sans-serif)

### Semantic Colors
| Token | Variable | Value | Purpose |
|---|---|---|---|
| Background | `--color-background` | `slate-950` (#020617) | App background |
| Foreground | `--color-foreground` | `slate-50` (#f8fafc) | Default text color |
| Card | `--color-card` | `slate-900` (#0f172a) | Elevated container backgrounds |
| Primary | `--color-primary` | `indigo-500` (#6366f1) | Call to action, primary buttons |
| Secondary | `--color-secondary` | `slate-800` (#1e293b) | Subtle interactive elements |
| Muted | `--color-muted` | `slate-800` (#1e293b) | Disabled states, empty states |
| Destructive | `--color-destructive` | `rose-500` (#f43f5e) | Delete buttons, critical alerts |
| Success | `--color-success` | `emerald-500` (#10b981) | Normal states, healthy systems |
| Border | `--color-border` | `slate-800` (#1e293b) | Generic subtle borders |

### Spacing & Borders
- **Border Radius**: Global `--radius` defaults to `0.5rem` for softly rounded cards and buttons.
- **Glassmorphism**: Components use classes like `bg-card/50 backdrop-blur-md` for depth.

## Animation (Framer Motion)
Micro-interactions are handled via Framer Motion:
- **Buttons**: Scale down (`whileTap={{ scale: 0.98 }}`)
- **Cards**: Subtle hover lift (`whileHover={{ y: -2 }}`)
- **Mounts**: Smooth fade-in (`initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}`)
