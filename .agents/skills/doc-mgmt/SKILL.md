---
name: doc-mgmt
description: >-
  Classify, triage, and clean up project markdown documentation. For each file: determine if it's stale, whether it can be deleted, and what the project loses if deleted. Use when user mentions doc audit, document cleanup, stale docs, orphaned files, or asks to review markdown files.
---

# Doc Management

## Quick start

```
for each .md file:
  classify → stale? → deletable? → loss if deleted?
```

## Core workflow

### 1. Inventory every `.md` file

List all `.md` files in root and `docs/`. Cross-reference against `INDEX.md` and `文件索引.md`.

### 2. Classify each file

| Class | Label | Description |
|-------|-------|-------------|
| A | **Active reference** | Currently used, cross-linked, content still accurate |
| B | **Active but stale** | Still referenced but content out of date (update, not delete) |
| C | **Historical record** | No longer active but valuable as record (test reports, audit logs, design docs of completed features) |
| D | **Orphaned** | Exists in repo but not referenced by any index or cross-link |
| E | **Superseded** | Content replaced by newer doc(s) — check if any cross-links remain |

### 3. Triage for deletion (classes C, D, E)

For each file in C/D/E, answer:

- **Can it be deleted?** — Are there any inbound links from other docs? Any code references? Any scripts that depend on it?
- **What is the project loss?** — Would deletion lose business rules, historical context, compliance evidence, or debugging reference?
- **Is there a replacement?** — If superseded, does the newer doc clearly cover all material info?

Decision matrix:

| Class | Default action | Keep if |
|-------|---------------|---------|
| C (historical) | Keep in `docs/archive/` | Valuable record, no replacement |
| D (orphaned) | Ask user to delete | External links exist, or content unique |
| E (superseded) | Delete after confirming no inbound links | Inbound links exist (update links first) |

### 4. Cross-reference health (for remaining A/B files)

- Broken links (every `[text](path)` resolves)
- Encoding issues (garbled Chinese chars)
- Plain-text file paths (should be hyperlinks)
- Stale anchors (`#section` mismatch)
- Obsolete references to deleted files
- Missing entries in `INDEX.md` or `文件索引.md`

## Report format

```
### [filename] — [Class: A/B/C/D/E]
- Stale?: yes/no — [what's outdated]
- Deletable?: yes/no — [any inbound links?]
- Loss if deleted: [high/medium/low] — [what would be lost]
- Action: [keep / update / archive / delete]
```

## References

- `docs/INDEX.md` — master document index
- `docs/文件索引.md` — full file inventory
- `CONTEXT.md` — project context & business rules
