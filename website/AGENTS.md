# Website — Agent Guide

Astro 5 static site + React 19 islands + Tailwind CSS 4, with an optional Convex backend for
user authentication and document tagging. Deployed to GitHub Pages at
`https://michalfapso.github.io/vlk_uradne_tabule/`.

## Dev Commands (run from `./website/`)

```bash
npm install       # install dependencies
npm run dev       # dev server at http://localhost:4321/vlk_uradne_tabule/
npm run build     # build static site to dist/
npm run preview   # preview built site locally
```

## Key Config Files

| File | Purpose |
|---|---|
| `astro.config.mjs` | Astro config — `base: '/vlk_uradne_tabule/'`, integrations: tailwind + react |
| `tailwind.config.mjs` | Tailwind CSS config |
| `convex/schema.ts` | Convex database schema |
| `package.json` | Node dependencies |

## Pages

| Page | Path | Description |
|---|---|---|
| Index | `src/pages/index.astro` | Document grid showing last 7 days of documents |
| Document detail | `src/pages/doc/[docId].astro` | Full analysis, extracted text, law references for one doc |

`index.astro` loads `data/scraped/minv_2_documents_old.json` and `minzp_2_documents_old.json`,
builds a `docIdToPathMap` via glob over `data/docs/*/*/*/*`, then enriches each document with
its `analysis.json`. It renders `TanStackDocumentGrid` and `Header` as React islands.

## Key Components

| Component | Type | Description |
|---|---|---|
| `TanStackDocumentGrid.tsx` | React island | Main sortable/filterable document table using TanStack React Table v8 |
| `Header.tsx` | React island | Navigation + auth section; requires `ConvexClientProvider` as ancestor |
| `ConvexClientProvider.tsx` | React island | Wraps children with Convex auth provider; must be ancestor of any component using Convex hooks |
| `AuthSection.tsx` | React island | Login/logout UI using Convex Auth |
| `OkresyStatus.astro` | Astro component | Shows per-district scraping status |
| `DocumentTable.astro` | Astro component | Legacy Tabulator-based table (being replaced by TanStack) |

**Important:** `ConvexClientProvider` must wrap `Header` and any component using Convex hooks.
Do not nest two `ConvexClientProvider` instances — causes auth state desync.

## Convex Backend

Schema at `convex/schema.ts`. Two table groups:

**`authTables`** (from `@convex-dev/auth`) — users, sessions, accounts, verification codes.

**`docTags`** — user-tagged documents:
```typescript
docTags: defineTable({
  userId: v.id("users"),
  docId: v.string(),       // document ID from scrapers
  tag: v.string(),         // "important" | "unimportant" | "noted"
  docDate: v.string(),     // ISO date string
})
  .index("by_user", ["userId"])
  .index("by_doc", ["docId"])
  .index("by_user_doc", ["userId", "docId"])
```

## Data Flow (website)

```
data/scraped/minv_2_documents_old.json   }
data/scraped/minzp_2_documents_old.json  } → index.astro (build time)
data/docs/{source}/{kraj}/{okres}/{docId}/analysis.json  }
    ↓
TanStackDocumentGrid (React, client-side filtering/sorting)
    ↓
doc/[docId].astro (dynamic route, build time — one page per document)
```

## State Management

- **Nanostores** (`nanostores`, `@nanostores/react`): lightweight auth state shared across islands
- **Convex hooks**: `useQuery`, `useMutation` for real-time DB access inside React islands

## Tech Stack Versions

- Astro 5.7.10, React 19.2.4, Tailwind CSS 4.1.10 (via `@tailwindcss/vite`)
- `@tanstack/react-table` 8.21.3
- `convex` 1.32.0, `@convex-dev/auth` 0.0.91
- `primereact` 10.9.7 (UI components), `marked` 15.0.12 (markdown rendering)
