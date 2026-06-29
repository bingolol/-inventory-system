# Design System

## Brand Colors
- Primary: `#4f6ef7` (deep blue) — buttons, links, active states
- Primary Light: `#eef1ff` — light backgrounds
- Primary Dark: `#3b57d9` — hover states

## Semantic Colors
- Success: `#67c23a` — positive, paid, completed
- Warning: `#e6a23c` — low stock, pending
- Danger: `#f56c6c` — negative, overdue, errors
- Info: `#909399` — neutral, disabled

## Neutral Palette
- Page BG: `#f5f6f8`
- Card BG: `#ffffff`
- Elevated BG: `#fafafa` — filter bars, stat cards
- Hover BG: `#f7f8fa`

- Text Primary: `#1d2129` — headings, totals
- Text Regular: `#4e5969` — body text
- Text Secondary: `#86909c` — labels, secondary info
- Text Placeholder: `#c9cdd4` — disabled, hints

- Border: `#f0f0f0` — cards, tables, dividers
- Border Dark: `#e0e0e0` — strong dividers

## Shadows
- Card: `0 2px 12px rgba(0,0,0,0.04)`
- Card Hover: `0 8px 24px rgba(0,0,0,0.08)`
- Dropdown: `0 8px 24px rgba(0,0,0,0.1)`

## Border Radius
- Card: `16px`
- Table: `12px`
- Button/Input: `8px`
- Group card: `12px`
- Pill (badge/tag): `9999px`

## Typography
- Font: system-ui stack (-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei')
- Monospace: 'Consolas', 'Monaco', monospace — for money and amounts
- Page Title: 22px / 700
- Section Title: 15-16px / 600
- Body: 14px / 400
- Table Header: 12px / 600 / uppercase
- Table Cell: 13px / 400
- Stat Value: 22-28px / 700
- Small: 12-13px / 400

## Spacing
- Base unit: 8px
- Card padding: 20-24px
- Section gap: 16-20px
- Filter bar padding: 16px

## Component Patterns

### Card
```
border-radius: 16px
border: 1px solid #f0f0f0
box-shadow: 0 2px 12px rgba(0,0,0,0.04)
background: #fff
hover: translateY(-2px) + shadow
```

### Stat Card (colored left border)
```
border-left: 4px solid <color>
border-radius: 12px
padding: 14px 16px
background: #fafafa
display: flex; flex-direction: column; gap: 4px
```

### Form Group Card
```
border-left: 4px solid <color>
border-radius: 12px
background: #fafafa
overflow: hidden
```

### Status Badge
```
border-radius: 9999px
padding: 2px 12px
font-size: 12px
font-weight: 500
.success: bg #f0f9eb / color #67c23a
.warning: bg #fdf6ec / color #e6a23c
.danger: bg #fef0f0 / color #f56c6c
.info: bg #f4f4f5 / color #909399
.primary: bg #ecf5ff / color #409eff
```

### Filter Bar
```
background: #fafafa
border: 1px solid #f0f0f0
border-radius: 12px
padding: 16px
display: flex; gap: 12px; flex-wrap: wrap; align-items: center
```

### Page Title
```
font-size: 22px; font-weight: 700; color: #1d2129; letter-spacing: -0.3px
```

## Dark Mode
Reserved. Not yet implemented. When added:
- Page BG: `#1a1d21`
- Card BG: `#23272e`
- Surface BG: `#2a2e35`
- Text: `#e5e6eb`
