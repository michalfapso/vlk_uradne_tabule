# Website Stack

## Framework and Build

- **Astro 5.7.10** — static site generator (`output: 'static'`)
- Base path: `/vlk_uradne_tabule/` (GitHub Pages repo name)
- Site URL: `https://michalfapso.github.io`
- Config: `website/astro.config.mjs`

React components are rendered as **islands** (client-side hydration). Most page-level data
loading happens at build time in `.astro` files.

## Pages

**`src/pages/index.astro`** — Homepage
- Loads `data/scraped/minv_2_documents_old.json` and `minzp_2_documents_old.json` at build time
- Builds `docIdToPathMap` using `glob.sync('data/docs/*/*/*/*')` — maps docId → directory path
- Enriches each document with its `analysis.json`
- Filters to last 7 days
- Renders `TanStackDocumentGrid` (client island) and `Header` (client island)

**`src/pages/doc/[docId].astro`** — Document detail (dynamic route, built statically)
- One page per document
- Shows full analysis, extracted text, law references, GIS data
- Includes `Header` component (needs `ConvexClientProvider` wrapper)

## Component Architecture

```
Layout.astro
└── Header.tsx (client:load)                 ← needs ConvexClientProvider as ancestor
    └── ConvexClientProvider.tsx             ← wraps everything needing Convex
        └── AuthSection.tsx                  ← login/logout UI

index.astro
└── TanStackDocumentGrid.tsx (client:load)   ← main data table
└── OkresyStatus.astro                       ← per-district scraping status
```

**Rule:** Never render two `ConvexClientProvider` instances on the same page — causes auth
desync. The provider should wrap `Header` once at the top level.

## Key Components

**`TanStackDocumentGrid.tsx`** — TanStack React Table v8
- Column definitions with sorting, filtering, pagination
- Reads documents array passed as Astro prop at build time
- Client-side filtering/sorting — no server calls

**`ConvexClientProvider.tsx`** — Convex auth provider
- Must wrap any component that uses `useQuery`, `useMutation`, or auth hooks
- Reads `CONVEX_URL` from Astro env

**`AuthSection.tsx`** — Auth UI
- Uses `useAuthActions()` from `@convex-dev/auth/react`
- Shows login form or user info + logout button

## Styling

- **Tailwind CSS 4.x** via `@tailwindcss/vite` plugin
- `tailwind.config.mjs` at root of `website/`
- `@tailwindcss/typography` for prose content

## State Management

- **Nanostores** — lightweight signal-based store for cross-island auth state
  (`src/stores/`)
- **Convex hooks** — real-time data in islands (`useQuery`, `useMutation`)

## Important Paths (relative to `website/`)

| Path | Description |
|---|---|
| `src/pages/` | Astro page files |
| `src/components/` | React and Astro components |
| `src/layouts/Layout.astro` | Base layout |
| `src/stores/` | Nanostores state |
| `src/scripts/getDocId.js` | Client-side docId utility |
| `convex/` | Convex schema and server functions |
| `public/` | Static assets |
