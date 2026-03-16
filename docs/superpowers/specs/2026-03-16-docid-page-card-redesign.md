# Design: Refactor Card Components for [docId].astro Reuse

**Date:** 2026-03-16
**Goal:** Make [docId].astro visually consistent with the document grid, support authenticated tagging, and add navigation back to the document list.

---

## 1. Overview

Currently, the [docId].astro page displays document details in a basic layout. We want it to:
- Look identical to the card view in the document grid (index.astro)
- Always show expanded details (no collapse needed)
- Support tag editing when a user is authenticated
- Provide a link back to the document list

**Approach:** Extract shared card header logic (`DocumentCardSummary`) so it's reused in both the grid view and detail page view.

---

## 2. Component Architecture

### Current Structure
```
TanStackDocumentGrid (orchestrator)
├── DocumentTable (desktop view, was DesktopTable)
│   └── DocumentDetail (expanded content, was ExpandedRowContent)
└── DocumentCard (mobile view, was EvaluationCard)
    └── DocumentDetail (expanded content, shared)
```

### New Structure
```
website/src/components/document-grid/
├── DocumentCardSummary.tsx (NEW - extracted header)
├── DocumentCard.tsx (renamed from EvaluationCard)
│   ├── Uses: DocumentCardSummary + DocumentDetail + expand/collapse logic
│   └── No changes to expand/collapse behavior
├── DocumentDetail.tsx (renamed from ExpandedRowContent)
│   └── No changes
├── DocumentTable.tsx (renamed from DesktopTable)
│   ├── Uses: DocumentCardSummary (via table columns) + DocumentDetail
│   └── No changes to collapse behavior
└── ...other components

website/src/components/
├── DocumentDetailView.tsx (NEW - React island for [docId].astro)
│   ├── Uses: DocumentCardSummary + DocumentDetail
│   ├── Always shows expanded details
│   ├── Wraps in ConvexClientProvider
│   └── Shows TagActionBar when authenticated

website/src/pages/
└── doc/[docId].astro (UPDATED)
    ├── Renders document metadata with getStaticPaths
    ├── Renders DocumentDetailView as React island
    ├── Adds link back to index.astro
    └── Max-width container (1200px, centered)
```

---

## 3. Component Responsibilities

### DocumentCardSummary.tsx (NEW)
**Purpose:** Render the card header—badges, date, title, location, applicant, laws.

**Props:**
```typescript
interface Props {
  docId: string;
  datum_display: string;
  data: {
    analyza?: any;
    nazov?: string;
  };
  hasGis: boolean;
  tagUI?: ReactNode; // Optional slot for tag section
}
```

**Rendered elements:**
- Date display
- Category badges (kategorie_vlk)
- Protection badges (GIS source type, conservation areas, etc.)
- Document title (typ_zasahu or nazov)
- Inline summary: Lokalita, Žiadateľ, Zákony

**Extracted from:** Current EvaluationCard lines 35–111 (card header without expand/collapse logic)

---

### DocumentCard.tsx (Renamed from EvaluationCard)
**Changes:**
1. Import and use `DocumentCardSummary`
2. Pass tagUI slot to DocumentCardSummary
3. Rest of logic stays the same (expand/collapse via row state, ExpandedRowContent conditional rendering)

**No impact on index.astro.** This is purely internal refactoring.

---

### DocumentTable.tsx (Renamed from DesktopTable)
**Changes:**
- Rename for clarity
- No functional changes

---

### DocumentDetail.tsx (Renamed from ExpandedRowContent)
**Changes:**
- Rename for clarity
- No functional changes

---

### DocumentDetailView.tsx (NEW)
**Purpose:** React island for [docId].astro; always-expanded document view with optional tagging.

**Props:**
```typescript
interface Props {
  docId: string;
  datum_display: string;
  data: {
    analyza?: any;
    nazov?: string;
    url?: string;
    hasGis: boolean;
  };
  isAuthenticated: boolean;
}
```

**Behavior:**
1. Render DocumentCardSummary (no expand/collapse toggle)
2. Always render DocumentDetail below it
3. If `isAuthenticated`, render TagActionBar in the card header (via tagUI slot)
4. Wrap in ConvexClientProvider for Convex mutations

**Similar to EvaluationCard but:**
- No expand/collapse state (DocumentDetail always visible)
- No row object (simpler data props)
- Standalone; doesn't depend on React Table

---

## 4. [docId].astro Integration

### Layout Structure
```html
<Layout>
  <div class="flex items-center justify-between mb-4">
    <h1>Document Details</h1>
    <a href="/index.astro">← Back to Documents</a>
  </div>

  <div class="max-w-[1200px] mx-auto">
    <DocumentDetailView
      client:load
      docId={docId}
      datum_display={datum_display}
      data={data}
      isAuthenticated={isAuthenticated}
    />
  </div>
</Layout>
```

### Key Points
1. **Navigation link:** Add a link/button in the header to return to index.astro
2. **Max-width container:** Constrain card to 1200px, centered on the page
3. **Client hydration:** `client:load` for DocumentDetailView (needed for Convex + auth)
4. **Static generation:** Metadata display (docId, date, location) is still generated at build time

---

## 5. Data Flow

### [docId].astro Render Path
1. `getStaticPaths()` generates static routes for each document
2. For each document, extract: `docId`, `datum_display`, `meta`, `analysis`
3. Determine `isAuthenticated` (client-side check via Astro context or default to false for SSG)
4. Pass data to `DocumentDetailView` island

### DocumentDetailView Runtime
1. `useStore($isAuthenticated)` checks auth state
2. If authenticated, show `TagActionBar` in the card header
3. `onTagChange` mutation updates Convex database
4. Component re-renders with updated tag status

---

## 6. Implementation Strategy

### Phase 1: Extract DocumentCardSummary
1. Create `DocumentCardSummary.tsx`
2. Extract card header markup from `EvaluationCard` (~60 lines)
3. Accept `tagUI` slot for conditionally rendering tag controls
4. Style: use existing Tailwind classes

### Phase 2: Refactor EvaluationCard
1. Rename to `DocumentCard`
2. Replace card header markup with `<DocumentCardSummary tagUI={...} />`
3. Test in grid: ensure expand/collapse still works
4. No changes to DesktopTable/DocumentTable yet

### Phase 3: Create DocumentDetailView
1. Create new component
2. Copy card header + detail rendering from DocumentCard
3. Remove expand/collapse logic
4. Add `tagUI` prop with conditional TagActionBar
5. Wrap in ConvexClientProvider

### Phase 4: Update [docId].astro
1. Render DocumentDetailView as React island
2. Add navigation header with link to index.astro
3. Add max-width + centered layout container
4. Test with authenticated and unauthenticated users

### Phase 5: Rename Components (Optional Polish)
1. Rename `DesktopTable` → `DocumentTable`
2. Rename `ExpandedRowContent` → `DocumentDetail`
3. Update all imports across the codebase

---

## 7. Styling & CSS

No new CSS needed. Reuse existing Tailwind classes from EvaluationCard:
- `.border-l-4` for left border (color-coded by importance)
- `.px-1.5 py-0.5 rounded text-[10px] font-bold uppercase` for badges
- `.flex flex-wrap gap-1` for badge containers
- All existing card styling carries over automatically

---

## 8. Testing Considerations

### Functional Tests
- [ ] Grid view (index.astro): cards still expand/collapse normally
- [ ] Detail page ([docId].astro): shows full expanded content (no collapse)
- [ ] Authenticated user: can set tags on detail page
- [ ] Unauthenticated user: tag controls hidden
- [ ] Navigation: link back to index.astro works

### Visual Regression
- [ ] Card styling identical between grid and detail page
- [ ] Badge rendering matches exactly
- [ ] No layout shifts when expanded content loads

---

## 9. Risk Mitigation

**Risk:** Breaking grid expand/collapse during DocumentCard refactor.
**Mitigation:** Extract DocumentCardSummary carefully; keep expand/collapse logic untouched. Test grid thoroughly before moving to Phase 3.

**Risk:** [docId].astro needs Convex bundle for tags.
**Mitigation:** Only load DocumentDetailView with `client:load` when `isAuthenticated` (requires runtime check). Fallback to static-only view for unauthenticated users if bundle size is a concern.

---

## 10. Success Criteria

- ✅ [docId].astro displays document card identical to grid card view
- ✅ Always-expanded detail section visible (no collapse button)
- ✅ Authenticated users can set tags
- ✅ Link to index.astro visible on detail page
- ✅ Card max-width is 1200px, centered
- ✅ Grid expand/collapse behavior unchanged
- ✅ No visual regressions in grid view
