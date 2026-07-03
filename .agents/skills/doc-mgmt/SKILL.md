---
name: doc-mgmt
description: >-
  Classify, triage, and clean up project markdown documentation. For each file: determine if it's stale, whether it can be deleted, and what the project loses if deleted. Use when user mentions doc audit, document cleanup, stale docs, orphaned files, or asks to review markdown files.
---

# Doc Management

## Quick start

```
for each .md file:
  check doc-type → classify stale? → deletable? → loss if deleted?
```

## Core workflow

### 0. Check `doc-type` header

Every doc should have a YAML front matter with `doc-type`:

```yaml
---
doc-type: catalog     # 目录索引 — 代码变则更新
doc-type: snapshot    # 代码快照 — 代码变则重验
doc-type: reference   # 参考/约定 — 不需同步
---
```

- Missing `doc-type` → flag as **needs header** (add one)
- `catalog` out of sync with code → flag as **update needed** (must fix)
- `snapshot` stale → flag as **reverify needed** (affected chapters)
- `reference` → no sync action needed, but check if still accurate

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
| C (historical) | **Delete** — history lives in git | External compliance requirement |
| D (orphaned) | Ask user to delete | External links exist, or content unique |
| E (superseded) | Delete after confirming no inbound links | Inbound links exist (update links first) |

> **v2 change**: Historical records (class C) now default to **delete** instead of archive. Git history preserves everything; docs/ is for current knowledge.

### 4. Cross-reference health (for remaining A/B files)

- Broken links (every `[text](path)` resolves)
- Encoding issues (garbled Chinese chars)
- Plain-text file paths (should be hyperlinks)
- Stale anchors (`#section` mismatch)
- Obsolete references to deleted files
- Missing entries in `INDEX.md` or `文件索引.md`
- `doc-type` missing or mismatched with content
- Content references entities (files/classes/functions/routes) that no longer exist

### 5. Apply doc-type headers

Files without `doc-type` header need one added. Rules:

- INDEX.md, 文件索引.md → `catalog`
- 代码调用逻辑图.md, 数据因果链.md → `snapshot`
- All other reference/guide docs → `reference`

### 6. Enforce sync rule after code changes

Search `docs/` for mentions of the changed **entity** (filename / class / function / route / ORM model / enum):

- In `catalog` docs → **must update**
- In `snapshot` docs → **affected chapters must reverify**
- New entity → check if `INDEX.md` + `文件索引.md` need new entry

## Report format

```
### [filename] — [Class: A/B/C/D/E] — [doc-type: catalog/snapshot/reference/missing]
- Stale?: yes/no — [what's outdated]
- Deletable?: yes/no — [any inbound links?]
- Loss if deleted: [high/medium/low] — [what would be lost]
- Action: [keep / update / delete / add-header]
```

## Doc rot speed reference

| Document type | Rot speed | Why |
|--------------|-----------|-----|
| API routes / file index | 🚀 Fast | New endpoints added frequently |
| Refactor plans / tracking | 🚀 Fast | Status changes but nobody updates marks |
| Call graphs / causality chains | 🐢 Medium | Stale from small cumulative changes |
| Business rules / BRs | 🐌 Slow | Confirmed decisions, rarely change |
| Coding conventions | 🐌 Slow | Team consensus, stable |

## References

- `docs/INDEX.md` — master document index (`catalog`)
- `docs/文件索引.md` — full file inventory (`catalog`)
- `docs/开发规范.md#文档分类` — doc-type classification table
- `docs/开发规范.md#文档同步规则` — sync rules after code change
- `CONTEXT.md` — project context & business rules
